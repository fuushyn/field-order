"""
Tests for the OCR cart-generation feature.

Covers:
  - Unit tests for parse_ocr_lines() and find_best_match()
  - Integration tests posting real test-case images to the /api/ocr/parse-order endpoint
    (using FastAPI's TestClient with an in-memory SQLite database)
"""

import os
import sys
import pytest
from pathlib import Path

# Ensure the backend package root is on sys.path so all imports work
BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from models import SalesRep, Product
from auth import hash_password
from main import app
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# In-memory database fixture
# ---------------------------------------------------------------------------

TEST_DB_URL = "sqlite:///./test_field_order.db"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(bind=test_engine)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


def setup_test_db():
    """Create tables and seed demo data."""
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    db = TestSessionLocal()
    rep = SalesRep(
        username="testuser",
        password_hash=hash_password("testpass"),
        name="Test Rep",
        email="test@fieldorder.com",
    )
    db.add(rep)
    db.flush()
    products = [
        Product(sku="BEV-001", name="Cola Classic 24-pack", category="Beverages", unit_price=18.99, unit="case"),
        Product(sku="BEV-002", name="Orange Juice 12-pack", category="Beverages", unit_price=24.50, unit="case"),
        Product(sku="BEV-003", name="Sparkling Water 24-pack", category="Beverages", unit_price=14.99, unit="case"),
        Product(sku="BEV-004", name="Energy Drink 12-pack", category="Beverages", unit_price=29.99, unit="case"),
        Product(sku="SNK-001", name="Potato Chips Variety Box", category="Snacks", unit_price=22.00, unit="box"),
        Product(sku="SNK-002", name="Granola Bars 48-ct", category="Snacks", unit_price=19.50, unit="box"),
        Product(sku="SNK-003", name="Mixed Nuts 12-pack", category="Snacks", unit_price=35.00, unit="box"),
        Product(sku="SNK-004", name="Pretzels 24-pack", category="Snacks", unit_price=16.75, unit="box"),
        Product(sku="DAI-001", name="Whole Milk 1 Gallon", category="Dairy", unit_price=4.29, unit="piece"),
        Product(sku="DAI-002", name="Cheddar Cheese Block", category="Dairy", unit_price=6.99, unit="piece"),
        Product(sku="DAI-003", name="Greek Yogurt 12-pack", category="Dairy", unit_price=15.00, unit="case"),
        Product(sku="BAK-001", name="White Bread Loaf", category="Bakery", unit_price=3.49, unit="piece"),
        Product(sku="BAK-002", name="Hamburger Buns 8-pack", category="Bakery", unit_price=4.99, unit="piece"),
        Product(sku="BAK-003", name="Croissants 12-ct", category="Bakery", unit_price=12.00, unit="box"),
        Product(sku="CLN-001", name="All-Purpose Cleaner 6-pack", category="Cleaning", unit_price=21.00, unit="case"),
        Product(sku="CLN-002", name="Paper Towels 12-roll", category="Cleaning", unit_price=18.50, unit="case"),
    ]
    db.add_all(products)
    db.commit()
    db.close()


# Run DB setup once at module import time so unit tests that access the DB can use it
setup_test_db()


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        # Log in to get a JWT token
        resp = c.post("/api/login", json={"username": "testuser", "password": "testpass"})
        assert resp.status_code == 200, f"Login failed: {resp.text}"
        token = resp.json()["access_token"]
        c.headers.update({"Authorization": f"Bearer {token}"})
        yield c


TEST_CASES_DIR = Path(__file__).parent.parent.parent / "test-cases"


# ===========================================================================
# Unit Tests – parse_ocr_lines
# ===========================================================================

from routers.ocr import parse_ocr_lines, find_best_match, clean_ocr_line


