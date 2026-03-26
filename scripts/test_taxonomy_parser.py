#!/usr/bin/env python3
"""
Test the taxonomy parser logic against sample data.

Run with: python scripts/test_taxonomy_parser.py
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.taxonomy_parser import extract_base_and_attributes, build_display_name

# Test cases from real data
TEST_CASES = [
    # Vesta produce style
    ("CARROT-DICE 3/8\"", {
        "base_name": "Carrot",
        "prep": "Diced",
        "cut_size": "3/8\"",
    }),
    ("ONION-RED JUMBO", {
        "base_name": "Onion",
        "variety": "Red",
        "form": "Jumbo",
    }),
    ("CARROT-BABY RAINBOW", {
        "base_name": "Carrot",
        "form": "Baby",
        "variety": "Rainbow",
    }),
    ("BRUSSELS SPROUTS-HALVED", {
        "base_name": "Brussels Sprouts",
        "prep": "Halved",
    }),
    ("CAULIFLOWER-FLORETS", {
        "base_name": "Cauliflower",
        "prep": "Florets",
    }),
    ("SPINACH-BABY", {
        "base_name": "Spinach",
        "form": "Baby",
    }),
    ("CABBAGE-GREEN SHRED 1/16\"", {
        "base_name": "Cabbage",
        "variety": "Green",
        "prep": "Shredded",
        "cut_size": "1/16\"",
    }),
    ("CARROT-PEEL WHOLE JUMBO", {
        "base_name": "Carrot",
        "prep": "Peeled",
        "form": "Jumbo",
    }),

    # Shamrock protein style
    ("[JIT] CHICKEN, BRST SGL SK ON TO NATRL", {
        "base_name": "Chicken",
        "cut": "Breast",
        "skin": "Skin On",
        "grade": "Natural",
    }),
    ("[JIT] CHICKEN, THIGH BNLS SK ON NATRL", {
        "base_name": "Chicken",
        "cut": "Thigh",
        "bone": "Boneless",
        "skin": "Skin On",
        "grade": "Natural",
    }),
    ("[JIT] CHICKEN, THIGH BI SK ON", {
        "base_name": "Chicken",
        "cut": "Thigh",
        "bone": "Bone-In",
        "skin": "Skin On",
    }),
    ("[JIT] CHICKEN, THIGH B&S JULIENNE FZN", {
        "base_name": "Chicken",
        "cut": "Thigh",
        "bone": "Boneless",
        "skin": "Skinless",
        "prep": "Julienne",
        "state": "Frozen",
    }),
    ("[JIT] SALMON, ATLANTIC FLT 3-4LB SKIN OFF FZN", {
        "base_name": "Salmon",
        "variety": "Atlantic",
        "cut": "Fillet",
        "skin": "Skin Off",
        "state": "Frozen",
    }),
    ("[JIT] PORK, LOIN BNLS CC", {
        "base_name": "Pork",
        "cut": "Loin",
        "bone": "Boneless",
    }),
    ("[JIT] CHICKEN, BRST GRND 3/8\" NATRL", {
        "base_name": "Chicken",
        "cut": "Breast",
        "prep": "Ground",
        "cut_size": "3/8\"",
        "grade": "Natural",
    }),
]


def run_tests():
    """Run all test cases and report results."""
    passed = 0
    failed = 0

    print("Testing taxonomy parser...\n")

    for input_name, expected in TEST_CASES:
        result = extract_base_and_attributes(input_name)

        # Check expected values
        errors = []
        for key, expected_val in expected.items():
            actual_val = result.get(key)
            if actual_val != expected_val:
                errors.append(f"  {key}: expected '{expected_val}', got '{actual_val}'")

        if errors:
            failed += 1
            print(f"❌ FAIL: {input_name}")
            for err in errors:
                print(err)
            print(f"   Full result: {result}")
            print()
        else:
            passed += 1
            display_name = build_display_name(result["base_name"], result)
            print(f"✅ PASS: {input_name}")
            print(f"   → {display_name}")
            print()

    print(f"\nResults: {passed} passed, {failed} failed out of {len(TEST_CASES)} tests")

    # Additional examples from CSV data
    print("\n" + "=" * 60)
    print("Additional parsing examples from CSV data:")
    print("=" * 60 + "\n")

    additional = [
        "YAMS-SWEET POTATO OKINAWA",
        "HERB-PARSLEY",
        "HERB-CILANTRO",
        "CARROT-BABY PEEL 1\" TOP",
        "BERRY-BLACKBERRY DRISCOLL",
        "CHILES-JALAPENO",
        "[JIT] CHICKEN, WHL 3UP NATRL",
        "[JIT] CHICKEN, FAJITA MEAT",
        "[JIT] PORK, RACK LOIN 10 BONE FRNCHD P12NC",
        "[JIT] PORK, BUTT BNLS",
        "TAMALE, PORK MILD 2Z",
    ]

    for name in additional:
        result = extract_base_and_attributes(name)
        display = build_display_name(result["base_name"], result)
        attrs = {k: v for k, v in result.items() if v and k != "base_name"}
        print(f"Input:   {name}")
        print(f"Output:  {display}")
        print(f"Attrs:   {attrs}")
        print()

    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
