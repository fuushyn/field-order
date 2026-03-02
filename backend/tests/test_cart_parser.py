"""
Unit tests for cart_parser.py covering:
  - Scenario 1: Exact match test (Image 1 – clean note)
  - Scenario 2: Fuzzy/no match test (Image 2 – tricky note with typos)
  - Scenario 3: Complex mixed / messy test (Image 3 – warehouse scrap paper)
"""
import pytest
from cart_parser import parse_ocr_text, match_items_to_products, ParsedItem


# ---------------------------------------------------------------------------
# OCR text fixtures (simulate what Tesseract returns from each image)
# These represent the *ideal* extracted text for testing matching logic.
# ---------------------------------------------------------------------------

# Image 1 – clean spiral notebook, exact match expected
IMAGE1_OCR_TEXT = """\
Order for Store:
2x Cola Classic 24-pack
1x Granola Bars 48-ct
3x Whole Milk 1 Gallon
2x Paper Towels 12-roll

Total: 4 items.
"""

# Image 2 – yellow paper, red pen, typos / abbreviations
IMAGE2_OCR_TEXT = """\
2x Orange Jce 12pk
1x Mix Nuts 12 box
1x Cheddar block
2x Cleaning spray 6-pack
3x White bread
"""

# Image 3 – warehouse scrap paper, complex revisions, cancellations
IMAGE3_OCR_TEXT = """\
4 cs Sparkling Water 24pk
MAKE THAT 5 CASES
2 Energy Drinks
1 box Crosaants 12-ct
3 boxes Potato Chip Var. Box
~2 cases Beer~
CANCEL BEER - add 1 case BEV-001 instead
"""


# ===========================================================================
# SCENARIO 1 – Exact Match (Image 1)
# ===========================================================================

class TestScenario1ExactMatch:
    """
    Image 1: Clean handwritten note with exact product names.
    All items should be matched exactly (case-insensitive).
    """

    def test_parse_ocr_text_extracts_four_items(self):
        items = parse_ocr_text(IMAGE1_OCR_TEXT)
        assert len(items) == 4, f"Expected 4 items, got {len(items)}: {items}"

    def test_parse_extracts_correct_quantities(self):
        items = parse_ocr_text(IMAGE1_OCR_TEXT)
        qty_map = {i.product_query.lower(): i.quantity for i in items}
        assert qty_map.get("cola classic 24-pack") == 2
        assert qty_map.get("granola bars 48-ct") == 1
        assert qty_map.get("whole milk 1 gallon") == 3
        assert qty_map.get("paper towels 12-roll") == 2

    def test_all_items_exact_match(self, product_dicts):
        items = parse_ocr_text(IMAGE1_OCR_TEXT)
        cart = match_items_to_products(items, product_dicts)
        assert len(cart) == 4
        for ci in cart:
            assert ci.match_type == "exact", (
                f"Expected exact match for '{ci.raw_text}', got '{ci.match_type}'"
            )
            assert ci.confidence == 1.0
            assert ci.product_id is not None
            assert ci.product_name is not None

    def test_correct_products_matched(self, product_dicts):
        items = parse_ocr_text(IMAGE1_OCR_TEXT)
        cart = match_items_to_products(items, product_dicts)
        name_to_cart = {ci.product_name: ci for ci in cart}

        assert "Cola Classic 24-pack" in name_to_cart
        assert "Granola Bars 48-ct" in name_to_cart
        assert "Whole Milk 1 Gallon" in name_to_cart
        assert "Paper Towels 12-roll" in name_to_cart

    def test_correct_quantities_in_cart(self, product_dicts):
        items = parse_ocr_text(IMAGE1_OCR_TEXT)
        cart = match_items_to_products(items, product_dicts)
        qty_map = {ci.product_name: ci.quantity for ci in cart}

        assert qty_map["Cola Classic 24-pack"] == 2
        assert qty_map["Granola Bars 48-ct"] == 1
        assert qty_map["Whole Milk 1 Gallon"] == 3
        assert qty_map["Paper Towels 12-roll"] == 2

    def test_correct_skus_in_cart(self, product_dicts):
        items = parse_ocr_text(IMAGE1_OCR_TEXT)
        cart = match_items_to_products(items, product_dicts)
        sku_map = {ci.sku: ci for ci in cart}

        assert "BEV-001" in sku_map
        assert "SNK-002" in sku_map
        assert "DAI-001" in sku_map
        assert "CLN-002" in sku_map

    def test_no_unmatched_items(self, product_dicts):
        items = parse_ocr_text(IMAGE1_OCR_TEXT)
        cart = match_items_to_products(items, product_dicts)
        unmatched = [ci for ci in cart if ci.match_type == "none"]
        assert len(unmatched) == 0, f"Unexpected unmatched: {unmatched}"

    def test_skip_header_and_total_lines(self):
        items = parse_ocr_text(IMAGE1_OCR_TEXT)
        raw_texts = [i.raw_text.lower() for i in items]
        assert not any("order for" in t for t in raw_texts)
        assert not any("total" in t for t in raw_texts)


