#!/bin/bash
# Make a user a super admin on the remote database
# Usage: ./make_super_admin_remote.sh <email> <environment>
# Example: ./make_super_admin_remote.sh mike.myers@fairmont.com dev

EMAIL=$1
ENV=${2:-dev}

if [ -z "$EMAIL" ]; then
    echo "Usage: ./make_super_admin_remote.sh <email> [dev|prod]"
    exit 1
fi

if [ "$ENV" = "dev" ]; then
    SERVICE_NAME="food-cost-tracker-dev"
elif [ "$ENV" = "prod" ]; then
    SERVICE_NAME="food-cost-tracker"
else
    echo "Environment must be 'dev' or 'prod'"
    exit 1
fi

echo "Making $EMAIL a super admin on $ENV environment..."

# Use Render CLI to execute the Python script
render exec -s "$SERVICE_NAME" -- python -c "
import os
import psycopg2
from urllib.parse import urlparse

# Parse DATABASE_URL
db_url = os.environ['DATABASE_URL']
result = urlparse(db_url)
username = result.username
password = result.password
database = result.path[1:]
hostname = result.hostname
port = result.port

# Connect to database
conn = psycopg2.connect(
    database=database,
    user=username,
    password=password,
    host=hostname,
    port=port
)
cursor = conn.cursor()

# Update user
cursor.execute('''
    UPDATE users
    SET is_super_admin = 1
    WHERE email = %s
    RETURNING id, email, username
''', ('$EMAIL',))

user = cursor.fetchone()
if user:
    conn.commit()
    print(f'✅ Successfully made $EMAIL a super admin!')
    print(f'   User ID: {user[0]}')
    print(f'   Username: {user[2]}')
else:
    print(f'❌ User not found: $EMAIL')

conn.close()
"

echo "Done!"
