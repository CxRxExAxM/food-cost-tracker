#!/usr/bin/env python3
"""
Taxonomy Parser Module

Contains the logic for parsing common_product names into structured attributes.
This module has no database dependencies and can be imported independently.
"""
import re


# =============================================================================
# Attribute Abbreviation Mappings
# =============================================================================

# Common abbreviations found in product descriptions
ABBREVIATIONS = {
    # Bone
    "BNLS": "Boneless",
    "B&S": "Boneless Skinless",
    "BI": "Bone-In",
    "BONE-IN": "Bone-In",
    "BONE IN": "Bone-In",
    "BONELESS": "Boneless",

    # Skin
    "SK ON": "Skin On",
    "SKON": "Skin On",
    "SK OFF": "Skin Off",
    "SKIN OFF": "Skin Off",
    "SKINLESS": "Skinless",
    "SKLS": "Skinless",

    # State
    "FZN": "Frozen",
    "FROZEN": "Frozen",
    "FRZ": "Frozen",
    "IQF": "IQF",
    "REFRIG": "Fresh",
    "REF": "Fresh",
    "FRESH": "Fresh",

    # Grade
    "NATRL": "Natural",
    "NATURAL": "Natural",
    "ORGANIC": "Organic",
    "CHOICE": "Choice",
    "PRIME": "Prime",
    "SELECT": "Select",

    # Form/Size
    "JUMBO": "Jumbo",
    "JMB": "Jumbo",
    "JMBO": "Jumbo",
    "BABY": "Baby",
    "PETITE": "Petite",
    "LARGE": "Large",
    "LRG": "Large",
    "MEDIUM": "Medium",
    "MED": "Medium",
    "SMALL": "Small",
    "SML": "Small",
    "COLOSSAL": "Colossal",
    "WHOLE": "Whole",
    "WHL": "Whole",

    # Prep
    "DICE": "Diced",
    "DICED": "Diced",
    "SLICED": "Sliced",
    "SLICE": "Sliced",
    "SHRED": "Shredded",
    "SHREDDED": "Shredded",
    "JULIENNE": "Julienne",
    "PEEL": "Peeled",
    "PEELED": "Peeled",
    "HALVED": "Halved",
    "QUARTERED": "Quartered",
    "CHOPPED": "Chopped",
    "MINCED": "Minced",
    "GRND": "Ground",
    "GROUND": "Ground",
    "FLORETS": "Florets",

    # Protein cuts
    "BRST": "Breast",
    "BREAST": "Breast",
    "THIGH": "Thigh",
    "THI": "Thigh",
    "LEG": "Leg",
    "WING": "Wing",
    "TENDER": "Tender",
    "TNDR": "Tender",
    "LOIN": "Loin",
    "BUTT": "Butt",
    "RACK": "Rack",
    "SHOULDER": "Shoulder",
    "SHLDR": "Shoulder",
    "FLT": "Fillet",
    "FILLET": "Fillet",
    "STEAK": "Steak",
}

# Category to subcategory mapping
CATEGORY_HINTS = {
    "Produce": {
        "vegetables": ["carrot", "onion", "celery", "broccoli", "cauliflower", "spinach",
                       "cabbage", "brussels", "potato", "yam", "squash", "pepper", "tomato",
                       "cucumber", "lettuce", "kale", "chard", "asparagus", "artichoke",
                       "zucchini", "eggplant", "mushroom", "corn", "pea", "bean", "beet"],
        "fruits": ["apple", "banana", "berry", "orange", "lemon", "lime", "grape", "melon",
                   "mango", "pineapple", "peach", "pear", "plum", "cherry", "fig", "date"],
        "herbs": ["parsley", "cilantro", "basil", "thyme", "rosemary", "sage", "mint",
                  "oregano", "dill", "chive", "tarragon"],
    },
    "Protein": {
        "poultry": ["chicken", "turkey", "duck", "quail", "cornish", "hen"],
        "beef": ["beef", "steak", "ribeye", "sirloin", "brisket", "chuck"],
        "pork": ["pork", "bacon", "ham", "pig"],
        "seafood": ["salmon", "tuna", "cod", "halibut", "shrimp", "crab", "lobster",
                    "scallop", "mussel", "clam", "oyster", "fish", "tilapia", "trout"],
        "lamb": ["lamb", "mutton"],
    }
}


def normalize_name(name: str) -> str:
    """Normalize product name for consistent parsing."""
    # Remove common prefixes
    name = re.sub(r'^\[JIT\]\s*', '', name)
    name = name.strip().upper()
    return name