# ===========================================================================
# SCENARIO 2 – Fuzzy / No Match (Image 2)
# ===========================================================================

class TestScenario2FuzzyMatch:
    """
    Image 2: Yellow paper, red pen, hurried messy handwriting.
    Items have typos, abbreviations. Fuzzy matching should find best candidates.
    """

    def test_parse_ocr_text_extracts_five_items(self):
        items = parse_ocr_text(IMAGE2_OCR_TEXT)
        assert len(items) == 5, f"Expected 5 items, got {len(items)}: {items}"

    def test_orange_juice_fuzzy_match(self, product_dicts):
        """'Orange Jce 12pk' should fuzzy-match to 'Orange Juice 12-pack'."""
        items = parse_ocr_text("2x Orange Jce 12pk")
        cart = match_items_to_products(items, product_dicts)
        assert len(cart) == 1
        ci = cart[0]
        assert ci.match_type in ("exact", "fuzzy")
        assert ci.product_name == "Orange Juice 12-pack", (
            f"Expected 'Orange Juice 12-pack', got '{ci.product_name}'"
        )
        assert ci.sku == "BEV-002"
        assert ci.quantity == 2

    def test_cheddar_block_fuzzy_match(self, product_dicts):
        """'Cheddar block' should fuzzy-match to 'Cheddar Cheese Block'."""
        items = parse_ocr_text("1x Cheddar block")
        cart = match_items_to_products(items, product_dicts)
        assert len(cart) == 1
        ci = cart[0]
        assert ci.match_type in ("exact", "fuzzy")
        assert ci.product_name == "Cheddar Cheese Block", (
            f"Expected 'Cheddar Cheese Block', got '{ci.product_name}'"
        )
        assert ci.sku == "DAI-002"

    def test_cleaning_spray_fuzzy_match(self, product_dicts):
        """'Cleaning spray 6-pack' should fuzzy-match to 'All-Purpose Cleaner 6-pack'."""
        items = parse_ocr_text("2x Cleaning spray 6-pack")
        cart = match_items_to_products(items, product_dicts)
        assert len(cart) == 1
        ci = cart[0]
        # Should match or suggest All-Purpose Cleaner
        all_names = [ci.product_name] + [s["product_name"] for s in ci.suggestions]
        assert any("Cleaner" in n or "cleaner" in n.lower() for n in all_names if n), (
            f"Expected All-Purpose Cleaner among suggestions. Got: {all_names}"
        )

    def test_mixed_nuts_fuzzy_match(self, product_dicts):
        """'Mix Nuts 12 box' should fuzzy-match to 'Mixed Nuts 12-pack'."""
        items = parse_ocr_text("1x Mix Nuts 12 box")
        cart = match_items_to_products(items, product_dicts)
        assert len(cart) == 1
        ci = cart[0]
        assert ci.product_name == "Mixed Nuts 12-pack", (
            f"Expected 'Mixed Nuts 12-pack', got '{ci.product_name}'"
        )
        assert ci.sku == "SNK-003"

    def test_white_bread_match(self, product_dicts):
        """'White bread' should match 'White Bread Loaf'."""
        items = parse_ocr_text("3x White bread")
        cart = match_items_to_products(items, product_dicts)
        assert len(cart) == 1
        ci = cart[0]
        assert ci.product_name == "White Bread Loaf", (
            f"Expected 'White Bread Loaf', got '{ci.product_name}'"
        )
        assert ci.sku == "BAK-001"

    def test_fuzzy_items_have_suggestions(self, product_dicts):
        """
        Fuzzy-matched items that went through difflib scoring (not substring match)
        should include a suggestions list. Items matched via substring path may have
        an empty suggestions list since the match is already unambiguous.
        """
        items = parse_ocr_text(IMAGE2_OCR_TEXT)
        cart = match_items_to_products(items, product_dicts)
        fuzzy_items = [ci for ci in cart if ci.match_type == "fuzzy"]
        # At least some fuzzy matches exist
        assert len(fuzzy_items) >= 1, "Expected at least one fuzzy-matched item"
        for ci in fuzzy_items:
            assert isinstance(ci.suggestions, list)
            # All fuzzy items must have a product_id (even via substring path)
            assert ci.product_id is not None, (
                f"Fuzzy item '{ci.raw_text}' has no product_id"
            )

    def test_all_items_have_match_or_suggestion(self, product_dicts):
        """Every item in image 2 should have at least a fuzzy match or suggestion."""
        items = parse_ocr_text(IMAGE2_OCR_TEXT)
        cart = match_items_to_products(items, product_dicts)
        for ci in cart:
            has_match = ci.product_id is not None
            has_suggestions = len(ci.suggestions) > 0
            assert has_match or has_suggestions, (
                f"Item '{ci.raw_text}' has no match or suggestions"
            )


