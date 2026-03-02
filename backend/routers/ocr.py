import re
import subprocess
import tempfile
import os
from difflib import SequenceMatcher

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from models import SalesRep, Product
from auth import get_current_rep

router = APIRouter(tags=["ocr"])


class ParsedItem(BaseModel):
    quantity: int
    raw_text: str
    matched_product_id: int | None = None
    matched_product_name: str | None = None
    matched_product_sku: str | None = None
    match_type: str  # "exact", "fuzzy", "sku", "none"
    confidence: float
    suggestions: list[dict] = []


class ParseOrderResponse(BaseModel):
    items: list[ParsedItem]
    raw_ocr_text: str
    unmatched_count: int


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def find_best_match(query: str, products: list[Product], threshold: float = 0.4):
    """Find best matching product using fuzzy string similarity."""
    best_score = 0
    best_product = None

    query_lower = query.lower()

    for product in products:
        name_lower = product.name.lower()
        sku_lower = product.sku.lower()

        # Check SKU match first
        if query_lower == sku_lower or query_lower in sku_lower:
            return product, 1.0, "sku"

        # Exact name match
        if query_lower == name_lower:
            return product, 1.0, "exact"

        # Contains match
        if query_lower in name_lower or name_lower in query_lower:
            score = 0.9
            if score > best_score:
                best_score = score
                best_product = product
            continue

        # Word overlap scoring
        query_words = set(re.findall(r'\w+', query_lower))
        name_words = set(re.findall(r'\w+', name_lower))
        if query_words and name_words:
            overlap = len(query_words & name_words) / max(len(query_words), len(name_words))
            if overlap > best_score:
                best_score = overlap
                best_product = product

        # Sequence similarity
        seq_score = similarity(query, product.name)
        if seq_score > best_score:
            best_score = seq_score
            best_product = product

    if best_product and best_score >= threshold:
        match_type = "exact" if best_score > 0.85 else "fuzzy"
        return best_product, best_score, match_type

    return None, 0.0, "none"


def get_top_suggestions(query: str, products: list[Product], top_n: int = 3) -> list[dict]:
    """Get top N product suggestions sorted by similarity."""
    scored = []
    for product in products:
        score = max(
            similarity(query, product.name),
            similarity(query, product.sku),
        )
        # Boost for word overlap
        q_words = set(re.findall(r'\w+', query.lower()))
        p_words = set(re.findall(r'\w+', product.name.lower()))
        if q_words and p_words:
            overlap = len(q_words & p_words) / max(len(q_words), len(p_words))
            score = max(score, overlap * 0.9)
        scored.append((score, product))

    scored.sort(key=lambda x: -x[0])
    return [
        {
            "product_id": p.id,
            "product_name": p.name,
            "sku": p.sku,
            "unit_price": p.unit_price,
            "unit": p.unit,
            "confidence": round(s, 3),
        }
        for s, p in scored[:top_n]
        if s > 0.2
    ]


