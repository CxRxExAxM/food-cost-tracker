#!/bin/bash
# Quick test to verify outlet_id shows in API responses
# Usage: ./quick_test.sh YOUR_JWT_TOKEN

if [ -z "$1" ]; then
    echo "Usage: ./quick_test.sh YOUR_JWT_TOKEN"
    exit 1
fi

TOKEN="$1"
API_URL="https://food-cost-tracker-dev.onrender.com"

echo "🧪 Testing outlet_id in API responses..."
echo ""

echo "1️⃣  Testing GET /outlets"
curl -s -H "Authorization: Bearer $TOKEN" \
  "$API_URL/outlets" | python3 -m json.tool
echo ""

echo "2️⃣  Testing GET /products (first 2)"
curl -s -H "Authorization: Bearer $TOKEN" \
  "$API_URL/products?limit=2" | python3 -m json.tool | grep -A5 '"name"'
echo ""

echo "3️⃣  Testing GET /recipes"
curl -s -H "Authorization: Bearer $TOKEN" \
  "$API_URL/recipes?limit=2" | python3 -m json.tool | grep -A3 '"name"'
echo ""

echo "✅ Check if outlet_id appears in the responses above!"
