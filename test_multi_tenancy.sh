#!/bin/bash

# Multi-Tenancy Testing Script
# Tests organization isolation and data security
# Prerequisites: API server running at http://127.0.0.1:8000

BASE_URL="http://127.0.0.1:8000"
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test results tracking
TESTS_PASSED=0
TESTS_FAILED=0

# Helper function to print colored output
print_test() {
    echo -e "${YELLOW}TEST:${NC} $1"
}

print_pass() {
    echo -e "${GREEN}✓ PASS:${NC} $1"
    ((TESTS_PASSED++))
}

print_fail() {
    echo -e "${RED}✗ FAIL:${NC} $1"
    ((TESTS_FAILED++))
}

print_info() {
    echo -e "${YELLOW}INFO:${NC} $1"
}

echo "========================================="
echo "Multi-Tenancy Testing Suite"
echo "========================================="
echo ""

# Check if server is running
print_info "Checking if API server is running..."
if ! curl -s "${BASE_URL}/docs" > /dev/null 2>&1; then
    print_fail "API server is not running at ${BASE_URL}"
    echo "Please start the server with: venv/bin/uvicorn api.app.main:app --port 8000 --host 127.0.0.1 --reload"
    exit 1
fi
print_pass "API server is running"
echo ""

# Step 1: Check setup status
print_test "Step 1: Checking setup status"
SETUP_STATUS=$(curl -s "${BASE_URL}/auth/setup-status")
echo "Setup status: ${SETUP_STATUS}"
echo ""

# Step 2: Get or create Organization A admin
print_test "Step 2: Setting up Organization A admin"
ORG_A_TOKEN=$(curl -s -X POST "${BASE_URL}/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin-org-a@test.com",
    "password": "testpass123"
  }' 2>/dev/null | jq -r '.access_token // empty')

if [ -z "$ORG_A_TOKEN" ]; then
    print_info "Org A admin doesn't exist, attempting to create..."
    ORG_A_TOKEN=$(curl -s -X POST "${BASE_URL}/auth/setup" \
      -H "Content-Type: application/json" \
      -d '{
        "email": "admin-org-a@test.com",
        "username": "admin_org_a",
        "password": "testpass123",
        "full_name": "Org A Admin"
      }' 2>/dev/null | jq -r '.access_token // empty')

    if [ -z "$ORG_A_TOKEN" ]; then
        print_fail "Could not create or login as Org A admin"
        print_info "Setup might already be complete. Try logging in with existing credentials."
        exit 1
    fi
    print_pass "Created Organization A admin"
else
    print_pass "Logged in as existing Organization A admin"
fi
echo ""

# Get Org A info
print_test "Step 3: Getting Organization A details"
ORG_A_INFO=$(curl -s -X GET "${BASE_URL}/auth/me" \
  -H "Authorization: Bearer ${ORG_A_TOKEN}")
ORG_A_ID=$(echo $ORG_A_INFO | jq -r '.organization_id')
ORG_A_EMAIL=$(echo $ORG_A_INFO | jq -r '.email')
echo "Organization A ID: ${ORG_A_ID}"
echo "Organization A Email: ${ORG_A_EMAIL}"
echo ""

# Step 4: Create Organization B (check if exists first)
print_test "Step 4: Setting up Organization B"

# Check if Org B already exists
ORG_B_EXISTS=$(sqlite3 db/food_cost_tracker.db "SELECT COUNT(*) FROM organizations WHERE id = 2;" 2>/dev/null || echo "0")

if [ "$ORG_B_EXISTS" == "0" ]; then
    print_info "Creating Organization B in database..."
    sqlite3 db/food_cost_tracker.db <<EOF 2>/dev/null
INSERT INTO organizations (id, name, slug, subscription_tier, subscription_status, max_recipes, max_distributors, max_ai_parses_per_month, ai_parses_used_this_month)
VALUES (2, 'Organization B', 'org-b', 'free', 'active', 5, 1, 10, 0);
EOF
    print_pass "Created Organization B"
else
    print_info "Organization B already exists"
fi

# Check if Org B admin exists
ORG_B_USER_EXISTS=$(sqlite3 db/food_cost_tracker.db "SELECT COUNT(*) FROM users WHERE email = 'admin-org-b@test.com';" 2>/dev/null || echo "0")

if [ "$ORG_B_USER_EXISTS" == "0" ]; then
    print_info "Creating admin user for Organization B..."
    # Get password hash from existing user
    HASH=$(sqlite3 db/food_cost_tracker.db "SELECT hashed_password FROM users LIMIT 1;" 2>/dev/null)
    sqlite3 db/food_cost_tracker.db <<EOF 2>/dev/null