# ===========================================================================
# SCENARIO 3 – Complex / Messy (Image 3)
# ===========================================================================

class TestScenario3ComplexMixed:
    """
    Image 3: Warehouse scrap paper with revisions, cancellations, SKU references,
    inconsistent formatting and misspellings.
    """

    def test_parse_extracts_expected_items(self):
        """
        After processing revisions and cancellations, should have:
        - Sparkling Water 24pk (qty revised to 5)
        - Energy Drinks (qty 2)
        - Crosaants 12-ct / Croissants 12-ct (qty 1)
        - Potato Chip Var. Box (qty 3)
        - BEV-001 added instead of Beer (qty 1)
        Beer (~2 cases Beer~) should be cancelled/excluded.
        """
        items = parse_ocr_text(IMAGE3_OCR_TEXT)
        queries = [i.product_query.lower() for i in items]
        # Beer should NOT appear as a non-cancelled item
        assert not any("beer" in q for q in queries), (
            f"Beer should be cancelled, but found in items: {queries}"
        )
        # BEV-001 substitution should appear
        assert any("bev-001" in i.product_query.upper() or "SKU:BEV-001" in i.product_query for i in items), (
            f"Expected BEV-001 SKU in items after 'add instead'. Items: {[i.product_query for i in items]}"
        )

    def test_make_that_revision_updates_quantity(self):
        """
        '4 cs Sparkling Water 24pk' followed by 'MAKE THAT 5 CASES'
        should result in quantity=5.
        """
        items = parse_ocr_text(IMAGE3_OCR_TEXT)
        sparkling = next(
            (i for i in items if "sparkling" in i.product_query.lower()), None
        )
        assert sparkling is not None, "Sparkling Water item not found"
        assert sparkling.quantity == 5, (
            f"Expected quantity 5 after revision, got {sparkling.quantity}"
        )

    def test_cancelled_beer_not_in_items(self):
        """Lines with ~strikethrough~ markers should not appear as cart items."""
        items = parse_ocr_text(IMAGE3_OCR_TEXT)
        for item in items:
            assert "beer" not in item.product_query.lower(), (
                f"Cancelled beer item should not appear: {item}"
            )

    def test_bev001_added_instead_of_beer(self, product_dicts):
        """'CANCEL BEER – add 1 case BEV-001 instead' should inject BEV-001."""
        items = parse_ocr_text(IMAGE3_OCR_TEXT)
        cart = match_items_to_products(items, product_dicts)

        cola_items = [ci for ci in cart if ci.sku == "BEV-001"]
        assert len(cola_items) >= 1, (
            f"Expected Cola Classic (BEV-001) in cart from 'add instead'. "
            f"Cart SKUs: {[ci.sku for ci in cart]}"
        )
        assert cola_items[0].quantity == 1

    def test_croissants_misspelling_matched(self, product_dicts):
        """'Crosaants 12-ct' should fuzzy-match to 'Croissants 12-ct'."""
        items = parse_ocr_text("1 box Crosaants 12-ct")
        cart = match_items_to_products(items, product_dicts)
        assert len(cart) == 1
        ci = cart[0]
        assert ci.product_name == "Croissants 12-ct", (
            f"Expected 'Croissants 12-ct', got '{ci.product_name}'"
        )
        assert ci.sku == "BAK-003"

    def test_potato_chip_var_box_matched(self, product_dicts):
        """'Potato Chip Var. Box' should match 'Potato Chips Variety Box'."""
        items = parse_ocr_text("3 boxes Potato Chip Var. Box")
        cart = match_items_to_products(items, product_dicts)
        assert len(cart) == 1
        ci = cart[0]
        assert ci.product_name == "Potato Chips Variety Box", (
            f"Expected 'Potato Chips Variety Box', got '{ci.product_name}'"
        )
        assert ci.sku == "SNK-001"
        assert ci.quantity == 3

    def test_energy_drinks_matched(self, product_dicts):
        """'Energy Drinks' should match 'Energy Drink 12-pack'."""
        items = parse_ocr_text("2 Energy Drinks")
        cart = match_items_to_products(items, product_dicts)
        assert len(cart) == 1
        ci = cart[0]
        assert ci.product_name == "Energy Drink 12-pack", (
            f"Expected 'Energy Drink 12-pack', got '{ci.product_name}'"
        )
        assert ci.sku == "BEV-004"
        assert ci.quantity == 2

    def test_sparkling_water_matched(self, product_dicts):
        """'Sparkling Water 24pk' with revised qty=5 should match 'Sparkling Water 24-pack'."""
        items = parse_ocr_text(IMAGE3_OCR_TEXT)
        cart = match_items_to_products(items, product_dicts)
        sparkling = next(
            (ci for ci in cart if ci.sku == "BEV-003"), None
        )
        assert sparkling is not None, (
            f"Sparkling Water (BEV-003) not found in cart. "
            f"Cart: {[(ci.product_name, ci.sku) for ci in cart]}"
        )
        assert sparkling.quantity == 5, (
            f"Expected revised quantity 5, got {sparkling.quantity}"
        )

    def test_full_scenario3_cart(self, product_dicts):
        """
        Full scenario 3 cart should contain 5 items (not beer).
        Expected: Sparkling Water, Energy Drink, Croissants, Potato Chips, Cola Classic.
        """
        items = parse_ocr_text(IMAGE3_OCR_TEXT)
        cart = match_items_to_products(items, product_dicts)

        expected_skus = {"BEV-003", "BEV-004", "BAK-003", "SNK-001", "BEV-001"}
        actual_skus = {ci.sku for ci in cart if ci.sku is not None}

        assert expected_skus == actual_skus, (
            f"Expected SKUs {expected_skus}, got {actual_skus}"
        )