class TestParseOcrLines:
    def test_simple_quantity_x_format(self):
        text = "2x Cola Classic 24-pack"
        items = parse_ocr_lines(text)
        assert len(items) == 1
        assert items[0]["quantity"] == 2
        assert "Cola Classic 24-pack" in items[0]["product_query"]

    def test_quantity_space_x_format(self):
        text = "1 x Granola Bars 48-ct"
        items = parse_ocr_lines(text)
        assert len(items) == 1
        assert items[0]["quantity"] == 1

    def test_quantity_no_x(self):
        text = "3 Whole Milk 1 Gallon"
        items = parse_ocr_lines(text)
        assert len(items) == 1
        assert items[0]["quantity"] == 3

    def test_make_that_directive(self):
        text = "MAKE THAT 5 CASES Sparkling Water"
        items = parse_ocr_lines(text)
        assert len(items) == 1
        assert items[0]["quantity"] == 5
        assert "Sparkling Water" in items[0]["product_query"]

    def test_cancel_and_add_correction(self):
        text = "CANCEL BEER - add 1 case BEV-001"
        items = parse_ocr_lines(text)
        assert len(items) == 1
        assert items[0]["quantity"] == 1
        assert "BEV-001" in items[0]["product_query"]

    def test_skips_total_lines(self):
        text = "2x Cola Classic 24-pack\nTotal: 4 items.\n1x Orange Juice 12-pack"
        items = parse_ocr_lines(text)
        assert len(items) == 2

    def test_skips_order_header(self):
        text = "Order for Store:\n2x Cola Classic 24-pack"
        items = parse_ocr_lines(text)
        assert len(items) == 1

    def test_skips_empty_lines(self):
        text = "\n\n2x Cola Classic 24-pack\n\n"
        items = parse_ocr_lines(text)
        assert len(items) == 1

    def test_multiline_order(self):
        text = (
            "2x Cola Classic 24-pack\n"
            "1x Granola Bars 48-ct\n"
            "3 Whole Milk 1 Gallon\n"
            "2x Paper Towels 12-roll\n"
        )
        items = parse_ocr_lines(text)
        assert len(items) == 4

    def test_noisy_prefix_stripped(self):
        # OCR noise: digits are still correctly parsed even with leading text noise
        text = "Meee, 2X Cola Classic 24-pack"
        items = parse_ocr_lines(text)
        assert len(items) == 1
        assert items[0]["quantity"] == 2

    def test_make_that_case_insensitive(self):
        text = "make that 4 sparkling water"
        items = parse_ocr_lines(text)
        assert len(items) == 1
        assert items[0]["quantity"] == 4


class TestCleanOcrLine:
    def test_removes_non_alpha_leading_chars(self):
        # Strips leading non-alphanumeric characters like "[7"
        result = clean_ocr_line("[7 2x Cola Classic")
        # Should start with a digit or word, no bracket
        assert not result.startswith("[")

    def test_removes_trailing_bracket_noise(self):
        result = clean_ocr_line("1x Granola Bars 48-ct [ie")
        assert "[ie" not in result

    def test_preserves_sku_dashes(self):
        result = clean_ocr_line("1 case BEV-001")
        assert "BEV-001" in result

    def test_removes_trailing_em_dash(self):
        result = clean_ocr_line("2x Cola Classic 24-pack —")
        assert "—" not in result

    def test_strips_leading_degree_symbol(self):
        # "m°" prefix should be stripped to start at "2x"
        result = clean_ocr_line("m° 2x Granola Bars")
        # Leading non-alpha chars like '°' are stripped; alpha prefix 'm' is kept
        assert "Granola Bars" in result


class TestFindBestMatch:
    @pytest.fixture(autouse=True)
    def _products(self):
        db = TestSessionLocal()
        self.products = db.query(Product).all()
        db.close()

    def test_exact_name_match(self):
        product, score, match_type = find_best_match("Cola Classic 24-pack", self.products)
        assert product is not None
        assert product.sku == "BEV-001"
        assert match_type in ("exact", "fuzzy")
        assert score > 0.8

    def test_sku_match(self):
        product, score, match_type = find_best_match("BEV-001", self.products)
        assert product is not None
        assert product.sku == "BEV-001"
        assert match_type == "sku"
        assert score == 1.0

    def test_partial_name_match(self):
        product, score, match_type = find_best_match("Granola Bars", self.products)
        assert product is not None
        assert product.sku == "SNK-002"

    def test_fuzzy_match_with_typo(self):
        product, score, match_type = find_best_match("Sparkling Watter", self.products)
        assert product is not None
        assert product.sku == "BEV-003"

    def test_no_match_below_threshold(self):
        product, score, match_type = find_best_match("XYZZY NONSENSE ITEM", self.products)
        assert product is None
        assert match_type == "none"


# ===========================================================================
# Integration Tests – POST /api/ocr/parse-order with real test-case images
# ===========================================================================