def extract_base_and_attributes(common_name: str, category: str = None) -> dict:
    """
    Parse a common_product name into base ingredient and attributes.

    Returns dict with:
    - base_name: str
    - variety: str or None
    - form: str or None
    - prep: str or None
    - cut_size: str or None
    - cut: str or None
    - bone: str or None
    - skin: str or None
    - grade: str or None
    - state: str or None
    """
    result = {
        "base_name": None,
        "variety": None,
        "form": None,
        "prep": None,
        "cut_size": None,
        "cut": None,
        "bone": None,
        "skin": None,
        "grade": None,
        "state": None,
    }

    name = normalize_name(common_name)

    # Try to split by common delimiters
    # Vesta style: "CARROT-DICE 3/8""
    # Shamrock style: "CHICKEN, BRST SGL SK ON NATRL"

    if "-" in name and "," not in name:
        # Vesta style (produce)
        parts = name.split("-", 1)
        result["base_name"] = parts[0].strip().title()
        if len(parts) > 1:
            attrs = parts[1].strip()
        else:
            attrs = ""
    elif "," in name:
        # Shamrock style (protein)
        parts = name.split(",", 1)
        result["base_name"] = parts[0].strip().title()
        if len(parts) > 1:
            attrs = parts[1].strip()
        else:
            attrs = ""
    else:
        # Single word or unknown format
        result["base_name"] = name.title()
        attrs = ""

    if not attrs:
        return result

    # Extract cut size (e.g., 3/8", 1/4", 1x1)
    cut_size_match = re.search(r'(\d+/\d+["\']?|\d+x\d+["\']?|\d+["\']\s*(?:TOP)?)', attrs)
    if cut_size_match:
        result["cut_size"] = cut_size_match.group(1).replace('"', '"').replace("'", "'")
        attrs = attrs.replace(cut_size_match.group(0), " ")

    # Tokenize remaining attributes - handle both comma and space separation
    # First replace commas with spaces, then split and clean up
    attrs_cleaned = attrs.replace(",", " ")
    tokens = [t.strip().upper() for t in attrs_cleaned.split() if t.strip()]

    # Multi-word abbreviation matching
    attrs_upper = " " + attrs.upper() + " "

    # Check for specific patterns first (B&S is common)
    if " B&S " in attrs_upper or attrs_upper.startswith("B&S ") or attrs_upper.endswith(" B&S"):
        result["bone"] = "Boneless"
        result["skin"] = "Skinless"
        attrs_upper = attrs_upper.replace("B&S", " ")

    # Check for multi-word patterns
    for abbr, expanded in ABBREVIATIONS.items():
        if " " in abbr and f" {abbr} " in attrs_upper:
            # Multi-word match
            if expanded in ["Boneless", "Boneless Skinless"]:
                result["bone"] = "Boneless"
                if expanded == "Boneless Skinless":
                    result["skin"] = "Skinless"
            elif expanded in ["Bone-In"]:
                result["bone"] = "Bone-In"
            elif expanded in ["Skin On", "Skin Off", "Skinless"]:
                result["skin"] = expanded
            elif expanded in ["Frozen", "Fresh", "IQF"]:
                result["state"] = expanded
            elif expanded in ["Natural", "Organic", "Choice", "Prime", "Select"]:
                result["grade"] = expanded
            attrs_upper = attrs_upper.replace(f" {abbr} ", " ")

    # Single-word matching
    for token in tokens:
        if token in ABBREVIATIONS:
            expanded = ABBREVIATIONS[token]

            # Categorize the attribute
            if expanded in ["Boneless", "Bone-In"]:
                result["bone"] = expanded
            elif expanded in ["Skin On", "Skin Off", "Skinless"]:
                result["skin"] = expanded
            elif expanded in ["Frozen", "Fresh", "IQF"]:
                result["state"] = expanded
            elif expanded in ["Natural", "Organic", "Choice", "Prime", "Select"]:
                result["grade"] = expanded
            elif expanded in ["Jumbo", "Baby", "Petite", "Large", "Medium", "Small", "Colossal", "Whole"]:
                result["form"] = expanded
            elif expanded in ["Diced", "Sliced", "Shredded", "Julienne", "Peeled", "Halved",
                              "Quartered", "Chopped", "Minced", "Ground", "Florets"]:
                result["prep"] = expanded
            elif expanded in ["Breast", "Thigh", "Leg", "Wing", "Tender", "Loin", "Butt",
                              "Rack", "Shoulder", "Fillet", "Steak"]:
                result["cut"] = expanded

        # Check for color/variety
        elif token in ["RED", "ORANGE", "YELLOW", "WHITE", "GREEN", "PURPLE", "RAINBOW",
                       "TRICOLOR", "ATLANTIC", "PACIFIC", "WILD", "ROMA", "CHERRY", "GRAPE",
                       "BEEFSTEAK", "RUSSET", "YUKON", "FINGERLING", "SWEET"]:
            result["variety"] = token.title()

    return result


def determine_category_subcategory(base_name: str) -> tuple:
    """Determine category and subcategory based on base ingredient name."""
    base_lower = base_name.lower()

    for category, subcats in CATEGORY_HINTS.items():
        for subcat, keywords in subcats.items():
            if any(kw in base_lower for kw in keywords):
                return category, subcat.title()

    return None, None


def build_display_name(base_name: str, attrs: dict) -> str:
    """Build a display name from base and attributes."""
    parts = [base_name]

    # Add attributes in consistent order
    if attrs.get("variety"):
        parts.append(attrs["variety"])
    if attrs.get("form"):
        parts.append(attrs["form"])
    if attrs.get("cut"):
        parts.append(attrs["cut"])
    if attrs.get("bone"):
        parts.append(attrs["bone"])
    if attrs.get("skin"):
        parts.append(attrs["skin"])
    if attrs.get("prep"):
        parts.append(attrs["prep"])
    if attrs.get("cut_size"):
        parts.append(attrs["cut_size"])
    if attrs.get("grade"):
        parts.append(attrs["grade"])
    if attrs.get("state"):
        parts.append(attrs["state"])

    return ", ".join(parts)
