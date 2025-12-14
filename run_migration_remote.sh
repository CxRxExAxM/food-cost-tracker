#!/bin/bash
# Run migration on remote Render database from local machine
# Usage:
#   1. Get DATABASE_URL from Render dashboard (Database -> Connect -> External Connection)
#   2. export DATABASE_URL="postgres://user:pass@host/dbname"
#   3. ./run_migration_remote.sh

if [ -z "$DATABASE_URL" ]; then
    echo "❌ Error: DATABASE_URL environment variable not set"
    echo ""
    echo "Please set it first:"
    echo "  export DATABASE_URL=\"postgres://user:pass@host/dbname\""
    echo ""
    echo "Get it from: Render Dashboard -> Your Database -> Connect -> External Connection"
    exit 1
fi

echo "Running migration on remote database..."
echo ""

python3 run_migration.py

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Migration completed! You can now test multi-outlet uploads."
else
    echo ""
    echo "❌ Migration failed. Check the error above."
    exit 1
fi
