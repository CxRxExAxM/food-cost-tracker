"""
EHC Module Seeder Service

Seeds the EHC (Environmental Health Compliance) audit structure:
- 6 Sections
- 26 Subsections (A-Z)
- 125 Audit Points
- 47 Records (37 EHC + 10 SCP-specific)
- Outlet-Record mappings
- Point-Record links

Based on EHC audit checklist for Fairmont Scottsdale Princess.
"""

from datetime import date, datetime
from typing import Dict, List, Optional
from ..logger import get_logger

logger = get_logger(__name__)


# ============================================
# SECTION DEFINITIONS (6 sections)
# ============================================
SECTIONS = [
    {"ref_number": 1, "name": "Purchasing, Receival & Food Storage", "sort_order": 1},
    {"ref_number": 2, "name": "Food Handling & Preparation", "sort_order": 2},
    {"ref_number": 3, "name": "Bar, IRD & Cleaning", "sort_order": 3},
    {"ref_number": 4, "name": "Good Hygiene Practices", "sort_order": 4},
    {"ref_number": 5, "name": "Support Documentation", "sort_order": 5},
    {"ref_number": 6, "name": "Special Circumstances", "sort_order": 6},
]


# ============================================
# SUBSECTION DEFINITIONS (26 subsections A-Z)
# Maps subsection code to (section_number, name, sort_order)
# ============================================
SUBSECTIONS = {
    # Section 1: Purchasing, Receival & Food Storage
    "A": (1, "Purchasing - Approved Suppliers", 1),
    "B": (1, "Receival & Delivery", 2),
    "C": (1, "Food Storage", 3),
    "D": (1, "Defrosting", 4),

    # Section 2: Food Handling & Preparation
    "E": (2, "Food Handling - Cross Contamination", 5),
    "F": (2, "Cooking & Reheating", 6),
    "G": (2, "Cooling of Food", 7),
    "H": (2, "Hot Holding", 8),
    "I": (2, "Food Display & Service", 9),
    "J": (2, "Thermometers", 10),

    # Section 3: Bar, IRD & Cleaning
    "K": (3, "Bar Operations", 11),
    "L": (3, "In-Room Dining (IRD)", 12),
    "M": (3, "Cleaning & Sanitation", 13),
    "N": (3, "Maintenance & Facilities", 14),

    # Section 4: Good Hygiene Practices
    "O": (4, "Personal Hygiene & Food Handler Behavior", 15),
    "P": (4, "Pest Control", 16),
    "Q": (4, "Waste Management", 17),

    # Section 5: Support Documentation
    "R": (5, "Training Records", 18),
    "S": (5, "Water Quality", 19),
    "T": (5, "Food Safety Management System", 20),
    "U": (5, "Guest Room Food Safety", 21),

    # Section 6: Special Circumstances
    "V": (6, "Raw Egg Preparations", 22),
    "W": (6, "Allergen Management", 23),
    "X": (6, "Food Washing", 24),
    "Y": (6, "Glass & Wood Policy", 25),
    "Z": (6, "Regulatory & Signage", 26),
}


