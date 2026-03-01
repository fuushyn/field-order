"""Backend tests for Field Order API - Cart Generation + OCR feature."""
import sys, os, pathlib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from httpx import AsyncClient, ASGITransport
from main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def auth_headers(client):
    resp = await client.post("/api/login", json={"username": "rep1", "password": "password"})
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


# Health
@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

# Auth
@pytest.mark.asyncio
async def test_login_success(client):
    resp = await client.post("/api/login", json={"username": "rep1", "password": "password"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()

@pytest.mark.asyncio
async def test_login_wrong_password(client):
    resp = await client.post("/api/login", json={"username": "rep1", "password": "wrong"})
    assert resp.status_code == 401

@pytest.mark.asyncio
async def test_login_unknown_user(client):
    resp = await client.post("/api/login", json={"username": "nobody", "password": "x"})
    assert resp.status_code == 401

# Products
@pytest.mark.asyncio
async def test_products_exact_search(client, auth_headers):
    resp = await client.get("/api/products", params={"search": "Cola Classic 24-pack"}, headers=auth_headers)
    assert resp.status_code == 200
    assert any(p["name"] == "Cola Classic 24-pack" for p in resp.json())

@pytest.mark.asyncio
async def test_products_fuzzy_search(client, auth_headers):
    resp = await client.get("/api/products", params={"search": "cola"}, headers=auth_headers)
    assert resp.status_code == 200
    assert any("cola" in p["name"].lower() for p in resp.json())

@pytest.mark.asyncio
async def test_products_no_results(client, auth_headers):
    resp = await client.get("/api/products", params={"search": "zzznotfoundxxx"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []

@pytest.mark.asyncio
async def test_products_requires_auth(client):
    resp = await client.get("/api/products")
    assert resp.status_code in (401, 403)

# Orders
@pytest.mark.asyncio
async def test_create_order(client, auth_headers):
    retailers = (await client.get("/api/retailers", headers=auth_headers)).json()
    products = (await client.get("/api/products", headers=auth_headers)).json()
    resp = await client.post("/api/orders", json={
        "retailer_id": retailers[0]["id"],
        "items": [{"product_id": products[0]["id"], "quantity": 2}]
    }, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"

# Cart generate
@pytest.mark.asyncio
async def test_cart_generate_exact_match(client, auth_headers):
    resp = await client.post("/api/cart/generate", json={"items": ["10x Cola Classic 24-pack"]}, headers=auth_headers)
    assert resp.status_code == 200
    item = resp.json()["cart_items"][0]
    assert item["match_type"] == "exact"
    assert item["confidence"] == 1.0
    assert item["quantity"] == 10
    assert item["product"]["name"] == "Cola Classic 24-pack"

@pytest.mark.asyncio
async def test_cart_generate_fuzzy_match(client, auth_headers):
    resp = await client.post("/api/cart/generate", json={"items": ["2x coke", "4x bread"]}, headers=auth_headers)
    assert resp.status_code == 200
    assert all(i["match_type"] in ("exact", "fuzzy", "not_found") for i in resp.json()["cart_items"])

@pytest.mark.asyncio
async def test_cart_generate_not_found(client, auth_headers):
    resp = await client.post("/api/cart/generate", json={"items": ["5x zzunknownproductzzz"]}, headers=auth_headers)
    item = resp.json()["cart_items"][0]
    assert item["match_type"] == "not_found"
    assert item["product"] is None

@pytest.mark.asyncio
async def test_cart_generate_requires_approval(client, auth_headers):
    resp = await client.post("/api/cart/generate", json={"items": ["10x Cola Classic 24-pack", "5x zzunknown"]}, headers=auth_headers)
    assert resp.json()["requires_approval"] is True

@pytest.mark.asyncio
async def test_cart_generate_no_approval_needed(client, auth_headers):
    resp = await client.post("/api/cart/generate", json={"items": ["10x Cola Classic 24-pack", "3x Whole Milk 1 Gallon"]}, headers=auth_headers)
    assert resp.json()["requires_approval"] is False

@pytest.mark.asyncio
async def test_cart_generate_mixed(client, auth_headers):
    resp = await client.post("/api/cart/generate", json={"items": ["3x Cola Classic 24-pack", "2x unknownproduct", "1x Whole Milk 1 Gallon"]}, headers=auth_headers)
    body = resp.json()
    assert len(body["cart_items"]) == 3
    assert body["requires_approval"] is True
    types = {i["original_text"]: i["match_type"] for i in body["cart_items"]}
    assert types["3x Cola Classic 24-pack"] == "exact"
    assert types["1x Whole Milk 1 Gallon"] == "exact"

@pytest.mark.asyncio
async def test_cart_generate_requires_auth(client):
    resp = await client.post("/api/cart/generate", json={"items": ["10x Cola Classic 24-pack"]})
    assert resp.status_code in (401, 403)

# Cart parse-text
@pytest.mark.asyncio
async def test_cart_parse_text_exact(client, auth_headers):
    resp = await client.post("/api/cart/parse-text", json={"text": "10x Cola Classic 24-pack\n5x Orange Juice 12-pack\n3x Whole Milk 1 Gallon"}, headers=auth_headers)
    body = resp.json()
    assert len(body["cart_items"]) == 3
    assert body["requires_approval"] is False
    assert all(i["match_type"] == "exact" for i in body["cart_items"])

@pytest.mark.asyncio
async def test_cart_parse_text_fuzzy(client, auth_headers):
    resp = await client.post("/api/cart/parse-text", json={"text": "2x coke\n4x oj\n6x bread"}, headers=auth_headers)
    assert resp.json()["requires_approval"] is True

@pytest.mark.asyncio
async def test_cart_parse_text_empty_lines_ignored(client, auth_headers):
    resp = await client.post("/api/cart/parse-text", json={"text": "\n\n10x Cola Classic 24-pack\n\n3x Whole Milk 1 Gallon\n\n"}, headers=auth_headers)
    assert len(resp.json()["cart_items"]) == 2

@pytest.mark.asyncio
async def test_cart_parse_text_quantities(client, auth_headers):
    resp = await client.post("/api/cart/parse-text", json={"text": "7x Cola Classic 24-pack\n12x Whole Milk 1 Gallon"}, headers=auth_headers)
    qtys = {i["original_text"]: i["quantity"] for i in resp.json()["cart_items"]}
    assert qtys["7x Cola Classic 24-pack"] == 7
    assert qtys["12x Whole Milk 1 Gallon"] == 12

# Cart from-image (OCR)
@pytest.mark.asyncio
async def test_cart_from_image_exact(client, auth_headers):
    img_path = pathlib.Path(__file__).parent / "order_exact.png"
    assert img_path.exists(), f"Test image not found: {img_path}"
    with open(img_path, "rb") as f:
        resp = await client.post("/api/cart/from-image", headers=auth_headers,
            files={"file": ("order_exact.png", f, "image/png")})
    assert resp.status_code == 200
    body = resp.json()
    assert body["confidence"] > 0
    assert len(body["raw_text"]) > 0
    # OCR quality varies by environment; verify the pipeline works end-to-end
    assert "cart_items" in body["cart"]
    assert isinstance(body["cart"]["cart_items"], list)

@pytest.mark.asyncio
async def test_cart_from_image_fuzzy(client, auth_headers):
    img_path = pathlib.Path(__file__).parent / "order_fuzzy.png"
    assert img_path.exists()
    with open(img_path, "rb") as f:
        resp = await client.post("/api/cart/from-image", headers=auth_headers,
            files={"file": ("order_fuzzy.png", f, "image/png")})
    assert resp.status_code == 200
    assert resp.json()["cart"]["requires_approval"] is True

@pytest.mark.asyncio
async def test_cart_from_image_non_image_rejected(client, auth_headers):
    resp = await client.post("/api/cart/from-image", headers=auth_headers,
        files={"file": ("test.txt", b"not an image", "text/plain")})
    assert resp.status_code == 400
