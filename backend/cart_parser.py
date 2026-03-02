"""
Cart parser: converts raw OCR text into structured cart items
and matches them against the Product DB using exact and fuzzy matching.
"""
import re
import difflib
from typing import Optional
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ParsedItem:
    """A raw item extracted from OCR text before DB matching."""
    raw_text: str
    quantity: int
    product_query: str  # cleaned name string for matching


@dataclass
class CartItem:
    """A matched (or suggested) cart item ready for the approval screen."""
    raw_text: str
    quantity: int
    product_id: Optional[int]
    product_name: Optional[str]
    sku: Optional[str]
    unit_price: Optional[float]
    match_type: str   # "exact", "fuzzy", "none"
    confidence: float  # 0.0 – 1.0
    suggestions: list = field(default_factory=list)  # list of dicts for fuzzy alternatives
    cancelled: bool = False


# ---------------------------------------------------------------------------
# Text pre-processing helpers
# ---------------------------------------------------------------------------

# Patterns for lines that are clearly not order items
_SKIP_PATTERNS = [
    r"^order\s+for",
    r"^total\s*:",
    r"^note\s*:",
    r"^check\s+price",
    r"^need\s+this\s+fast",
    r"^\s*$",
]
_SKIP_RE = [re.compile(p, re.IGNORECASE) for p in _SKIP_PATTERNS]

# Cancellation indicators: lines with strikethrough markers or explicit cancel note
_CANCEL_RE = re.compile(
    r"(cancel|cancelled|~{1,3}.*~{1,3}|crossed\s*out)", re.IGNORECASE
)

# Quantity prefixes:  "2x", "1x", "3 x", "2 cases", "4 cs", "MAKE THAT 5 CASES"
_QTY_PATTERNS = [
    # "MAKE THAT 5 CASES" overrides earlier quantity
    r"make\s+that\s+(\d+)\s+cases?",
    # Standard Nx / N x prefix
    r"^(\d+)\s*x\s+(.+)",
    # "N cases/cs/box/boxes/pack" prefix
    r"^(\d+)\s+(?:cases?|cs|box(?:es)?|packs?|piece[s]?|ct)\s+(.+)",
    # bare number prefix: "2 Cola Classic"
    r"^(\d+)\s+(.+)",
]
_QTY_RE = [(re.compile(p, re.IGNORECASE), p) for p, _ in
           [(p, None) for p in _QTY_PATTERNS]]


def _is_skip_line(line: str) -> bool:
    for rx in _SKIP_RE:
        if rx.search(line.strip()):
            return True
    return False


def _clean_noise(text: str) -> str:
    """
    Remove common OCR noise / annotation artifacts from a product name.
    E.g. "(sp?)", "NEED THIS FAST", "Check price", trailing dashes/arrows.
    """
    # Remove bracketed annotations like (sp?), (sic), etc.
    text = re.sub(r"\([^)]*\)", "", text)
    # Remove annotation phrases
    noise_phrases = [
        r"check\s+price",
        r"need\s+this\s+fast!?",
        r"need\s+this",
        r"fast!?",
        r"<[-—]+",
        r"[-—]+>",
        r"[~\-]{2,}",
    ]
    for phrase in noise_phrases:
        text = re.sub(phrase, "", text, flags=re.IGNORECASE)
    # Collapse multiple spaces
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip().strip(".-,;:")


def _normalise_product_name(name: str) -> str:
    """Lowercase + collapse whitespace for comparison."""
    return re.sub(r"\s+", " ", name.lower().strip())


# ---------------------------------------------------------------------------
# Quantity / item extraction
# ---------------------------------------------------------------------------

def _extract_quantity_and_name(line: str) -> Optional[tuple[int, str]]:
    """
    Returns (quantity, product_name_string) or None if the line cannot
    be parsed as an order item.
    """
    line = line.strip()

    # Check for "MAKE THAT N CASES" override
    make_that = re.search(
        r"make\s+that\s+(\d+)\s+cases?", line, re.IGNORECASE
    )
    if make_that:
        qty = int(make_that.group(1))
        # Product name is whatever comes before/after – handled by caller
        return qty, ""

    for rx, _ in _QTY_RE:
        m = rx.match(line)
        if m:
            qty = int(m.group(1))
            name = m.group(2).strip() if len(m.groups()) > 1 else ""
            name = _clean_noise(name)
            if name:
                return qty, name
    return None


# ---------------------------------------------------------------------------
# Cancellation / revision detection
# ---------------------------------------------------------------------------