# ===========================================================================
# Additional unit tests for cart_parser helpers
# ===========================================================================

class TestParseOcrTextHelpers:
    """Unit tests for individual parser behaviours."""

    def test_skip_order_header(self):
        text = "Order for Store:\n2x Cola Classic 24-pack"
        items = parse_ocr_text(text)
        assert len(items) == 1
        assert "cola" in items[0].product_query.lower()

    def test_skip_total_line(self):
        text = "2x Cola Classic 24-pack\nTotal: 1 item."
        items = parse_ocr_text(text)
        assert len(items) == 1

    def test_case_insensitive_quantity_prefix(self):
        text = "3X Granola Bars 48-ct"
        items = parse_ocr_text(text)
        assert len(items) == 1
        assert items[0].quantity == 3

    def test_unit_prefix_cs(self):
        text = "4 cs Sparkling Water 24-pack"
        items = parse_ocr_text(text)
        assert len(items) == 1
        assert items[0].quantity == 4
        assert "sparkling" in items[0].product_query.lower()

    def test_unit_prefix_boxes(self):
        text = "3 boxes Potato Chips Variety Box"
        items = parse_ocr_text(text)
        assert len(items) == 1
        assert items[0].quantity == 3

    def test_strikethrough_line_excluded(self):
        text = "~2 cases Beer~\n1x Cola Classic 24-pack"
        items = parse_ocr_text(text)
        queries = [i.product_query.lower() for i in items]
        assert not any("beer" in q for q in queries)
        assert any("cola" in q for q in queries)

    def test_make_that_revision(self):
        text = "4 cs Sparkling Water 24-pack\nMAKE THAT 5 CASES"
        items = parse_ocr_text(text)
        assert len(items) == 1
        assert items[0].quantity == 5

    def test_empty_text(self):
        items = parse_ocr_text("")
        assert items == []

    def test_blank_lines_ignored(self):
        text = "\n\n2x Cola Classic 24-pack\n\n"
        items = parse_ocr_text(text)
        assert len(items) == 1

    def test_sku_lookup(self, product_dicts):
        """SKU: prefix should trigger direct SKU lookup."""
        items = [ParsedItem(raw_text="SKU:BEV-001", quantity=2, product_query="SKU:BEV-001")]
        cart = match_items_to_products(items, product_dicts)
        assert len(cart) == 1
        assert cart[0].product_name == "Cola Classic 24-pack"
        assert cart[0].match_type == "exact"
        assert cart[0].quantity == 2

    def test_unknown_sku_returns_none_match(self, product_dicts):
        items = [ParsedItem(raw_text="SKU:ZZZ-999", quantity=1, product_query="SKU:ZZZ-999")]
        cart = match_items_to_products(items, product_dicts)
        assert cart[0].match_type == "none"
        assert cart[0].product_id is None