# ============================================
# AUDIT POINTS (125 questions)
# Format: (ref_code, question_text, nc_level, max_score, responsible_area)
# NC Levels: 1=Critical, 2=Operational, 3=Structural, 4=Administrative
# ============================================
AUDIT_POINTS = [
    # Subsection A: Purchasing - Approved Suppliers
    ("A1", "Are all food suppliers approved and listed?", 4, 1.0, "Office"),
    ("A2", "Is there a supplier visit checklist on file?", 4, 0.5, "Office"),

    # Subsection B: Receival & Delivery
    ("B1", "Are food delivery records maintained?", 4, 1.0, "Office"),
    ("B2", "Is there a rejection record for non-conforming deliveries?", 4, 0.5, "Office"),

    # Subsection C: Food Storage
    ("C1", "Are refrigerator temperatures recorded and within range (0-5C)?", 1, 2.0, "All Kitchens"),
    ("C2", "Are freezer temperatures recorded and within range (-18C or below)?", 1, 2.0, "All Kitchens"),
    ("C3", "Are dry storage areas clean and organized?", 3, 0.5, "All Kitchens"),
    ("C4", "Is food stored off the floor (minimum 6 inches)?", 2, 0.5, "All Kitchens"),
    ("C5", "Are foods covered and labeled with dates?", 2, 1.0, "All Kitchens"),
    ("C6", "Is there proper separation of raw and cooked foods?", 1, 2.0, "All Kitchens"),
    ("C7", "Are chemicals stored separately from food?", 1, 1.5, "All Kitchens"),
    ("C8", "Is FIFO (First In, First Out) being followed?", 2, 0.5, "All Kitchens"),
    ("C9", "Are walk-in coolers clean and well-maintained?", 3, 0.5, "All Kitchens"),
    ("C10", "Are temperature logs complete and current?", 4, 1.0, "All Kitchens"),

    # Subsection D: Defrosting
    ("D1", "Are defrosting records maintained?", 4, 0.5, "All Kitchens"),
    ("D2", "Is food defrosted safely (refrigerator, cold water, microwave)?", 1, 1.5, "All Kitchens"),
    ("D3", "Is defrosted food used within appropriate timeframe?", 2, 0.5, "All Kitchens"),

    # Subsection E: Food Handling - Cross Contamination
    ("E1", "Are separate cutting boards used for raw and cooked foods?", 1, 2.0, "All Kitchens"),
    ("E2", "Is proper hand washing observed between tasks?", 1, 2.0, "All Kitchens"),

    # Subsection F: Cooking & Reheating
    ("F1", "Are cooking/reheating temperatures recorded (minimum 74C)?", 1, 2.5, "All Kitchens"),
    ("F2", "Are menu items with raw ingredients properly disclosed?", 2, 0.5, "All Outlets"),

    # Subsection G: Cooling of Food
    ("G1", "Are cooling records maintained (2-hour/4-hour rule)?", 1, 2.0, "All Kitchens"),
    ("G2", "Is proper cooling equipment available and used?", 2, 0.5, "All Kitchens"),

    # Subsection H: Hot Holding
    ("H1", "Are hot holding temperatures maintained above 60C?", 1, 2.0, "All Outlets"),

    # Subsection I: Food Display & Service
    ("I1", "Are food display temperatures recorded?", 4, 0.5, "Casual, Dish, Gold"),
    ("I2", "Are sneeze guards in place where required?", 2, 0.5, "Buffet Outlets"),
    ("I3", "Is displayed food protected from contamination?", 2, 1.0, "All Outlets"),
    ("I4", "Are serving utensils clean and properly stored?", 2, 0.5, "All Outlets"),
    ("I5", "Is food rotation practiced during service?", 2, 0.5, "Buffet Outlets"),

    # Subsection J: Thermometers
    ("J1", "Are thermometers available in all food storage areas?", 2, 0.5, "All Kitchens"),
    ("J2", "Is there a thermometer register maintained?", 4, 0.5, "All Kitchens"),
    ("J3", "Are thermometers calibrated monthly?", 4, 1.0, "All Kitchens"),
    ("J4", "Are probe wipes available for thermometer sanitation?", 2, 0.25, "All Kitchens"),

    # Subsection K: Bar Operations
    ("K1", "Are glasswasher temperatures recorded (60C wash, 82C rinse)?", 2, 1.0, "All Bars"),
    ("K2", "Are dishwasher temperatures recorded?", 2, 1.0, "Dish"),
    ("K3", "Are ice machines clean and maintained?", 2, 1.0, "All Outlets"),
    ("K4", "Is ice machine cleaning record on file?", 4, 0.5, "Office"),
    ("K5", "Are ice scoops stored properly (not in ice)?", 2, 0.5, "All Outlets"),
    ("K6", "Are garnishes stored properly and fresh?", 2, 0.5, "All Bars"),
    ("K7", "Are bar mats and speed rails clean?", 3, 0.25, "All Bars"),
    ("K8", "Are beer lines cleaned regularly?", 2, 0.5, "Plaza, Toro, Pools"),
    ("K9", "Is draft line cleaning record maintained?", 4, 0.5, "Plaza, Toro, Pools"),
    ("K10", "Are cocktail ingredients properly dated?", 2, 0.5, "All Bars"),
    ("K11", "Is bar equipment (blenders, juicers) cleaned regularly?", 2, 0.5, "All Bars"),
    ("K12", "Are glass racks clean and in good condition?", 3, 0.25, "All Bars"),

    # Subsection L: In-Room Dining (IRD)
    ("L1", "Is IRD food properly covered during transport?", 2, 0.5, "IRD"),

    # Subsection M: Cleaning & Sanitation
    ("M1", "Are cleaning schedules posted and followed?", 4, 0.5, "All Kitchens"),
    ("M2", "Are cleaning chemicals properly diluted?", 2, 0.5, "All Kitchens"),
    ("M3", "Are sanitizer concentrations tested and recorded?", 1, 1.0, "All Kitchens"),
    ("M4", "Are floors, walls, and ceilings clean?", 3, 0.5, "All Kitchens"),
    ("M5", "Are hoods and exhaust filters clean?", 3, 0.5, "All Kitchens"),
    ("M6", "Are drains clean and functioning?", 3, 0.5, "All Kitchens"),
    ("M7", "Is cleaning equipment stored properly?", 3, 0.25, "All Kitchens"),
    ("M8", "Are cloth towels properly stored and sanitized?", 2, 0.5, "All Kitchens"),
    ("M9", "Are dishwasher temperatures at required levels?", 2, 1.0, "Dish"),
    ("M10", "Is dishwasher detergent/rinse aid properly dispensing?", 2, 0.5, "Dish"),
    ("M11", "Are deep cleaning records maintained?", 4, 0.5, "All Kitchens"),
    ("M12", "Are SDS/MSDS sheets accessible?", 4, 0.5, "Office"),

    # Subsection N: Maintenance & Facilities
    ("N1", "Are floors in good repair (no cracks, holes)?", 3, 0.5, "All Kitchens"),
    ("N2", "Are walls and ceilings in good repair?", 3, 0.5, "All Kitchens"),
    ("N3", "Is equipment in good working condition?", 2, 0.5, "All Kitchens"),
    ("N4", "Are lights adequate and protected?", 3, 0.25, "All Kitchens"),
    ("N5", "Is there a maintenance defect reporting system?", 4, 0.5, "Office"),
    ("N6", "Are doors and windows properly screened?", 3, 0.25, "All Kitchens"),
    ("N7", "Is ventilation adequate?", 3, 0.25, "All Kitchens"),

    # Subsection O: Personal Hygiene & Food Handler Behavior
    ("O1", "Are food handlers wearing clean uniforms?", 2, 0.5, "All Outlets"),
    ("O2", "Are hats/hair restraints worn properly?", 2, 0.5, "All Kitchens"),
    ("O3", "Are gloves changed appropriately?", 1, 1.0, "All Kitchens"),
    ("O4", "Is jewelry policy followed (no watches, rings)?", 2, 0.5, "All Kitchens"),
    ("O5", "Are hand wash stations properly equipped?", 2, 0.5, "All Kitchens"),
    ("O6", "Is hand washing observed at appropriate times?", 1, 2.0, "All Kitchens"),
    ("O7", "Is there no evidence of eating in food prep areas?", 2, 0.5, "All Kitchens"),
    ("O8", "Is there no evidence of smoking in food areas?", 2, 0.5, "All Kitchens"),
    ("O9", "Are staff illness reporting procedures followed?", 1, 1.5, "All Outlets"),
    ("O10", "Is personal hygiene signage posted?", 4, 0.25, "All Kitchens"),
    ("O11", "Are staff lockers/changing areas separate from food areas?", 3, 0.25, "All Kitchens"),
    ("O12", "Are cuts and wounds properly covered?", 1, 1.0, "All Kitchens"),
    ("O13", "Is bare-hand contact with ready-to-eat food avoided?", 1, 1.5, "All Kitchens"),
    ("O14", "Are disposable gloves single-use only?", 2, 0.5, "All Kitchens"),

    # Subsection P: Pest Control
    ("P1", "Is there a pest sighting log?", 4, 0.5, "Office"),
    ("P2", "Is there evidence of pest activity?", 1, 2.0, "All Areas"),
    ("P3", "Are openings sealed to prevent pest entry?", 3, 0.5, "All Areas"),
    ("P4", "Is there a valid pest control contract?", 4, 0.5, "Office"),
    ("P5", "Is pest control insurance documentation on file?", 4, 0.25, "Office"),
    ("P6", "Is there a bait station map on file?", 4, 0.25, "Office"),
    ("P7", "Is there an approved pesticide list?", 4, 0.25, "Office"),
    ("P8", "Are pesticide usage records maintained?", 4, 0.5, "Office"),

    # Subsection Q: Waste Management
    ("Q1", "Are waste bins covered and emptied regularly?", 2, 0.5, "All Areas"),
    ("Q2", "Is waste area clean and separate from food areas?", 3, 0.5, "All Areas"),

    # Subsection R: Training Records
    ("R1", "Are food safety training records on file?", 4, 1.0, "Office"),
    ("R2", "Is training material current and accessible?", 4, 0.5, "Office"),
    ("R3", "Is there a certified hygiene champion on staff?", 4, 0.5, "Office"),

    # Subsection S: Water Quality
    ("S1", "Are water testing records maintained (quarterly)?", 4, 0.5, "Office"),

    # Subsection T: Food Safety Management System
    ("T1", "Are food poisoning records/investigations on file?", 4, 0.5, "Office"),
    ("T2", "Is there an internal food safety audit completed?", 4, 1.5, "Office"),
    ("T3", "Are microbial lab test results on file?", 4, 0.5, "Office"),
    ("T4", "Are swabbing/environmental testing records maintained?", 4, 0.5, "Office"),
    ("T5", "Are pH testing records maintained (where applicable)?", 4, 0.25, "Toro"),
    ("T6", "Is there a food sample retention log (14 days)?", 4, 0.5, "MK"),
    ("T7", "Are non-conformance records documented?", 4, 0.5, "Office"),
    ("T8", "Are corrective actions documented and followed up?", 4, 0.5, "Office"),

    # Subsection U: Guest Room Food Safety
    ("U1", "Are guest room glasses properly sanitized?", 2, 0.5, "Housekeeping"),
    ("U2", "Are room swabbing records maintained?", 4, 0.25, "Office"),

    # Subsection V: Raw Egg Preparations
    ("V1", "Are raw egg preparations properly handled and disclosed?", 2, 0.5, "All Kitchens"),

    # Subsection W: Allergen Management
    ("W1", "Is there an allergen matrix for all outlets?", 4, 1.0, "All Outlets"),
    ("W2", "Are staff trained on allergen awareness?", 4, 0.5, "All Outlets"),
    ("W3", "Are allergen ingredients clearly identified?", 2, 0.5, "All Outlets"),
    ("W4", "Is there a process to handle allergen requests?", 2, 0.5, "All Outlets"),
    ("W5", "Are separate utensils used for allergen-free prep?", 2, 0.5, "All Kitchens"),

    # Subsection X: Food Washing
    ("X1", "Are fruits and vegetables washed before use?", 2, 1.0, "GM"),
    ("X2", "Is there a food washing record?", 4, 0.5, "GM"),
    ("X3", "Is produce wash solution at correct concentration?", 2, 0.5, "GM"),
    ("X4", "Are wash sinks designated for produce only?", 3, 0.25, "GM"),

    # Subsection Y: Glass & Wood Policy
    ("Y1", "Is there a glass breakage procedure?", 3, 0.25, "All Areas"),
    ("Y2", "Is wood equipment (cutting boards) properly maintained?", 3, 0.25, "All Kitchens"),

    # Subsection Z: Regulatory & Signage
    ("Z1", "Are notice board documents current?", 4, 0.25, "All Outlets"),
    ("Z2", "Is required signage posted (hand wash, no smoking)?", 4, 0.25, "All Areas"),
    ("Z3", "Are employee health posters displayed?", 4, 0.25, "Back of House"),
    ("Z4", "Is food safety policy posted?", 4, 0.25, "All Kitchens"),
    ("Z5", "Are emergency contact numbers posted?", 4, 0.25, "All Areas"),
    ("Z6", "Is the HACCP program review record current?", 4, 0.5, "Office"),
    ("Z7", "Is doggy bag/leftover policy followed?", 3, 0.25, "All Outlets"),
    ("Z8", "Is health department license/permit displayed?", 4, 0.25, "Main Entrance"),
    ("Z9", "Is food safety team record on file?", 4, 0.5, "Office"),
    ("Z10", "Any other comments or observations?", 4, 0.25, "All Areas"),
]