_CANCEL_LINE_RE = re.compile(
    r"""
    (?:
        ~{1,}.*~{1,}          # ~~ strikethrough ~~
      | cancel\s*beer          # explicit "CANCEL BEER"
      | \bcancel(led)?\b       # "cancelled" near the item
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

_ADD_INSTEAD_RE = re.compile(
    r"add\s+(\d+)?\s*(?:case[s]?)?\s+([A-Z]{2,5}-\d{3})\s+instead",
    re.IGNORECASE,
)

_CANCEL_BEER_RE = re.compile(
    r"cancel\s+beer\s*[-–—]\s*add\s+(\d+)\s*(?:case[s]?)?\s+([A-Z]{2,5}-\d{3})\s+instead",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Main parsing entry point
# ---------------------------------------------------------------------------

def parse_ocr_text(ocr_text: str) -> list[ParsedItem]:
    """
    Parse raw OCR text into a list of ParsedItems.
    Handles:
    - Standard "Nx Product Name" format
    - Unit prefixes: cs, cases, box, boxes
    - "MAKE THAT N CASES" quantity revision
    - Crossed-out / cancelled lines
    - "CANCEL X – add N SKU instead" instructions
    """
    lines = ocr_text.splitlines()
    items: list[ParsedItem] = []
    cancelled_skus: set[str] = set()
    # Extra items injected by "add instead" instructions
    extra_items: list[ParsedItem] = []
    # Track last quantity parsed for "MAKE THAT" override
    last_qty: Optional[int] = None
    last_item_index: Optional[int] = None  # index into items[]

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        if _is_skip_line(line):
            continue

        # ----------------------------------------------------------------
        # Detect "CANCEL BEER – add 1 case BEV-001 instead" compound line
        # ----------------------------------------------------------------
        cancel_beer_match = _CANCEL_BEER_RE.search(line)
        if cancel_beer_match:
            qty_str = cancel_beer_match.group(1)
            sku = cancel_beer_match.group(2).upper()
            qty = int(qty_str) if qty_str else 1
            extra_items.append(
                ParsedItem(
                    raw_text=line,
                    quantity=qty,
                    product_query=f"SKU:{sku}",
                )
            )
            # Also mark that the beer line should be considered cancelled
            # (it will be filtered by the strikethrough detection above it)
            continue

        # ----------------------------------------------------------------
        # Detect "add N SKU instead" (without cancel prefix)
        # ----------------------------------------------------------------
        add_instead = _ADD_INSTEAD_RE.search(line)
        if add_instead and "cancel" not in line.lower():
            qty_str = add_instead.group(1)
            sku = add_instead.group(2).upper()
            qty = int(qty_str) if qty_str else 1
            extra_items.append(
                ParsedItem(
                    raw_text=line,
                    quantity=qty,
                    product_query=f"SKU:{sku}",
                )
            )
            continue

        # ----------------------------------------------------------------
        # Detect "MAKE THAT N CASES" revision – update the last item's qty
        # ----------------------------------------------------------------
        make_that = re.search(
            r"make\s+that\s+(\d+)\s+cases?", line, re.IGNORECASE
        )
        if make_that:
            new_qty = int(make_that.group(1))
            if last_item_index is not None and last_item_index < len(items):
                items[last_item_index].quantity = new_qty
            continue

        # ----------------------------------------------------------------
        # Detect cancelled/crossed-out lines (strikethrough markers)
        # ----------------------------------------------------------------
        is_cancelled = bool(_CANCEL_LINE_RE.search(line))

        # ----------------------------------------------------------------
        # Try to extract quantity + product name
        # ----------------------------------------------------------------
        result = _extract_quantity_and_name(line)
        if result is None:
            continue

        qty, name = result
        if not name:
            continue

        parsed = ParsedItem(
            raw_text=line,
            quantity=qty,
            product_query=name,
        )

        if is_cancelled:
            # Don't add cancelled items to items list; record for filtering
            cancelled_skus.add(name.lower())
            continue

        items.append(parsed)
        last_item_index = len(items) - 1

    # Inject extra items from "add instead" instructions
    items.extend(extra_items)

    return items


# ---------------------------------------------------------------------------
# Product matching
# ---------------------------------------------------------------------------

def _product_list_to_dicts(products) -> list[dict]:
    """Convert SQLAlchemy Product ORM objects to plain dicts."""
    result = []
    for p in products:
        result.append({
            "id": p.id,
            "sku": p.sku,
            "name": p.name,
            "category": p.category,
            "unit_price": p.unit_price,
            "unit": p.unit,
            "in_stock": p.in_stock,
        })
    return result


def match_items_to_products(
    parsed_items: list[ParsedItem],
    products: list,  # list of Product ORM objects or dicts
    fuzzy_threshold: float = 0.4,
) -> list[CartItem]:
    """
    Match each ParsedItem against the product list.

    Matching strategy (in order):
    1. SKU lookup  – if product_query starts with "SKU:"
    2. Exact match (case-insensitive)
    3. Substring match
    4. Fuzzy match via difflib SequenceMatcher
    5. No match

    Returns a list of CartItem objects.
    """
    # Convert ORM objects to dicts if needed
    if products and hasattr(products[0], "id"):
        db_products = _product_list_to_dicts(products)
    else:
        db_products = products  # already dicts (used in tests)

    cart_items: list[CartItem] = []

    for parsed in parsed_items:
        query = parsed.product_query

        # ---- 1. SKU lookup ----
        if query.upper().startswith("SKU:"):
            sku = query[4:].upper().strip()
            match = next((p for p in db_products if p["sku"].upper() == sku), None)
            if match:
                cart_items.append(
                    CartItem(
                        raw_text=parsed.raw_text,
                        quantity=parsed.quantity,
                        product_id=match["id"],
                        product_name=match["name"],
                        sku=match["sku"],
                        unit_price=match["unit_price"],
                        match_type="exact",
                        confidence=1.0,
                    )
                )
            else:
                cart_items.append(
                    CartItem(
                        raw_text=parsed.raw_text,
                        quantity=parsed.quantity,
                        product_id=None,
                        product_name=None,
                        sku=sku,
                        unit_price=None,
                        match_type="none",
                        confidence=0.0,
                    )
                )
            continue

        norm_query = _normalise_product_name(query)

        # ---- 2. Exact match ----
        exact = next(
            (p for p in db_products if _normalise_product_name(p["name"]) == norm_query),
            None,
        )
        if exact:
            cart_items.append(
                CartItem(
                    raw_text=parsed.raw_text,
                    quantity=parsed.quantity,
                    product_id=exact["id"],
                    product_name=exact["name"],
                    sku=exact["sku"],
                    unit_price=exact["unit_price"],
                    match_type="exact",
                    confidence=1.0,
                )
            )
            continue

        # ---- 3. Substring match ----
        substring_matches = [
            p for p in db_products
            if norm_query in _normalise_product_name(p["name"])
            or _normalise_product_name(p["name"]) in norm_query
        ]
        if len(substring_matches) == 1:
            p = substring_matches[0]
            cart_items.append(
                CartItem(
                    raw_text=parsed.raw_text,
                    quantity=parsed.quantity,
                    product_id=p["id"],
                    product_name=p["name"],
                    sku=p["sku"],
                    unit_price=p["unit_price"],
                    match_type="fuzzy",
                    confidence=0.85,
                )
            )
            continue

        # ---- 4. Fuzzy match ----
        scores: list[tuple[float, dict]] = []
        for p in db_products:
            ratio = difflib.SequenceMatcher(
                None,
                norm_query,
                _normalise_product_name(p["name"]),
            ).ratio()
            scores.append((ratio, p))

        scores.sort(key=lambda x: x[0], reverse=True)
        best_score, best_product = scores[0]

        if best_score >= fuzzy_threshold:
            suggestions = [
                {
                    "product_id": p["id"],
                    "product_name": p["name"],
                    "sku": p["sku"],
                    "unit_price": p["unit_price"],
                    "confidence": round(score, 3),
                }
                for score, p in scores[:3]
            ]
            cart_items.append(
                CartItem(
                    raw_text=parsed.raw_text,
                    quantity=parsed.quantity,
                    product_id=best_product["id"],
                    product_name=best_product["name"],
                    sku=best_product["sku"],
                    unit_price=best_product["unit_price"],
                    match_type="fuzzy",
                    confidence=round(best_score, 3),
                    suggestions=suggestions,
                )
            )
        else:
            cart_items.append(
                CartItem(
                    raw_text=parsed.raw_text,
                    quantity=parsed.quantity,
                    product_id=None,
                    product_name=None,
                    sku=None,
                    unit_price=None,
                    match_type="none",
                    confidence=0.0,
                    suggestions=[
                        {
                            "product_id": p["id"],
                            "product_name": p["name"],
                            "sku": p["sku"],
                            "unit_price": p["unit_price"],
                            "confidence": round(score, 3),
                        }
                        for score, p in scores[:3]
                    ],
                )
            )

    return cart_items
