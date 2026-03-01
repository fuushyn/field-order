"""Cart generation router with OCR support."""
import re, difflib, json, subprocess, tempfile, os
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from models import SalesRep, Product
from schemas import ProductOut
from auth import get_current_rep

_OCR_SERVICE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ocr_service.js")
router = APIRouter(tags=["cart"])

class GenerateCartRequest(BaseModel):
    items: list[str]

class ParseTextRequest(BaseModel):
    text: str

class CartItemResult(BaseModel):
    product: Optional[ProductOut]
    quantity: int
    match_type: str
    confidence: float
    original_text: str

class CartGenerateResponse(BaseModel):
    cart_items: list[CartItemResult]
    requires_approval: bool

class OCRResponse(BaseModel):
    raw_text: str
    confidence: float
    cart: CartGenerateResponse

_QTY_RE = re.compile(r"^\s*(?P<qty>\d+(?:\.\d+)?)\s*[xX×*]\s*(?P<name>.+)$")
_QTY_TRAILING_RE = re.compile(r"^(?P<name>.+?)\s*[xX×*]\s*(?P<qty>\d+(?:\.\d+)?)$")

def _parse_item_string(text: str) -> tuple[int, str]:
    text = text.strip()
    m = _QTY_RE.match(text)
    if m:
        return int(float(m.group("qty"))), m.group("name").strip()
    m = _QTY_TRAILING_RE.match(text)
    if m:
        return int(float(m.group("qty"))), m.group("name").strip()
    parts = text.split(None, 1)
    if len(parts) == 2 and parts[0].isdigit():
        return int(parts[0]), parts[1].strip()
    return 1, text

def _match_product(name: str, products: list, fuzzy_threshold: float = 0.40):
    name_lower = name.lower().strip()
    for p in products:
        if p.name.lower() == name_lower:
            return p, "exact", 1.0
    subs = [(p, difflib.SequenceMatcher(None, name_lower, p.name.lower()).ratio())
            for p in products if name_lower in p.name.lower() or p.name.lower() in name_lower]
    if subs:
        best_p, best_r = max(subs, key=lambda x: x[1])
        return best_p, "fuzzy", round(min(0.95, best_r + 0.10), 3)
    best_p, best_r = None, 0.0
    for p in products:
        r = difflib.SequenceMatcher(None, name_lower, p.name.lower()).ratio()
        if r > best_r:
            best_r, best_p = r, p
    if best_r >= fuzzy_threshold and best_p:
        return best_p, "fuzzy", round(best_r, 3)
    return None, "not_found", 0.0

def _generate_cart_items(items: list[str], db: Session) -> CartGenerateResponse:
    products = db.query(Product).all()
    cart_items, requires_approval = [], False
    for item_str in items:
        item_str = item_str.strip()
        if not item_str:
            continue
        qty, name = _parse_item_string(item_str)
        product, match_type, confidence = _match_product(name, products)
        if match_type != "exact":
            requires_approval = True
        cart_items.append(CartItemResult(
            product=ProductOut.model_validate(product) if product else None,
            quantity=qty, match_type=match_type, confidence=confidence, original_text=item_str,
        ))
    return CartGenerateResponse(cart_items=cart_items, requires_approval=requires_approval)

def _run_ocr(image_path: str) -> tuple[str, float]:
    try:
        result = subprocess.run(["node", _OCR_SERVICE_PATH, image_path],
            capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"OCR error: {result.stderr}")
        data = json.loads(result.stdout)
        if "error" in data:
            raise HTTPException(status_code=500, detail=f"OCR error: {data['error']}")
        return data["text"], data.get("confidence", 0.0)
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="OCR timed out")

@router.post("/cart/generate", response_model=CartGenerateResponse)
def generate_cart(body: GenerateCartRequest, rep: SalesRep = Depends(get_current_rep), db: Session = Depends(get_db)):
    return _generate_cart_items(body.items, db)

@router.post("/cart/parse-text", response_model=CartGenerateResponse)
def parse_text_to_cart(body: ParseTextRequest, rep: SalesRep = Depends(get_current_rep), db: Session = Depends(get_db)):
    return _generate_cart_items([l.strip() for l in body.text.splitlines() if l.strip()], db)

@router.post("/cart/from-image", response_model=OCRResponse)
async def cart_from_image(file: UploadFile = File(...), rep: SalesRep = Depends(get_current_rep), db: Session = Depends(get_db)):
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are accepted")
    suffix = ".png" if "png" in (file.content_type or "") else ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        raw_text, confidence = _run_ocr(tmp_path)
        cart = _generate_cart_items([l.strip() for l in raw_text.splitlines() if l.strip()], db)
        return OCRResponse(raw_text=raw_text, confidence=confidence, cart=cart)
    finally:
        os.unlink(tmp_path)