# ============================================
# RECORD DEFINITIONS (47 records)
# Format: (record_number, name, record_type, location_type, responsibility_code, is_physical_only, notes)
# ============================================
RECORDS = [
    # Standard EHC Records (Outlet Book)
    ("3", "Food Storage Temperature", "daily", "outlet_book", "MM", True, None),
    ("4", "Cooking/Reheating Temperature", "daily", "outlet_book", "CF", True, None),
    ("5", "Cooling of Food", "daily", "outlet_book", "CF", True, None),
    ("6", "Food Display Temperature", "daily", "outlet_book", "AM", True, None),
    ("7", "Thermometer Calibration", "monthly", "outlet_book", "AM", True, None),
    ("12", "Defrosting Record", "daily", "outlet_book", "CF", True, None),
    ("13", "Dishwasher/Glasswasher Temperature", "daily", "outlet_book", "AM", True, None),
    ("17", "Cleaning Schedule", "monthly", "outlet_book", "AM", True, None),
    ("20", "Kitchen Audit Checklist", "monthly", "outlet_book", "MM", True, None),
    ("21", "Food Washing Record", "daily", "outlet_book", "CF", True, None),
    ("24", "Allergen Matrix", "annual", "outlet_book", "CF", True, None),
    ("27", "pH Testing Record", "daily", "outlet_book", "CF", True, "Toro only - ceviche/acidified foods"),
    ("28", "Thermometer Register", "annual", "outlet_book", "AM", True, None),
    ("37", "Non Conformance Record", "as_needed", "outlet_book", "MM", True, None),

    # SCP-Specific Records (Outlet Book)
    ("SCP 40", "Draft Line Cleaning", "monthly", "outlet_book", "AM", True, None),
    ("SCP 47", "Food Sample Log (14 Day)", "daily", "outlet_book", "CF", True, "MK only"),

    # Standard EHC Records (Office Book)
    ("1", "Checklist to Visit Suppliers", "annual", "office_book", "EHC", False, None),
    ("1a", "Approved Supplier List", "annual", "office_book", "CM", False, None),
    ("2", "Food Delivery Record", "daily", "office_book", "CM", True, "May-July audit window"),
    ("8", "Internal Food Safety Audit", "annual", "office_book", "MM", False, "Primary + Pre-inspection with CAs"),
    ("9", "Food Poisoning Allegation", "as_needed", "office_book", "EHC", False, None),
    ("11", "Staff Food Safety Declaration", "annual", "office_book", "EHC", False, None),
    ("14", "Foreign Matter Record", "as_needed", "office_book", "MM", False, None),
    ("15", "Pesticide Usage Record", "as_needed", "office_book", "ENG", False, None),
    ("16", "Pesticide Approved List", "annual", "office_book", "ENG", False, None),
    ("18", "Food Poisoning/Foreign Object Letter", "as_needed", "office_book", "EHC", False, None),
    ("19", "Outdoor Catering Temperature Record", "as_needed", "office_book", "EHC", True, None),
    ("23", "Training Records", "annual", "office_book", "AM", False, "Attendance + discussion sheets"),
    ("25", "Ice Machine Cleaning", "monthly", "office_book", "ENG", False, None),
    ("29", "Internal Swabbing Record", "monthly", "office_book", "MM", False, "Kitchen monthly, Room bi-monthly"),
    ("30", "Guest-Supplied Food Indemnity", "as_needed", "office_book", "EHC", False, None),
    ("30b", "Baby Milk Reheating Indemnity", "as_needed", "office_book", "EHC", False, None),
    ("32", "Maintenance Defect Record", "daily", "office_book", "AM", False, "Print Alice records May-July"),
    ("33", "Pest Sighting Record", "daily", "office_book", "AM", False, "Print Alice records May-July"),
    ("34", "Review Record", "annual", "office_book", "MM", False, "Close out prior year"),
    ("35", "Food Safety Team Record", "annual", "office_book", "MM", False, "Summary + signatures"),
    ("36", "Food Donation Waiver", "as_needed", "office_book", "EHC", False, None),

    # SCP-Specific Records (Office Book)
    ("SCP 38", "Notice Board Documents", "annual", "office_book", "AM", False, None),
    ("SCP 39", "Dish Machine 3rd Party PM", "quarterly", "office_book", "FF", False, None),
    ("SCP 41", "MSDS/SDS Link", "annual", "office_book", "FF", False, None),
    ("SCP 42", "Pest Control License/Contract", "annual", "office_book", "ENG", False, None),
    ("SCP 43", "Pest Control Insurance", "annual", "office_book", "ENG", False, None),
    ("SCP 44", "Pest Control Bait Map", "annual", "office_book", "ENG", False, None),
    ("SCP 45", "Water Testing Records", "quarterly", "office_book", "MM", False, "Q1, Q2, Q3"),
    ("SCP 46", "Microbial Lab Test Results", "quarterly", "office_book", "MM", False, "Q1, Q2, Q3"),
]


