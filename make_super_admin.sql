-- Make mike.myers@fairmont.com a super admin
-- Run this on the dev database

UPDATE users
SET is_super_admin = 1
WHERE email = 'mike.myers@fairmont.com'
RETURNING id, email, username, is_super_admin;

-- Verify the update
SELECT id, email, username, role, is_super_admin
FROM users
WHERE email = 'mike.myers@fairmont.com';