INSERT INTO users (organization_id, email, username, hashed_password, full_name, role, is_active)
VALUES (2, 'admin-org-b@test.com', 'admin_org_b', '${HASH}', 'Org B Admin', 'admin', 1);
EOF
    print_pass "Created admin user for Organization B"
else
    print_info "Organization B admin already exists"
fi
echo ""

# Login as Org B admin
print_test "Step 5: Logging in as Organization B admin"
ORG_B_TOKEN=$(curl -s -X POST "${BASE_URL}/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin-org-b@test.com",
    "password": "testpass123"
  }' 2>/dev/null | jq -r '.access_token // empty')

if [ -z "$ORG_B_TOKEN" ]; then
    print_fail "Failed to login as Organization B admin"
    exit 1
fi
print_pass "Logged in as Organization B admin"

ORG_B_INFO=$(curl -s -X GET "${BASE_URL}/auth/me" \
  -H "Authorization: Bearer ${ORG_B_TOKEN}")
ORG_B_ID=$(echo $ORG_B_INFO | jq -r '.organization_id')
ORG_B_EMAIL=$(echo $ORG_B_INFO | jq -r '.email')
echo "Organization B ID: ${ORG_B_ID}"
echo "Organization B Email: ${ORG_B_EMAIL}"
echo ""

# Verify organizations are different
print_test "Step 6: Verifying organizations are separate"
if [ "$ORG_A_ID" == "$ORG_B_ID" ]; then
    print_fail "Organization IDs are the same! Multi-tenancy not working."
    exit 1
fi
if [ "$ORG_A_ID" == "null" ] || [ "$ORG_B_ID" == "null" ]; then
    print_fail "Organization IDs are null! Check JWT tokens."
    exit 1
fi
print_pass "Organizations have different IDs: Org A=${ORG_A_ID}, Org B=${ORG_B_ID}"
echo ""

# Step 7: Create test recipe for Org A
print_test "Step 7: Creating test recipe for Organization A"
ORG_A_RECIPE=$(curl -s -X POST "${BASE_URL}/recipes" \
  -H "Authorization: Bearer ${ORG_A_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Org A Secret Recipe",
    "description": "This should only be visible to Org A",
    "category": "Entrees",
    "category_path": "Entrees",
    "yield_amount": 4,
    "prep_time_minutes": 30,
    "cook_time_minutes": 45,
    "method": [],
    "ingredients": []
  }' 2>/dev/null)
ORG_A_RECIPE_ID=$(echo $ORG_A_RECIPE | jq -r '.id // empty')

if [ -z "$ORG_A_RECIPE_ID" ] || [ "$ORG_A_RECIPE_ID" == "null" ]; then
    print_fail "Failed to create recipe for Org A"
    echo "Response: ${ORG_A_RECIPE}"
else
    print_pass "Created recipe for Org A (ID: ${ORG_A_RECIPE_ID})"
fi
echo ""

# Step 8: Create test recipe for Org B
print_test "Step 8: Creating test recipe for Organization B"
ORG_B_RECIPE=$(curl -s -X POST "${BASE_URL}/recipes" \
  -H "Authorization: Bearer ${ORG_B_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Org B Proprietary Recipe",
    "description": "This should only be visible to Org B",
    "category": "Desserts",
    "category_path": "Desserts",
    "yield_amount": 8,
    "prep_time_minutes": 20,
    "cook_time_minutes": 60,
    "method": [],
    "ingredients": []
  }' 2>/dev/null)
ORG_B_RECIPE_ID=$(echo $ORG_B_RECIPE | jq -r '.id // empty')

if [ -z "$ORG_B_RECIPE_ID" ] || [ "$ORG_B_RECIPE_ID" == "null" ]; then
    print_fail "Failed to create recipe for Org B"
    echo "Response: ${ORG_B_RECIPE}"
else
    print_pass "Created recipe for Org B (ID: ${ORG_B_RECIPE_ID})"
fi
echo ""

# Step 9: Test data isolation - Org A should NOT see Org B's data
print_test "Step 9: Testing data isolation - Org A listing recipes"
ORG_A_RECIPES=$(curl -s -X GET "${BASE_URL}/recipes" \
  -H "Authorization: Bearer ${ORG_A_TOKEN}")
ORG_A_RECIPE_COUNT=$(echo $ORG_A_RECIPES | jq 'length')
echo "Org A sees ${ORG_A_RECIPE_COUNT} recipes"
echo "Org A recipes: $(echo $ORG_A_RECIPES | jq -c '[.[].name]')"

# Check if Org B's recipe appears in Org A's list
if echo $ORG_A_RECIPES | jq -e '.[] | select(.name == "Org B Proprietary Recipe")' > /dev/null 2>&1; then
    print_fail "DATA LEAK! Org A can see Org B's recipe"
else
    print_pass "Data isolation verified: Org A cannot see Org B's recipe"
fi
echo ""