# ============================================
# OUTLET-RECORD MAPPINGS
# Which outlets need which outlet-book records
# ============================================
OUTLET_RECORD_MAPPINGS = {
    "3": ["Casual", "Plaza", "Pools", "Toro", "LaHa", "BSAZ", "Gold", "Starbucks", "Dish", "MK", "Pastry", "GM"],
    "4": ["Casual", "Toro", "LaHa", "BSAZ", "Dish", "MK", "Starbucks", "Pastry"],
    "5": ["Casual", "Toro", "LaHa", "BSAZ", "Dish", "MK", "GM", "Pastry"],
    "6": ["Casual", "Dish", "Gold"],
    "7": ["Casual", "Plaza", "Pools", "Toro", "LaHa", "BSAZ", "Gold", "Starbucks", "Dish", "MK", "Pastry", "GM"],
    "12": ["Casual", "MK", "GM", "Pastry", "Dish", "Toro", "LaHa", "BSAZ"],
    "13": ["Casual", "MK", "Palomino", "LaHa", "Toro", "BSAZ", "Plaza", "Pools", "Gold"],  # Dish + Glass combined
    "17": ["MK", "GM", "Pastry", "Palomino", "Casual", "BSAZ", "Toro", "LaHa", "Gold", "Starbucks"],
    "20": ["MK", "GM", "Pastry", "Dish", "Casual", "BSAZ", "Toro", "LaHa"],
    "21": ["GM"],
    "24": ["Casual", "BSAZ", "Toro", "LaHa", "Gold", "Starbucks"],
    "27": ["Toro"],
    "28": ["Casual", "BSAZ", "Toro", "LaHa", "Gold"],
    "37": [],  # All outlets as-needed
    "SCP 40": ["Plaza", "Toro", "Pools"],
    "SCP 47": ["MK"],
}


