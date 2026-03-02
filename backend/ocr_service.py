"""OCR service for extracting text from handwritten order note images."""
import re
import os
from pathlib import Path


def extract_text_from_image(image_path: str) -> str:
    """
    Extract text from an image using pytesseract (Tesseract OCR).
    Returns the raw OCR text string.
    """
    try:
        import pytesseract
        from PIL import Image

        img = Image.open(image_path)
        # Use page segmentation mode 6 (uniform block of text) for better results on notes
        custom_config = r"--oem 3 --psm 6"
        text = pytesseract.image_to_string(img, config=custom_config)
        return text
    except ImportError:
        raise RuntimeError("pytesseract and Pillow are required for OCR. Install them via pip.")


def extract_text_from_bytes(image_bytes: bytes) -> str:
    """
    Extract text from image bytes using pytesseract.
    Returns the raw OCR text string.
    """
    try:
        import pytesseract
        from PIL import Image
        import io

        img = Image.open(io.BytesIO(image_bytes))
        custom_config = r"--oem 3 --psm 6"
        text = pytesseract.image_to_string(img, config=custom_config)
        return text
    except ImportError:
        raise RuntimeError("pytesseract and Pillow are required for OCR. Install them via pip.")
