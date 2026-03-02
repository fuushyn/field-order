"""
Integration tests for the POST /api/ocr/scan endpoint.

These tests use the FastAPI TestClient with:
- An in-memory SQLite database (seeded with the standard 16 products)
- Mocked OCR (pytesseract) so the tests do not depend on the Tesseract binary
  or image quality.

The mocked OCR returns representative text for each test image to verify
that the full pipeline (OCR → parse → match → response) works end-to-end.
"""
import io
import sys
import os
import pytest
from unittest.mock import patch, MagicMock

# Ensure the backend directory is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from main import app
from models import Product, SalesRep, Retailer
from auth import hash_password, create_access_token


# ---------------------------------------------------------------------------
# In-memory DB setup for integration tests
# ---------------------------------------------------------------------------

INTEGRATION_DB_URL = "sqlite:///./test_integration.db"


def _create_integration_engine():
    engine = create_engine(
        INTEGRATION_DB_URL, connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    return engine


def _seed_integration_db(session):
    # Clear any existing data
    session.query(Product).delete()
    session.query(Retailer).delete()
    session.query(SalesRep).delete()
    session.commit()

    rep = SalesRep(
        username="testrep",
        password_hash=hash_password("testpass"),
        name="Test Rep",
        email="testrep@integrationtest.com",
    )
    session.add(rep)
    session.flush()

    retailer = Retailer(
        name="Test Store",
        address="1 Test St",
        rep_id=rep.id,
    )
    session.add(retailer)

    products = [
        Product(sku="BEV-001", name="Cola Classic 24-pack",     category="Beverages", unit_price=18.99, unit="case"),
        Product(sku="BEV-002", name="Orange Juice 12-pack",      category="Beverages", unit_price=24.50, unit="case"),
        Product(sku="BEV-003", name="Sparkling Water 24-pack",   category="Beverages", unit_price=14.99, unit="case"),
        Product(sku="BEV-004", name="Energy Drink 12-pack",      category="Beverages", unit_price=29.99, unit="case"),
        Product(sku="SNK-001", name="Potato Chips Variety Box",  category="Snacks",    unit_price=22.00, unit="box"),
        Product(sku="SNK-002", name="Granola Bars 48-ct",        category="Snacks",    unit_price=19.50, unit="box"),
        Product(sku="SNK-003", name="Mixed Nuts 12-pack",        category="Snacks",    unit_price=35.00, unit="box"),
        Product(sku="SNK-004", name="Pretzels 24-pack",          category="Snacks",    unit_price=16.75, unit="box"),
        Product(sku="DAI-001", name="Whole Milk 1 Gallon",       category="Dairy",     unit_price=4.29,  unit="piece"),
        Product(sku="DAI-002", name="Cheddar Cheese Block",      category="Dairy",     unit_price=6.99,  unit="piece"),
        Product(sku="DAI-003", name="Greek Yogurt 12-pack",      category="Dairy",     unit_price=15.00, unit="case"),
        Product(sku="BAK-001", name="White Bread Loaf",          category="Bakery",    unit_price=3.49,  unit="piece"),
        Product(sku="BAK-002", name="Hamburger Buns 8-pack",     category="Bakery",    unit_price=4.99,  unit="piece"),
        Product(sku="BAK-003", name="Croissants 12-ct",          category="Bakery",    unit_price=12.00, unit="box"),
        Product(sku="CLN-001", name="All-Purpose Cleaner 6-pack",category="Cleaning",  unit_price=21.00, unit="case"),
        Product(sku="CLN-002", name="Paper Towels 12-roll",      category="Cleaning",  unit_price=18.50, unit="case"),
    ]
    session.add_all(products)
    session.commit()
    return rep


@pytest.fixture(scope="module")
def integration_client():
    """TestClient with in-memory DB override and a valid JWT token."""
    engine = _create_integration_engine()
    TestSessionLocal = sessionmaker(bind=engine)

    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    # Seed the DB
    db = TestSessionLocal()
    rep = _seed_integration_db(db)
    token = create_access_token({"sub": str(rep.id)})
    db.close()

    client = TestClient(app)
    client.headers = {"Authorization": f"Bearer {token}"}
    yield client

    app.dependency_overrides.clear()
    # Cleanup test DB file
    if os.path.exists("./test_integration.db"):
        os.remove("./test_integration.db")


def _make_fake_image() -> bytes:
    """Return a minimal 1x1 white PNG image as bytes."""
    from PIL import Image
    import io
    img = Image.new("RGB", (100, 50), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Endpoint smoke tests
# ---------------------------------------------------------------------------

class TestOcrEndpointSmoke:
    """Basic endpoint availability and authentication tests."""

    def test_endpoint_requires_auth(self):
        """Without a token, HTTPBearer returns 403 (FastAPI/Starlette default)."""
        client = TestClient(app)
        img_bytes = _make_fake_image()
        resp = client.post(
            "/api/ocr/scan",
            files={"file": ("test.png", io.BytesIO(img_bytes), "image/png")},
        )
        assert resp.status_code in (401, 403), (
            f"Expected 401 or 403 without auth token, got {resp.status_code}"
        )

    def test_endpoint_rejects_non_image(self, integration_client):
        resp = integration_client.post(
            "/api/ocr/scan",
            files={"file": ("order.txt", io.BytesIO(b"hello"), "text/plain")},
        )
        assert resp.status_code == 400
        assert "image" in resp.json()["detail"].lower()

    def test_endpoint_rejects_empty_file(self, integration_client):
        resp = integration_client.post(
            "/api/ocr/scan",
            files={"file": ("empty.png", io.BytesIO(b""), "image/png")},
        )
        assert resp.status_code == 400

    def test_response_shape(self, integration_client):
        """Response should have ocr_text, cart, requires_approval, unmatched_count."""
        ocr_result = "2x Cola Classic 24-pack\n1x Granola Bars 48-ct\n"
        img_bytes = _make_fake_image()

        with patch("routers.ocr.extract_text_from_bytes", return_value=ocr_result):
            resp = integration_client.post(
                "/api/ocr/scan",
                files={"file": ("test.png", io.BytesIO(img_bytes), "image/png")},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "ocr_text" in data
        assert "cart" in data
        assert "requires_approval" in data
        assert "unmatched_count" in data
        assert data["requires_approval"] is True

    def test_cart_item_shape(self, integration_client):
        """Each cart item should have the expected fields."""
        ocr_result = "2x Cola Classic 24-pack\n"
        img_bytes = _make_fake_image()

        with patch("routers.ocr.extract_text_from_bytes", return_value=ocr_result):
            resp = integration_client.post(
                "/api/ocr/scan",
                files={"file": ("test.png", io.BytesIO(img_bytes), "image/png")},
            )

        assert resp.status_code == 200
        cart = resp.json()["cart"]
        assert len(cart) >= 1
        item = cart[0]
        for field in ("raw_text", "quantity", "product_id", "product_name",
                      "sku", "unit_price", "match_type", "confidence", "suggestions"):
            assert field in item, f"Missing field '{field}' in cart item"


# ---------------------------------------------------------------------------
# Scenario 1 integration test
# ---------------------------------------------------------------------------

class TestScenario1Integration:
    """
    Integration test for the clean exact-match scenario (Image 1).
    OCR returns the ideal text; all items should be exact matches.
    """

    IMAGE1_OCR = (
        "Order for Store:\n"
        "2x Cola Classic 24-pack\n"
        "1x Granola Bars 48-ct\n"
        "3x Whole Milk 1 Gallon\n"
        "2x Paper Towels 12-roll\n"
        "\n"
        "Total: 4 items.\n"
    )

    def test_returns_four_cart_items(self, integration_client):
        img_bytes = _make_fake_image()
        with patch("routers.ocr.extract_text_from_bytes", return_value=self.IMAGE1_OCR):
            resp = integration_client.post(
                "/api/ocr/scan",
                files={"file": ("test1.png", io.BytesIO(img_bytes), "image/png")},
            )
        assert resp.status_code == 200
        assert len(resp.json()["cart"]) == 4

    def test_all_exact_matches(self, integration_client):
        img_bytes = _make_fake_image()
        with patch("routers.ocr.extract_text_from_bytes", return_value=self.IMAGE1_OCR):
            resp = integration_client.post(
                "/api/ocr/scan",
                files={"file": ("test1.png", io.BytesIO(img_bytes), "image/png")},
            )
        cart = resp.json()["cart"]
        for item in cart:
            assert item["match_type"] == "exact", (
                f"Expected exact match for '{item['raw_text']}', got '{item['match_type']}'"
            )

    def test_unmatched_count_zero(self, integration_client):
        img_bytes = _make_fake_image()
        with patch("routers.ocr.extract_text_from_bytes", return_value=self.IMAGE1_OCR):
            resp = integration_client.post(
                "/api/ocr/scan",
                files={"file": ("test1.png", io.BytesIO(img_bytes), "image/png")},
            )
        assert resp.json()["unmatched_count"] == 0

    def test_correct_skus_returned(self, integration_client):
        img_bytes = _make_fake_image()
        with patch("routers.ocr.extract_text_from_bytes", return_value=self.IMAGE1_OCR):
            resp = integration_client.post(
                "/api/ocr/scan",
                files={"file": ("test1.png", io.BytesIO(img_bytes), "image/png")},
            )
        skus = {item["sku"] for item in resp.json()["cart"]}
        assert skus == {"BEV-001", "SNK-002", "DAI-001", "CLN-002"}

    def test_correct_quantities(self, integration_client):
        img_bytes = _make_fake_image()
        with patch("routers.ocr.extract_text_from_bytes", return_value=self.IMAGE1_OCR):
            resp = integration_client.post(
                "/api/ocr/scan",
                files={"file": ("test1.png", io.BytesIO(img_bytes), "image/png")},
            )
        qty_map = {item["sku"]: item["quantity"] for item in resp.json()["cart"]}
        assert qty_map["BEV-001"] == 2
        assert qty_map["SNK-002"] == 1
        assert qty_map["DAI-001"] == 3
        assert qty_map["CLN-002"] == 2


# ---------------------------------------------------------------------------
# Scenario 2 integration test
# ---------------------------------------------------------------------------

class TestScenario2Integration:
    """
    Integration test for fuzzy/no-match scenario (Image 2).
    Items have typos and abbreviations; fuzzy matching should resolve them.
    """

    IMAGE2_OCR = (
        "2x Orange Jce 12pk\n"
        "1x Mix Nuts 12 box\n"
        "1x Cheddar block\n"
        "2x Cleaning spray 6-pack\n"
        "3x White bread\n"
    )

    def test_returns_five_cart_items(self, integration_client):
        img_bytes = _make_fake_image()
        with patch("routers.ocr.extract_text_from_bytes", return_value=self.IMAGE2_OCR):
            resp = integration_client.post(
                "/api/ocr/scan",
                files={"file": ("test2.png", io.BytesIO(img_bytes), "image/png")},
            )
        assert resp.status_code == 200
        assert len(resp.json()["cart"]) == 5

    def test_orange_juice_matched(self, integration_client):
        img_bytes = _make_fake_image()
        with patch("routers.ocr.extract_text_from_bytes", return_value=self.IMAGE2_OCR):
            resp = integration_client.post(
                "/api/ocr/scan",
                files={"file": ("test2.png", io.BytesIO(img_bytes), "image/png")},
            )
        cart = resp.json()["cart"]
        orange = next((i for i in cart if i["sku"] == "BEV-002"), None)
        assert orange is not None, f"Orange Juice (BEV-002) not found in cart: {[i['sku'] for i in cart]}"
        assert orange["quantity"] == 2

    def test_cheddar_matched(self, integration_client):
        img_bytes = _make_fake_image()
        with patch("routers.ocr.extract_text_from_bytes", return_value=self.IMAGE2_OCR):
            resp = integration_client.post(
                "/api/ocr/scan",
                files={"file": ("test2.png", io.BytesIO(img_bytes), "image/png")},
            )
        cart = resp.json()["cart"]
        cheddar = next((i for i in cart if i["sku"] == "DAI-002"), None)
        assert cheddar is not None, f"Cheddar (DAI-002) not found. Cart: {[(i['sku'], i['product_name']) for i in cart]}"

    def test_fuzzy_items_have_suggestions(self, integration_client):
        """
        Items with match_type 'fuzzy' should have a suggestions list.
        Items matched via substring path may have an empty suggestions list
        since the match is already unambiguous. Items matched via difflib
        scoring will have non-empty suggestions.
        """
        img_bytes = _make_fake_image()
        with patch("routers.ocr.extract_text_from_bytes", return_value=self.IMAGE2_OCR):
            resp = integration_client.post(
                "/api/ocr/scan",
                files={"file": ("test2.png", io.BytesIO(img_bytes), "image/png")},
            )
        cart = resp.json()["cart"]
        fuzzy_items = [i for i in cart if i["match_type"] == "fuzzy"]
        assert len(fuzzy_items) >= 1, "Expected at least one fuzzy-matched item"
        for item in fuzzy_items:
            assert isinstance(item["suggestions"], list)
            # All fuzzy items must have been resolved to a product
            assert item["product_id"] is not None, (
                f"Fuzzy item '{item['raw_text']}' has no product_id"
            )

    def test_requires_approval_true(self, integration_client):
        img_bytes = _make_fake_image()
        with patch("routers.ocr.extract_text_from_bytes", return_value=self.IMAGE2_OCR):
            resp = integration_client.post(
                "/api/ocr/scan",
                files={"file": ("test2.png", io.BytesIO(img_bytes), "image/png")},
            )
        assert resp.json()["requires_approval"] is True


# ---------------------------------------------------------------------------
# Scenario 3 integration test
# ---------------------------------------------------------------------------

class TestScenario3Integration:
    """
    Integration test for the complex warehouse note (Image 3).
    Tests cancellation, quantity revision, SKU substitution, and misspellings.
    """

    IMAGE3_OCR = (
        "4 cs Sparkling Water 24pk\n"
        "MAKE THAT 5 CASES\n"
        "2 Energy Drinks\n"
        "1 box Crosaants 12-ct\n"
        "3 boxes Potato Chip Var. Box\n"
        "~2 cases Beer~\n"
        "CANCEL BEER - add 1 case BEV-001 instead\n"
    )

    def test_beer_not_in_cart(self, integration_client):
        """Cancelled beer should not appear in the cart."""
        img_bytes = _make_fake_image()
        with patch("routers.ocr.extract_text_from_bytes", return_value=self.IMAGE3_OCR):
            resp = integration_client.post(
                "/api/ocr/scan",
                files={"file": ("test3.png", io.BytesIO(img_bytes), "image/png")},
            )
        cart = resp.json()["cart"]
        names = [i.get("product_name", "") or "" for i in cart]
        queries = [i.get("raw_text", "").lower() for i in cart]
        assert not any("beer" in n.lower() for n in names), f"Beer should not be in cart: {names}"
        # Beer may appear in raw_text of the CANCEL instruction, but should not be a cart entry
        beer_entries = [i for i in cart if "beer" in (i.get("product_name") or "").lower()]
        assert len(beer_entries) == 0

    def test_cola_added_instead_of_beer(self, integration_client):
        """BEV-001 (Cola Classic) should be in cart from 'add 1 case BEV-001 instead'."""
        img_bytes = _make_fake_image()
        with patch("routers.ocr.extract_text_from_bytes", return_value=self.IMAGE3_OCR):
            resp = integration_client.post(
                "/api/ocr/scan",
                files={"file": ("test3.png", io.BytesIO(img_bytes), "image/png")},
            )
        cart = resp.json()["cart"]
        cola = next((i for i in cart if i.get("sku") == "BEV-001"), None)
        assert cola is not None, f"Cola Classic (BEV-001) should be in cart. SKUs: {[i.get('sku') for i in cart]}"
        assert cola["quantity"] == 1

    def test_sparkling_water_revised_qty(self, integration_client):
        """Sparkling Water quantity should be 5 after 'MAKE THAT 5 CASES' revision."""
        img_bytes = _make_fake_image()
        with patch("routers.ocr.extract_text_from_bytes", return_value=self.IMAGE3_OCR):
            resp = integration_client.post(
                "/api/ocr/scan",
                files={"file": ("test3.png", io.BytesIO(img_bytes), "image/png")},
            )
        cart = resp.json()["cart"]
        sparkling = next((i for i in cart if i.get("sku") == "BEV-003"), None)
        assert sparkling is not None, f"Sparkling Water (BEV-003) not found. SKUs: {[i.get('sku') for i in cart]}"
        assert sparkling["quantity"] == 5, f"Expected qty 5, got {sparkling['quantity']}"

    def test_croissants_matched_despite_typo(self, integration_client):
        """'Crosaants 12-ct' should match to Croissants 12-ct (BAK-003)."""
        img_bytes = _make_fake_image()
        with patch("routers.ocr.extract_text_from_bytes", return_value=self.IMAGE3_OCR):
            resp = integration_client.post(
                "/api/ocr/scan",
                files={"file": ("test3.png", io.BytesIO(img_bytes), "image/png")},
            )
        cart = resp.json()["cart"]
        croissants = next((i for i in cart if i.get("sku") == "BAK-003"), None)
        assert croissants is not None, (
            f"Croissants (BAK-003) not found. Items: {[(i.get('sku'), i.get('product_name')) for i in cart]}"
        )

    def test_full_expected_skus(self, integration_client):
        """Full scenario 3 should produce exactly these 5 SKUs."""
        img_bytes = _make_fake_image()
        with patch("routers.ocr.extract_text_from_bytes", return_value=self.IMAGE3_OCR):
            resp = integration_client.post(
                "/api/ocr/scan",
                files={"file": ("test3.png", io.BytesIO(img_bytes), "image/png")},
            )
        cart = resp.json()["cart"]
        actual_skus = {i["sku"] for i in cart if i.get("sku")}
        expected_skus = {"BEV-003", "BEV-004", "BAK-003", "SNK-001", "BEV-001"}
        assert expected_skus == actual_skus, (
            f"Expected {expected_skus}, got {actual_skus}"
        )