# ============================================
# POINT-RECORD LINKS
# Maps audit point ref_codes to record numbers
# ============================================
POINT_RECORD_LINKS = {
    "A1": ["1a"],
    "A2": ["1"],
    "B1": ["2"],
    "C1": ["3"],
    "C2": ["3"],
    "C10": ["3"],
    "D1": ["12"],
    "F1": ["4"],
    "G1": ["5"],
    "I1": ["6"],
    "J2": ["28"],
    "J3": ["7"],
    "K1": ["13"],
    "K2": ["13"],
    "K3": ["25"],
    "K4": ["25"],
    "K8": ["SCP 40"],
    "K9": ["SCP 40"],
    "M1": ["17"],
    "M9": ["13"],
    "M10": ["13"],
    "M11": ["17"],
    "M12": ["SCP 41"],
    "N5": ["32"],
    "P1": ["33"],
    "P4": ["SCP 42"],
    "P5": ["SCP 43"],
    "P6": ["SCP 44"],
    "P7": ["16"],
    "P8": ["15"],
    "R1": ["23"],
    "R3": ["23"],
    "S1": ["SCP 45"],
    "T1": ["9", "18"],
    "T2": ["8"],
    "T3": ["SCP 46"],
    "T4": ["29"],
    "T5": ["27"],
    "T6": ["SCP 47"],
    "T7": ["37"],
    "T8": ["37"],
    "U2": ["29"],
    "W1": ["24"],
    "X1": ["21"],
    "X2": ["21"],
    "Z1": ["SCP 38"],
    "Z6": ["34"],
    "Z9": ["35"],
}