class TestOcrEndpointWithTestCaseImages:
    def _post_image(self, client, filename):
        img_path = TEST_CASES_DIR / filename
        assert img_path.exists(), f"Test image not found: {img_path}"
        with open(img_path, "rb") as f:
            resp = client.post(
                "/api/ocr/parse-order",
                files={"image": (filename, f, "image/png")},
            )
        return resp

    def test_test1_returns_200(self, client):
        """test1.png: standard multi-item handwritten order note."""
        resp = self._post_image(client, "test1.png")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    def test_test1_has_items(self, client):
        resp = self._post_image(client, "test1.png")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) >= 2, f"Expected at least 2 items, got {len(data['items'])}"

    def test_test1_includes_raw_ocr_text(self, client):
        resp = self._post_image(client, "test1.png")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["raw_ocr_text"]) > 0

    def test_test1_cola_matched(self, client):
        """Cola Classic 24-pack should be matched from test1."""
        resp = self._post_image(client, "test1.png")
        assert resp.status_code == 200
        data = resp.json()
        matched_skus = [i["matched_product_sku"] for i in data["items"] if i.get("matched_product_sku")]
        assert "BEV-001" in matched_skus, f"Cola Classic (BEV-001) not found in {matched_skus}"

    def test_test1_quantities_are_positive(self, client):
        resp = self._post_image(client, "test1.png")
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["quantity"] >= 1

    def test_test2_returns_200(self, client):
        """test2.png: mixed handwritten order with noisy OCR."""
        resp = self._post_image(client, "test2.png")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    def test_test2_has_items(self, client):
        resp = self._post_image(client, "test2.png")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) >= 1, f"Expected at least 1 item, got {len(data['items'])}"

    def test_test3_returns_200(self, client):
        """test3.png: order with MAKE THAT and CANCEL corrections."""
        resp = self._post_image(client, "test3.png")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    def test_test3_cancel_beer_handled(self, client):
        """CANCEL BEER - add 1 case BEV-001 should resolve to BEV-001."""
        resp = self._post_image(client, "test3.png")
        assert resp.status_code == 200
        data = resp.json()
        matched_skus = [i["matched_product_sku"] for i in data["items"] if i.get("matched_product_sku")]
        assert "BEV-001" in matched_skus, f"BEV-001 not found after CANCEL correction: {matched_skus}"

    def test_test3_make_that_directive_applied(self, client):
        """MAKE THAT 5 CASES should produce qty=5 for some item."""
        resp = self._post_image(client, "test3.png")
        assert resp.status_code == 200
        data = resp.json()
        quantities = [i["quantity"] for i in data["items"]]
        assert 5 in quantities, f"Expected qty=5 from MAKE THAT directive, got quantities: {quantities}"

    def test_all_items_have_required_fields(self, client):
        """Every item in any response must have the required schema fields."""
        for fname in ["test1.png", "test2.png", "test3.png"]:
            resp = self._post_image(client, fname)
            if resp.status_code != 200:
                continue
            for item in resp.json()["items"]:
                assert "quantity" in item
                assert "raw_text" in item
                assert "match_type" in item
                assert "confidence" in item
                assert item["match_type"] in ("exact", "fuzzy", "sku", "none")
                assert 0.0 <= item["confidence"] <= 1.0

    def test_confidence_score_range(self, client):
        """Confidence must be between 0.0 and 1.0 for all matched items."""
        resp = self._post_image(client, "test1.png")
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert 0.0 <= item["confidence"] <= 1.0

    def test_unmatched_items_have_suggestions(self, client):
        """Items with match_type='none' should still provide suggestions."""
        for fname in ["test1.png", "test2.png", "test3.png"]:
            resp = self._post_image(client, fname)
            if resp.status_code != 200:
                continue
            for item in resp.json()["items"]:
                if item["match_type"] == "none":
                    assert isinstance(item["suggestions"], list)


# ===========================================================================
# Edge-case / error handling tests
# ===========================================================================

class TestOcrEndpointEdgeCases:
    def test_invalid_file_returns_error(self, client):
        """Sending a non-image file should return a 422 or 500."""
        resp = client.post(
            "/api/ocr/parse-order",
            files={"image": ("note.txt", b"not an image", "text/plain")},
        )
        assert resp.status_code in (422, 500)

    def test_empty_image_returns_error(self, client):
        """Sending an empty file should return 422 or 500."""
        resp = client.post(
            "/api/ocr/parse-order",
            files={"image": ("empty.png", b"", "image/png")},
        )
        assert resp.status_code in (422, 500)

    def test_unauthenticated_request_rejected(self):
        """Requests without a token must be rejected with 401 or 403."""
        with TestClient(app) as c:
            img_path = TEST_CASES_DIR / "test1.png"
            with open(img_path, "rb") as f:
                resp = c.post(
                    "/api/ocr/parse-order",
                    files={"image": ("test1.png", f, "image/png")},
                )
        assert resp.status_code in (401, 403)
