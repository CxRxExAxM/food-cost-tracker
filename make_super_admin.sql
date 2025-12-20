-- Script to make mike.myers@fairmont.com a super admin
-- Run this against your PostgreSQL database

-- Update the user to be a super admin
UPDATE users
SET is_super_admin = true
WHERE email = 'mike.myers@fairmont.com';

-- Verify the change
SELECT
    id,
    email,
    full_name,
    role,
    is_super_admin,
    organization_id
FROM users
WHERE email = 'mike.myers@fairmont.com';