# ============================================
# SEEDING FUNCTIONS
# ============================================

def seed_ehc_records(cursor, organization_id: int) -> Dict[str, int]:
    """
    Seed the master record list for an organization.
    Returns mapping of record_number -> record_id.
    """
    record_ids = {}

    for record in RECORDS:
        record_number, name, record_type, location_type, responsibility_code, is_physical_only, notes = record

        cursor.execute("""
            INSERT INTO ehc_record (
                organization_id, record_number, name, record_type,
                location_type, responsibility_code, is_physical_only, notes
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (organization_id, record_number) DO UPDATE SET
                name = EXCLUDED.name,
                record_type = EXCLUDED.record_type,
                updated_at = NOW()
            RETURNING id
        """, (
            organization_id, record_number, name, record_type,
            location_type, responsibility_code, is_physical_only, notes
        ))

        result = cursor.fetchone()
        record_ids[record_number] = result['id']

    logger.info(f"Seeded {len(record_ids)} EHC records for org {organization_id}")
    return record_ids


def seed_outlet_record_mappings(cursor, record_ids: Dict[str, int]) -> int:
    """
    Seed outlet-record mappings.
    Returns count of mappings created.
    """
    count = 0

    for record_number, outlets in OUTLET_RECORD_MAPPINGS.items():
        if record_number not in record_ids:
            continue

        record_id = record_ids[record_number]

        for outlet_name in outlets:
            cursor.execute("""
                INSERT INTO ehc_record_outlet (record_id, outlet_name)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            """, (record_id, outlet_name))
            count += 1

    logger.info(f"Seeded {count} outlet-record mappings")
    return count


def seed_audit_cycle(cursor, organization_id: int, year: int, target_date: date = None) -> int:
    """
    Create a new audit cycle for the given year.
    Returns the cycle_id.
    """
    name = f"EHC {year}"

    cursor.execute("""
        INSERT INTO ehc_audit_cycle (organization_id, name, year, target_date, status)
        VALUES (%s, %s, %s, %s, 'preparing')
        ON CONFLICT (organization_id, year) DO UPDATE SET
            target_date = COALESCE(EXCLUDED.target_date, ehc_audit_cycle.target_date),
            updated_at = NOW()
        RETURNING id
    """, (organization_id, name, year, target_date))

    result = cursor.fetchone()
    cycle_id = result['id']

    logger.info(f"Created/updated audit cycle '{name}' (id={cycle_id})")
    return cycle_id