# Step 10: Test data isolation - Org B should NOT see Org A's data
print_test "Step 10: Testing data isolation - Org B listing recipes"
ORG_B_RECIPES=$(curl -s -X GET "${BASE_URL}/recipes" \
  -H "Authorization: Bearer ${ORG_B_TOKEN}")
ORG_B_RECIPE_COUNT=$(echo $ORG_B_RECIPES | jq 'length')
echo "Org B sees ${ORG_B_RECIPE_COUNT} recipes"
echo "Org B recipes: $(echo $ORG_B_RECIPES | jq -c '[.[].name]')"

# Check if Org A's recipe appears in Org B's list
if echo $ORG_B_RECIPES | jq -e '.[] | select(.name == "Org A Secret Recipe")' > /dev/null 2>&1; then
    print_fail "DATA LEAK! Org B can see Org A's recipe"
else
    print_pass "Data isolation verified: Org B cannot see Org A's recipe"
fi
echo ""

# Step 11: Test direct access prevention - Org A trying to access Org B's recipe by ID
if [ -n "$ORG_B_RECIPE_ID" ] && [ "$ORG_B_RECIPE_ID" != "null" ]; then
    print_test "Step 11: Org A attempting to access Org B's recipe directly by ID"
    UNAUTHORIZED_ACCESS=$(curl -s -w "%{http_code}" -o /tmp/multi_tenancy_test_response.txt \
      -X GET "${BASE_URL}/recipes/${ORG_B_RECIPE_ID}" \
      -H "Authorization: Bearer ${ORG_A_TOKEN}")

    if [ "$UNAUTHORIZED_ACCESS" == "404" ]; then
        print_pass "Access denied: Org A cannot access Org B's recipe by ID (404)"
    elif [ "$UNAUTHORIZED_ACCESS" == "403" ]; then
        print_pass "Access denied: Org A cannot access Org B's recipe by ID (403)"
    else
        print_fail "SECURITY ISSUE! Org A accessed Org B's recipe (HTTP ${UNAUTHORIZED_ACCESS})"
        echo "Response: $(cat /tmp/multi_tenancy_test_response.txt)"
    fi
    echo ""
fi

# Step 12: Test common products isolation
print_test "Step 12: Testing common products isolation"

# Create common product for Org A
ORG_A_PRODUCT=$(curl -s -X POST "${BASE_URL}/common-products" \
  -H "Authorization: Bearer ${ORG_A_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "common_name": "Org A Chicken Breast",
    "category": "Proteins",
    "subcategory": "Poultry"
  }' 2>/dev/null)
ORG_A_PRODUCT_ID=$(echo $ORG_A_PRODUCT | jq -r '.id // empty')

# Create common product for Org B (same name, different org)
ORG_B_PRODUCT=$(curl -s -X POST "${BASE_URL}/common-products" \
  -H "Authorization: Bearer ${ORG_B_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "common_name": "Org B Chicken Breast",
    "category": "Proteins",
    "subcategory": "Poultry"
  }' 2>/dev/null)
ORG_B_PRODUCT_ID=$(echo $ORG_B_PRODUCT | jq -r '.id // empty')

if [ -n "$ORG_A_PRODUCT_ID" ] && [ "$ORG_A_PRODUCT_ID" != "null" ] && [ -n "$ORG_B_PRODUCT_ID" ] && [ "$ORG_B_PRODUCT_ID" != "null" ]; then
    print_pass "Both organizations can create products with unique names"

    # Check isolation
    ORG_A_PRODUCTS=$(curl -s -X GET "${BASE_URL}/common-products" \
      -H "Authorization: Bearer ${ORG_A_TOKEN}")

    if echo $ORG_A_PRODUCTS | jq -e '.[] | select(.common_name == "Org B Chicken Breast")' > /dev/null 2>&1; then
        print_fail "DATA LEAK! Org A can see Org B's common product"
    else
        print_pass "Common products properly isolated between organizations"
    fi
else
    print_fail "Failed to create common products for testing"
    echo "Org A Product: ${ORG_A_PRODUCT}"
    echo "Org B Product: ${ORG_B_PRODUCT}"
fi
echo ""

# Summary
echo ""
echo "========================================="
echo "Test Summary"
echo "========================================="
echo -e "${GREEN}Tests Passed: ${TESTS_PASSED}${NC}"
echo -e "${RED}Tests Failed: ${TESTS_FAILED}${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All multi-tenancy tests passed!${NC}"
    echo ""
    echo "Multi-tenancy is working correctly:"
    echo "  - Organizations have separate data"
    echo "  - Cross-organization access is blocked"
    echo "  - JWT tokens correctly enforce isolation"
    exit 0
else
    echo -e "${RED}✗ Some tests failed. Multi-tenancy may have security issues.${NC}"
    exit 1
fi