class TestMatchItemsToProducts:
    """Unit tests for the match_items_to_products function."""

    def test_exact_match_case_insensitive(self, product_dicts):
        items = [ParsedItem(raw_text="2x cola classic 24-pack", quantity=2,
                            product_query="cola classic 24-pack")]
        cart = match_items_to_products(items, product_dicts)
        assert cart[0].match_type == "exact"
        assert cart[0].product_name == "Cola Classic 24-pack"

    def test_fuzzy_match_returns_best_candidate(self, product_dicts):
        items = [ParsedItem(raw_text="2x Orange Jce 12pk", quantity=2,
                            product_query="Orange Jce 12pk")]
        cart = match_items_to_products(items, product_dicts)
        assert cart[0].product_name == "Orange Juice 12-pack"
        assert cart[0].match_type in ("fuzzy", "exact")

    def test_no_match_returns_suggestions(self, product_dicts):
        items = [ParsedItem(raw_text="1x Unicorn Milk 999pk", quantity=1,
                            product_query="Unicorn Milk 999pk")]
        cart = match_items_to_products(items, product_dicts)
        # Should still return suggestions even if confidence is low
        assert isinstance(cart[0].suggestions, list)

    def test_quantity_preserved(self, product_dicts):
        items = [ParsedItem(raw_text="7x Granola Bars 48-ct", quantity=7,
                            product_query="Granola Bars 48-ct")]
        cart = match_items_to_products(items, product_dicts)
        assert cart[0].quantity == 7

    def test_unit_price_returned(self, product_dicts):
        items = [ParsedItem(raw_text="1x Cola Classic 24-pack", quantity=1,
                            product_query="Cola Classic 24-pack")]
        cart = match_items_to_products(items, product_dicts)
        assert cart[0].unit_price == 18.99