def seed_sections_and_subsections(cursor, cycle_id: int) -> Dict[str, int]:
    """
    Seed sections and subsections for a cycle.
    Returns mapping of subsection_code -> subsection_id.
    """
    section_ids = {}
    subsection_ids = {}

    # Create sections
    for section in SECTIONS:
        cursor.execute("""
            INSERT INTO ehc_section (audit_cycle_id, ref_number, name, sort_order)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (audit_cycle_id, ref_number) DO UPDATE SET
                name = EXCLUDED.name
            RETURNING id
        """, (cycle_id, section["ref_number"], section["name"], section["sort_order"]))

        result = cursor.fetchone()
        section_ids[section["ref_number"]] = result['id']

    logger.info(f"Seeded {len(section_ids)} sections")

    # Create subsections
    for code, (section_num, name, sort_order) in SUBSECTIONS.items():
        section_id = section_ids[section_num]

        cursor.execute("""
            INSERT INTO ehc_subsection (section_id, ref_code, name, sort_order)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (section_id, ref_code) DO UPDATE SET
                name = EXCLUDED.name
            RETURNING id
        """, (section_id, code, name, sort_order))

        result = cursor.fetchone()
        subsection_ids[code] = result['id']

    logger.info(f"Seeded {len(subsection_ids)} subsections")
    return subsection_ids


def seed_audit_points(cursor, subsection_ids: Dict[str, int]) -> Dict[str, int]:
    """
    Seed all 125 audit points.
    Returns mapping of ref_code -> audit_point_id.
    """
    point_ids = {}

    for ref_code, question_text, nc_level, max_score, responsible_area in AUDIT_POINTS:
        # Extract subsection code (first letter(s) before the number)
        subsection_code = ''.join(c for c in ref_code if c.isalpha())
        subsection_id = subsection_ids.get(subsection_code)

        if not subsection_id:
            logger.warning(f"No subsection found for point {ref_code}")
            continue

        cursor.execute("""
            INSERT INTO ehc_audit_point (
                subsection_id, ref_code, question_text, nc_level,
                max_score, responsible_area, status
            )
            VALUES (%s, %s, %s, %s, %s, %s, 'not_started')
            ON CONFLICT (subsection_id, ref_code) DO UPDATE SET
                question_text = EXCLUDED.question_text,
                nc_level = EXCLUDED.nc_level,
                max_score = EXCLUDED.max_score,
                updated_at = NOW()
            RETURNING id
        """, (
            subsection_id, ref_code, question_text, nc_level,
            max_score, responsible_area
        ))

        result = cursor.fetchone()
        point_ids[ref_code] = result['id']

    logger.info(f"Seeded {len(point_ids)} audit points")
    return point_ids


def seed_point_record_links(cursor, point_ids: Dict[str, int], record_ids: Dict[str, int]) -> int:
    """
    Seed point-record links.
    Returns count of links created.
    """
    count = 0

    for point_code, record_numbers in POINT_RECORD_LINKS.items():
        if point_code not in point_ids:
            continue

        point_id = point_ids[point_code]
        is_primary = True  # First record is primary

        for record_number in record_numbers:
            if record_number not in record_ids:
                continue

            record_id = record_ids[record_number]

            cursor.execute("""
                INSERT INTO ehc_point_record_link (audit_point_id, record_id, is_primary)
                VALUES (%s, %s, %s)
                ON CONFLICT (audit_point_id, record_id) DO NOTHING
            """, (point_id, record_id, is_primary))

            count += 1
            is_primary = False  # Subsequent records are not primary

    logger.info(f"Seeded {count} point-record links")
    return count


