#!/bin/bash
# Quick script to run API tests against your dev environment
# Usage: ./run_api_tests.sh YOUR_JWT_TOKEN

if [ -z "$1" ]; then
    echo "❌ Error: Missing JWT token"
    echo ""
    echo "Usage: ./run_api_tests.sh YOUR_JWT_TOKEN"
    echo ""
    echo "How to get your JWT token:"
    echo "  1. Visit https://food-cost-tracker-dev.onrender.com"
    echo "  2. Log in with your account"
    echo "  3. Open Browser DevTools → Network tab"
    echo "  4. Look at any API request"
    echo "  5. Copy the Authorization header (the part after 'Bearer ')"
    echo ""
    echo "Example:"
    echo "  ./run_api_tests.sh eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    exit 1
fi

TOKEN="$1"
DEV_URL="https://food-cost-tracker-dev.onrender.com"

echo "🧪 Running API tests against dev environment..."
echo "📍 API URL: $DEV_URL"
echo "🔑 Token: ${TOKEN:0:20}..."
echo ""

python test_api_endpoints.py "$DEV_URL" "$TOKEN"
