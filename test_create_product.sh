#!/bin/bash
# Test creating a product to see the full error response

if [ -z "$1" ]; then
    echo "Usage: ./test_create_product.sh YOUR_JWT_TOKEN"
    exit 1
fi

TOKEN="$1"
API_URL="https://food-cost-tracker-dev.onrender.com"

echo "🧪 Testing POST /products with detailed error output..."
echo ""

curl -v -X POST "$API_URL/products" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Debug Test Product",
    "brand": "Test Brand",
    "pack": 12,
    "size": 16.0,
    "outlet_id": 2
  }' 2>&1 | tail -50

echo ""
echo "Check the response above for error details"