def generate_submissions_for_cycle(
    cursor,
    cycle_id: int,
    record_ids: Dict[str, int],
    year: int
) -> int:
    """
    Generate record submissions for a full year based on record types.
    Returns count of submissions created.
    """
    count = 0
    months = ["January", "February", "March", "April", "May", "June",
              "July", "August", "September", "October", "November", "December"]

    for record_number, record_id in record_ids.items():
        # Get record details
        cursor.execute("""
            SELECT record_type, location_type FROM ehc_record WHERE id = %s
        """, (record_id,))
        record = cursor.fetchone()

        if not record:
            continue

        record_type = record['record_type']
        location_type = record['location_type']

        # Get outlets for this record (if outlet_book)
        outlets = [None]  # Default for office_book
        if location_type == 'outlet_book':
            cursor.execute("""
                SELECT outlet_name FROM ehc_record_outlet WHERE record_id = %s
            """, (record_id,))
            outlet_rows = cursor.fetchall()
            if outlet_rows:
                outlets = [row['outlet_name'] for row in outlet_rows]

        # Generate submissions based on record_type
        for outlet_name in outlets:
            if record_type == 'daily':
                # Monthly rollup for daily records
                for i, month in enumerate(months):
                    period_label = f"{month} {year}"
                    period_start = date(year, i + 1, 1)
                    if i == 11:
                        period_end = date(year, 12, 31)
                    else:
                        period_end = date(year, i + 2, 1)

                    count += _create_submission(
                        cursor, cycle_id, record_id, outlet_name,
                        period_label, period_start, period_end
                    )

            elif record_type == 'monthly':
                for i, month in enumerate(months):
                    period_label = f"{month} {year}"
                    period_start = date(year, i + 1, 1)
                    if i == 11:
                        period_end = date(year, 12, 31)
                    else:
                        period_end = date(year, i + 2, 1)

                    count += _create_submission(
                        cursor, cycle_id, record_id, outlet_name,
                        period_label, period_start, period_end
                    )

            elif record_type == 'quarterly':
                quarters = [
                    ("Q1", date(year, 1, 1), date(year, 3, 31)),
                    ("Q2", date(year, 4, 1), date(year, 6, 30)),
                    ("Q3", date(year, 7, 1), date(year, 9, 30)),
                    ("Q4", date(year, 10, 1), date(year, 12, 31)),
                ]
                for label, start, end in quarters:
                    count += _create_submission(
                        cursor, cycle_id, record_id, outlet_name,
                        f"{label} {year}", start, end
                    )

            elif record_type in ('annual', 'one_time'):
                count += _create_submission(
                    cursor, cycle_id, record_id, outlet_name,
                    f"Annual {year}", date(year, 1, 1), date(year, 12, 31)
                )

            elif record_type == 'as_needed':
                count += _create_submission(
                    cursor, cycle_id, record_id, outlet_name,
                    "As Needed", None, None
                )

            elif record_type == 'bi_monthly':
                # Every other month
                bi_months = [(1, "Jan-Feb"), (3, "Mar-Apr"), (5, "May-Jun"),
                             (7, "Jul-Aug"), (9, "Sep-Oct"), (11, "Nov-Dec")]
                for month_num, label in bi_months:
                    period_start = date(year, month_num, 1)
                    period_end = date(year, month_num + 1, 28)  # Approximate
                    count += _create_submission(
                        cursor, cycle_id, record_id, outlet_name,
                        f"{label} {year}", period_start, period_end
                    )

    logger.info(f"Generated {count} submissions for cycle year {year}")
    return count


def _create_submission(
    cursor,
    cycle_id: int,
    record_id: int,
    outlet_name: Optional[str],
    period_label: str,
    period_start: Optional[date],
    period_end: Optional[date]
) -> int:
    """Helper to create a single submission. Returns 1 if created, 0 if exists."""
    try:
        cursor.execute("""
            INSERT INTO ehc_record_submission (
                audit_cycle_id, record_id, outlet_name,
                period_label, period_start, period_end, status
            )
            VALUES (%s, %s, %s, %s, %s, %s, 'pending')
            ON CONFLICT DO NOTHING
        """, (cycle_id, record_id, outlet_name, period_label, period_start, period_end))
        return 1
    except Exception as e:
        logger.warning(f"Failed to create submission: {e}")
        return 0


def seed_full_ehc_cycle(
    conn,
    organization_id: int,
    year: int,
    target_date: date = None
) -> Dict:
    """
    Complete seeding for a new EHC audit cycle.

    1. Seeds master records (if not exist)
    2. Seeds outlet-record mappings
    3. Creates audit cycle
    4. Seeds sections/subsections
    5. Seeds audit points
    6. Seeds point-record links
    7. Generates submissions

    Returns summary of what was created.
    """
    cursor = conn.cursor()

    # Step 1: Seed records
    record_ids = seed_ehc_records(cursor, organization_id)

    # Step 2: Seed outlet mappings
    outlet_mapping_count = seed_outlet_record_mappings(cursor, record_ids)

    # Step 3: Create cycle
    cycle_id = seed_audit_cycle(cursor, organization_id, year, target_date)

    # Step 4: Seed sections and subsections
    subsection_ids = seed_sections_and_subsections(cursor, cycle_id)

    # Step 5: Seed audit points
    point_ids = seed_audit_points(cursor, subsection_ids)

    # Step 6: Seed point-record links
    link_count = seed_point_record_links(cursor, point_ids, record_ids)

    # Step 7: Generate submissions
    submission_count = generate_submissions_for_cycle(cursor, cycle_id, record_ids, year)

    conn.commit()

    summary = {
        "cycle_id": cycle_id,
        "year": year,
        "records": len(record_ids),
        "outlet_mappings": outlet_mapping_count,
        "sections": len(SECTIONS),
        "subsections": len(subsection_ids),
        "audit_points": len(point_ids),
        "point_record_links": link_count,
        "submissions": submission_count,
    }

    logger.info(f"EHC cycle seeding complete: {summary}")
    return summary
