"""
OCR cart generation endpoint.

POST /api/ocr/scan
  - Accepts an uploaded image (multipart/form-data, field: "file")
  - Runs OCR to extract text
  - Parses the text into order items
  - Matches items against the Product DB
  - Returns a cart suggestion (items with match_type, confidence, suggestions)

The frontend then presents the populated cart to the user for approval.
"""
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import SalesRep, Product
from auth import get_current_rep
from ocr_service import extract_text_from_bytes
from cart_parser import parse_ocr_text, match_items_to_products

router = APIRouter(tags=["ocr"])


@router.post("/ocr/scan")
def scan_order_image(
    file: UploadFile = File(...),
    rep: SalesRep = Depends(get_current_rep),
    db: Session = Depends(get_db),
):
    """
    Upload a handwritten order image, extract items via OCR, and return
    a structured cart suggestion for user approval.

    Response shape:
    {
      "ocr_text": "<raw text from image>",
      "cart": [
        {
          "raw_text": "2x Cola Classic 24-pack",
          "quantity": 2,
          "product_id": 1,
          "product_name": "Cola Classic 24-pack",
          "sku": "BEV-001",
          "unit_price": 18.99,
          "match_type": "exact",   // "exact" | "fuzzy" | "none"
          "confidence": 1.0,
          "suggestions": []        // non-empty when match_type == "fuzzy"
        },
        ...
      ],
      "requires_approval": true,
      "unmatched_count": 0
    }
    """
    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file must be an image.")

    image_bytes = file.file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded image is empty.")

    # Run OCR
    try:
        ocr_text = extract_text_from_bytes(image_bytes)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"OCR failed: {exc}")

    # Parse text → ParsedItems
    parsed_items = parse_ocr_text(ocr_text)

    # Load all products from DB
    all_products = db.query(Product).all()

    # Match ParsedItems → CartItems
    cart_items = match_items_to_products(parsed_items, all_products)

    unmatched = sum(1 for ci in cart_items if ci.match_type == "none")

    return {
        "ocr_text": ocr_text,
        "cart": [
            {
                "raw_text": ci.raw_text,
                "quantity": ci.quantity,
                "product_id": ci.product_id,
                "product_name": ci.product_name,
                "sku": ci.sku,
                "unit_price": ci.unit_price,
                "match_type": ci.match_type,
                "confidence": ci.confidence,
                "suggestions": ci.suggestions,
                "cancelled": ci.cancelled,
            }
            for ci in cart_items
        ],
        "requires_approval": True,
        "unmatched_count": unmatched,
    }