def run_tesseract(image_bytes: bytes) -> str:
    """Run Tesseract OCR on image bytes and return extracted text."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp.write(image_bytes)
        tmp_path = tmp.name
    try:
        result = subprocess.run(
            ["tesseract", tmp_path, "stdout", "--psm", "6"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Tesseract error: {result.stderr}")
        return result.stdout.strip()
    finally:
        os.unlink(tmp_path)


def clean_ocr_line(line: str) -> str:
    """Strip common OCR noise: leading checkbox artifacts, dashes, trailing junk."""
    # Remove leading noise chars like "me,", "Meee,", "m°", "[7", checkbox artifacts
    line = re.sub(r'^[^a-zA-Z0-9MAKE\d]*', '', line)
    # Remove trailing OCR noise: lone bracketed letters like "[ie", "[im"
    # But NOT SKU-like patterns (e.g. "Bev-001") or plain words
    line = re.sub(r'\s+[\[\(][a-zA-Z]{1,4}[\]\)]?\s*$', '', line)
    # Remove trailing standalone em-dash or long dashes
    line = re.sub(r'\s*[—–]+\s*$', '', line)
    return line.strip()


def parse_ocr_lines(ocr_text: str) -> list[dict]:
    """
    Parse OCR text lines into structured items.
    Handles formats like:
      2x Cola Classic 24-pack
      1 x Granola Bars 48-ct
      3 Whole Milk 1 Gallon
      MAKE THAT 5 CASES Sparkling Water
      CANCEL BEER - add 1 case BEV-001
    Ignores totals, headers, annotations, and crossed-out lines.
    """
    items = []
    lines = ocr_text.splitlines()

    # Patterns to skip (matched on cleaned line)
    skip_patterns = [
        r'^\s*$',
        r'(?i)total[:\s]',            # totals anywhere in line
        r'(?i)^(order\s+(for|note|list)|store\s*:)',
        r'(?i)need this fast',
        r'(?i)^\s*cancel\s+\w+\s*$',
        r'(?i)items?\.',              # "4 items." summary lines
    ]

    # "MAKE THAT N CASES product"
    make_that_re = re.compile(
        r'(?i)make\s+that\s+(\d+)\s+(?:cases?\s+)?(.+)',
    )

    # "CANCEL X - add N case Y" or "CANCEL X - add N Y"
    cancel_add_re = re.compile(
        r'(?i)cancel\s+\S+\s*[-–]\s*add\s+(\d+)\s+(?:case\s+)?(.+)',
    )

    # Standard: optional noise prefix, then qty (with optional x/cases/cs), then product
    # Allows leading noise like "me," "Meee," before the digit
    qty_re = re.compile(
        r'(?:[^0-9]*)(\d+)\s*[xX]?\s+(.+)',
    )

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        cleaned = clean_ocr_line(line)
        if not cleaned:
            continue

        # Skip unwanted lines
        if any(re.search(p, cleaned) for p in skip_patterns):
            continue

        # Handle CANCEL...add corrections (use search, not match, for leading noise)
        m = cancel_add_re.search(cleaned)
        if m:
            qty = int(m.group(1))
            product_query = m.group(2).strip()
            items.append({"quantity": qty, "raw_text": raw_line, "product_query": product_query})
            continue

        # Handle "MAKE THAT N CASES product"
        m = make_that_re.search(cleaned)
        if m:
            qty = int(m.group(1))
            product_query = m.group(2).strip()
            items.append({"quantity": qty, "raw_text": raw_line, "product_query": product_query})
            continue

        # Standard quantity + product line
        m = qty_re.match(cleaned)
        if m:
            qty = int(m.group(1))
            product_query = m.group(2).strip()
            # Clean trailing OCR noise (lone letters at end like "iim", "—")
            product_query = re.sub(r'\s+[-—]?\s*[iIlL\[\(]{1,4}[\]\)]?\s*$', '', product_query).strip()
            if product_query:
                items.append({"quantity": qty, "raw_text": raw_line, "product_query": product_query})

    return items


@router.post("/ocr/parse-order", response_model=ParseOrderResponse)
async def parse_order_image(
    image: UploadFile = File(...),
    rep: SalesRep = Depends(get_current_rep),
    db: Session = Depends(get_db),
):
    # Read image bytes
    image_bytes = await image.read()

    # Run Tesseract OCR
    try:
        ocr_text = run_tesseract(image_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tesseract OCR error: {str(e)}")

    if not ocr_text:
        raise HTTPException(status_code=422, detail="No text could be extracted from the image")

    # Parse OCR lines into items
    parsed_items = parse_ocr_lines(ocr_text)

    if not parsed_items:
        raise HTTPException(status_code=422, detail=f"No order items found in OCR text: {ocr_text[:200]}")

    # Get all products for matching
    products = db.query(Product).all()

    # Match each item against products
    result_items = []
    unmatched_count = 0

    for item in parsed_items:
        quantity = max(1, item["quantity"])
        raw = item["raw_text"]
        query = item["product_query"]

        # Try SKU match first
        sku_match = None
        for product in products:
            if query.upper().strip() == product.sku.upper():
                sku_match = product
                break

        if sku_match:
            result_items.append(ParsedItem(
                quantity=quantity,
                raw_text=raw,
                matched_product_id=sku_match.id,
                matched_product_name=sku_match.name,
                matched_product_sku=sku_match.sku,
                match_type="sku",
                confidence=1.0,
                suggestions=[],
            ))
            continue

        # Fuzzy match
        best_product, score, match_type = find_best_match(query, products)

        if best_product:
            suggestions = []
            if match_type == "fuzzy":
                suggestions = get_top_suggestions(query, products, top_n=3)
            result_items.append(ParsedItem(
                quantity=quantity,
                raw_text=raw,
                matched_product_id=best_product.id,
                matched_product_name=best_product.name,
                matched_product_sku=best_product.sku,
                match_type=match_type,
                confidence=round(score, 3),
                suggestions=suggestions,
            ))
        else:
            unmatched_count += 1
            suggestions = get_top_suggestions(query, products, top_n=3)
            result_items.append(ParsedItem(
                quantity=quantity,
                raw_text=raw,
                matched_product_id=None,
                matched_product_name=None,
                matched_product_sku=None,
                match_type="none",
                confidence=0.0,
                suggestions=suggestions,
            ))

    return ParseOrderResponse(
        items=result_items,
        raw_ocr_text=ocr_text,
        unmatched_count=unmatched_count,
    )
