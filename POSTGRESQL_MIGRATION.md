# PostgreSQL Migration & Troubleshooting Guide

**Last Updated:** 2025-12-10
**Status:** In Progress - Login authentication debugging in dev environment

## Overview

This document tracks the migration from SQLite-only to dual PostgreSQL/SQLite support, the RestauranTek rebrand, and current troubleshooting efforts for the dev environment.

---

## What We Accomplished Today

### 1. RestauranTek Rebrand ✅
- Changed all branding from "Food Cost Tracker" to "RestauranTek"
- Updated navigation to use logo + horizontal menu
- Created modern Navigation component with responsive design
- Applied to all pages: Home, Products, Recipes, Users, Admin, Login

**Key Files Modified:**
- `frontend/src/components/Navigation.jsx` - New navigation component
- `frontend/src/components/Navigation.css` - Navigation styling
- All page components - Added Navigation import and usage
- `frontend/src/pages/Login.jsx` - Updated branding

### 2. PostgreSQL Compatibility Layer ✅
Built a complete abstraction layer to support both SQLite and PostgreSQL transparently.

**Key Changes:**

#### Database Detection (`api/app/database.py`)
```python
# Automatically detect database type from environment
DATABASE_URL = os.getenv("DATABASE_URL")
USE_POSTGRES = DATABASE_URL and DATABASE_URL.startswith("postgresql")

if USE_POSTGRES:
    import psycopg2
    from psycopg2.extras import RealDictCursor
else:
    # SQLite setup
    DB_PATH = Path(os.getenv("DATABASE_PATH", str(_default_db_path)))
```

#### UniversalRow Wrapper Class
Created to support both integer indexing `row[0]` and dict-style `row['column']` access:

```python
class UniversalRow:
    """Row object that supports both tuple-style [0] and dict-style ['col'] access."""

    def __init__(self, data, use_postgres):
        if use_postgres:
            # RealDictCursor returns dict-like RealDictRow
            self._dict = dict(data)
            self._list = list(self._dict.values())
        else:
            # sqlite3.Row already supports both access methods
            self._original = data
            self._dict = dict(data)

    def __getitem__(self, key):
        if isinstance(key, int):
            # Integer indexing [0], [1], etc
            return self._list[key] if self._list else self._original[key]
        else:
            # String indexing ['column_name']
            return self._dict[key]
```

**Why This Was Needed:**
- SQLite's `Row` objects support both `row[0]` and `row['column']`
- PostgreSQL's `RealDictRow` only supports `row['column']`
- Existing code uses `cursor.fetchone()[0]` throughout
- Wrapper allows code to work with both databases

#### DatabaseCursorWrapper Class
Handles SQL dialect differences:

```python
class DatabaseCursorWrapper:
    """Wrapper for database cursors that converts SQLite ? placeholders to PostgreSQL %s."""

    def execute(self, query, params=None):
        if self.use_postgres:
            if params:
                # Convert SQLite ? placeholders to PostgreSQL %s
                query = query.replace('?', '%s')

            # For INSERT statements, add RETURNING id to support lastrowid
            if query.strip().upper().startswith('INSERT'):
                if 'RETURNING' not in query.upper():
                    query = query.rstrip(';') + ' RETURNING id'

        result = self.cursor.execute(query, params)

        # Store the returned id for lastrowid property
        if self.use_postgres and query.strip().upper().startswith('INSERT'):
            returned_row = self.cursor.fetchone()
            if returned_row:
                self._last_insert_id = returned_row.get('id') or returned_row[0]

        return result

    def fetchone(self):
        result = self.cursor.fetchone()
        return UniversalRow(result, self.use_postgres) if result else None
```

**What It Does:**
1. Converts `?` placeholders to `%s` for PostgreSQL
2. Adds `RETURNING id` to INSERT statements (PostgreSQL doesn't have `lastrowid`)
3. Wraps all fetch results in `UniversalRow` for consistent access
4. Transparently handles both databases

#### Helper Functions Updated
```python
def dict_from_row(row):
    """Convert database row to dictionary - works with both PostgreSQL and SQLite."""
    if row is None:
        return None
    # Handle UniversalRow (our wrapper)
    if isinstance(row, UniversalRow):
        return row._dict
    # Both psycopg2 RealDictCursor and sqlite3.Row can be converted with dict()
    return dict(row)

def dicts_from_rows(rows):
    """Convert list of database rows to list of dictionaries."""
    return [row._dict if isinstance(row, UniversalRow) else dict(row) for row in rows]
```

### 3. Alembic Migration Fixes ✅

**Problem:** Migration used SQLite-specific syntax (`batch_alter_table`)

**Fix:** Updated to use standard Alembic operations with try/except for compatibility

**File:** `alembic/versions/cc2c3eef7f15_add_max_users_to_organizations.py`

```python
def upgrade() -> None:
    """Upgrade schema - PostgreSQL and SQLite compatible."""
    # Add max_users column
    op.add_column('organizations', sa.Column('max_users', sa.Integer(), server_default='2', nullable=True))

    # Drop and recreate check constraint for subscription_tier
    try:
        op.drop_constraint('check_subscription_tier', 'organizations', type_='check')
    except Exception:
        pass  # SQLite doesn't have named constraints, ignore

    op.create_check_constraint(
        'check_subscription_tier',
        'organizations',
        "subscription_tier IN ('free', 'basic', 'pro', 'enterprise')"
    )
```

### 4. Alembic Environment Configuration ✅

**Problem:** Alembic couldn't find database path on Render

**Fix:** Added support for both `DATABASE_URL` and `DATABASE_PATH`

**File:** `alembic/env.py`

```python
# Support both DATABASE_URL (PostgreSQL) and DATABASE_PATH (SQLite on Render)
database_url = os.getenv('DATABASE_URL')
database_path = os.getenv('DATABASE_PATH')

if database_url:
    config.set_main_option('sqlalchemy.url', database_url)
elif database_path:
    # Convert DATABASE_PATH to SQLite URL format
    config.set_main_option('sqlalchemy.url', f'sqlite:///{database_path}')
else:
    # Fallback to local db folder for development
    default_db = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'food_cost_tracker.db')
    config.set_main_option('sqlalchemy.url', f'sqlite:///{default_db}')
```

### 5. Setup Endpoint - Organization Creation ✅

**Problem:** Users table requires `organization_id` (NOT NULL), but setup endpoint didn't create organization

**Fix:** Setup endpoint now creates a default organization first

**File:** `api/app/routers/auth.py`

```python
@router.post("/setup", response_model=Token)
def initial_setup(user: UserCreate):
    with get_db() as conn:
        cursor = conn.cursor()

        # Check if any users exist
        cursor.execute("SELECT COUNT(*) as count FROM users")
        count = cursor.fetchone()[0]

        if count > 0:
            raise HTTPException(status_code=400, detail="Setup already completed")

        # Check if default organization already exists, create if not
        cursor.execute("SELECT id FROM organizations WHERE slug = ?", ("default",))
        org_row = cursor.fetchone()

        if org_row:
            organization_id = org_row[0]
        else:
            # Create default organization
            cursor.execute("""
                INSERT INTO organizations (name, slug, subscription_tier, subscription_status)
                VALUES (?, ?, 'free', 'active')
            """, ("Default Organization", "default"))
            organization_id = cursor.lastrowid

        # Create admin user with organization_id
        hashed_password = get_password_hash(user.password)
        cursor.execute("""
            INSERT INTO users (organization_id, email, username, hashed_password, full_name, role)
            VALUES (?, ?, ?, ?, ?, 'admin')
        """, (organization_id, user.email, user.username, hashed_password, user.full_name))

        user_id = cursor.lastrowid
        conn.commit()

        # Generate token with organization_id
        access_token = create_access_token(
            data={
                "sub": str(user_id),
                "organization_id": organization_id,
                "email": user.email,
                "role": "admin"
            },
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )

        return {"access_token": access_token, "token_type": "bearer"}
```

### 6. Render Environment Configuration ✅

**Removed:** `DATABASE_PATH` from dev environment (was conflicting with PostgreSQL)

**Kept:** `DATABASE_URL` pointing to PostgreSQL database

---

## Current Status: 401 Unauthorized on /auth/me

### Symptoms
1. ✅ Login endpoint succeeds (POST /auth/login returns JWT token)
2. ✅ Token is saved to localStorage
3. ❌ `/auth/me` endpoint returns 401 Unauthorized
4. ❌ User cannot navigate past login page (redirected back)
5. ❌ No Python errors in Render logs (fails silently)

### Browser Console Error
```
[AuthContext] Login failed: AxiosError
message: "Request failed with status code 401"
code: "ERR_BAD_REQUEST"
```

### What We Know
- `/auth/setup-status` works correctly (returns 200)
- Login creates JWT token successfully
- Token is stored in localStorage
- But when frontend calls `/auth/me` with the token, it gets 401
- The request to `/auth/me` is never made visible in Network tab

### Debugging Added

#### Frontend Logging (`frontend/src/context/AuthContext.jsx`)
```javascript
const login = async (email, password) => {
  try {
    console.log('[AuthContext] Starting login...');
    const response = await axios.post(`${API_URL}/auth/login`, { email, password });

    console.log('[AuthContext] Login response:', response.data);
    const { access_token } = response.data;

    if (!access_token) {
      throw new Error('No access token received from server');
    }

    localStorage.setItem('token', access_token);
    console.log('[AuthContext] Token saved, fetching user info...');

    const userResponse = await axios.get(`${API_URL}/auth/me`, {
      headers: { Authorization: `Bearer ${access_token}` }
    });

    console.log('[AuthContext] User info received:', userResponse.data);
    setUser(userResponse.data);
    setSetupRequired(false);
    return userResponse.data;
  } catch (error) {
    console.error('[AuthContext] Login failed:', error);
    throw error;
  }
};
```

#### Backend Logging (`api/app/auth.py`)

**decode_token() function:**
```python
def decode_token(token: str) -> Optional[TokenData]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print(f"[decode_token] Payload: {payload}")
        user_id_str = payload.get("sub")
        organization_id: int = payload.get("organization_id")
        email: str = payload.get("email")
        role: str = payload.get("role")
        if user_id_str is None:
            print("[decode_token] No 'sub' in payload")
            return None
        user_id = int(user_id_str)
        token_data = TokenData(user_id=user_id, organization_id=organization_id, email=email, role=role)
        print(f"[decode_token] Success: {token_data}")
        return token_data
    except (JWTError, ValueError) as e:
        print(f"[decode_token] Failed: {type(e).__name__}: {str(e)}")
        return None
```

**get_user_by_id() function:**
```python
def get_user_by_id(user_id: int):
    print(f"[get_user_by_id] Looking up user_id: {user_id}")
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        print(f"[get_user_by_id] Row type: {type(row)}, Row: {row}")
        result = dict_from_row(row)
        print(f"[get_user_by_id] Result type: {type(result)}, Result: {result}")
        return result
```

**get_current_user() dependency:**
```python
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        print(f"[get_current_user] Validating token: {token[:20]}...")

        token_data = decode_token(token)
        print(f"[get_current_user] Token decoded: {token_data}")

        if token_data is None:
            print("[get_current_user] Token decode failed")
            raise credentials_exception

        print(f"[get_current_user] Looking up user_id: {token_data.user_id}")
        user = get_user_by_id(token_data.user_id)
        print(f"[get_current_user] User found: {user is not None}")

        if user is None:
            print("[get_current_user] User not found in database")
            raise credentials_exception

        if not user["is_active"]:
            print("[get_current_user] User is inactive")
            raise HTTPException(status_code=403, detail="User account is disabled")

        print(f"[get_current_user] Success - returning user {user.get('id')}")
        return user
    except HTTPException:
        raise
    except Exception as e:
        print(f"[get_current_user] Unexpected error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise credentials_exception
```

### Next Steps for Tomorrow

1. **Check Render Logs** - After login attempt, check logs for the detailed debug output:
   - Look for `[get_current_user]` messages
   - Look for `[decode_token]` messages
   - Look for `[get_user_by_id]` messages
   - Check if there are any Python tracebacks now

2. **Possible Root Causes:**
   - JWT token decode failing (wrong SECRET_KEY?)
   - User lookup returning None (UniversalRow issue?)
   - Token format issue (missing Bearer prefix?)
   - Exception being swallowed somewhere

3. **If Logs Show Nothing:**
   - The request might not be reaching the endpoint at all
   - Check if axios is sending the Authorization header correctly
   - Verify the token format in localStorage

4. **Quick Test:**
   - Open browser DevTools → Application → Local Storage
   - Copy the token value
   - Go to https://food-cost-tracker-dev.onrender.com/docs
   - Click "Authorize" button
   - Paste token
   - Try calling `/auth/me` directly from Swagger UI
   - This will show the actual error response

---

## Architecture Summary

### Database Layer
```
┌─────────────────────────────────────────────┐
│         Application Code (Routers)          │
│  cursor.execute("SELECT * FROM users ...")  │
└─────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────┐
│      DatabaseConnectionWrapper.cursor()      │
│    Returns: DatabaseCursorWrapper instance   │
└─────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────┐
│      DatabaseCursorWrapper.execute()         │
│  - Converts ? to %s if PostgreSQL            │
│  - Adds RETURNING id to INSERT               │
└─────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────┐
│     DatabaseCursorWrapper.fetchone()         │
│  - Wraps result in UniversalRow              │
│  - Returns None if no result                 │
└─────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────┐
│             UniversalRow Object              │
│  - Supports row[0] (integer index)           │
│  - Supports row['column'] (dict access)      │
│  - Works with both SQLite and PostgreSQL     │
└─────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────┐
│         dict_from_row() / dict()             │
│  - Extracts _dict from UniversalRow          │
│  - Returns plain Python dict                 │
└─────────────────────────────────────────────┘
```

### Environment Detection
```
Startup → Check DATABASE_URL env var
    │
    ├─ If starts with "postgresql://" → USE_POSTGRES = True
    │   └─ Import psycopg2, use RealDictCursor
    │
    └─ Else → USE_POSTGRES = False
        └─ Use SQLite with DB_PATH
```

### Migration Strategy
```
Render Deploy
    │
    ├─ Dockerfile.render builds app
    │
    └─ CMD runs: alembic upgrade head && uvicorn app.main:app
        │
        └─ db_startup.py checks database type
            │
            ├─ If PostgreSQL → Migrations already ran via alembic
            │
            └─ If SQLite → Run init_db() to create tables
```

---

## Key Files Modified

### Backend
- `api/app/database.py` - Database abstraction layer (UniversalRow, wrappers)
- `api/app/auth.py` - Added debug logging to token validation
- `api/app/routers/auth.py` - Fixed setup endpoint, added logging
- `alembic/versions/cc2c3eef7f15_*.py` - PostgreSQL-compatible migration
- `alembic/env.py` - Support DATABASE_PATH and DATABASE_URL

### Frontend
- `frontend/src/context/AuthContext.jsx` - Added debug logging
- `frontend/src/components/Navigation.jsx` - New component
- `frontend/src/components/Navigation.css` - Styling
- `frontend/src/pages/*.jsx` - Added Navigation to all pages

### Infrastructure
- Render dev environment variables (removed DATABASE_PATH)

---

## Testing Checklist

### Local Testing (SQLite)
- [ ] Login works
- [ ] User creation works
- [ ] Products CRUD works
- [ ] Recipes CRUD works
- [ ] CSV import works
- [ ] Navigation displays correctly

### Dev Environment Testing (PostgreSQL)
- [x] Migrations run successfully
- [x] Setup endpoint creates organization
- [x] Setup endpoint creates admin user
- [x] Login endpoint returns JWT token
- [ ] `/auth/me` endpoint validates token ← **CURRENTLY FAILING**
- [ ] Navigation after login
- [ ] Full app functionality

---

## PostgreSQL vs SQLite Differences

| Feature | SQLite | PostgreSQL | Our Solution |
|---------|--------|------------|--------------|
| Placeholder | `?` | `%s` | Auto-convert in wrapper |
| lastrowid | `cursor.lastrowid` | N/A | Add `RETURNING id` |
| Row Access | `row[0]` and `row['col']` | Only `row['col']` | UniversalRow wrapper |
| Named Constraints | Not enforced | Enforced | try/except in migrations |
| AUTOINCREMENT | AUTOINCREMENT | SERIAL/GENERATED | Handled by models.py |

---

## Environment Variables

### Production (main branch)
```bash
DATABASE_URL=postgresql://username:password@host/database
JWT_SECRET_KEY=<auto-generated>
PORT=8000
```

### Development (dev branch)
```bash
DATABASE_URL=postgresql://username:password@host/database_dev
JWT_SECRET_KEY=<auto-generated>
PORT=8000
LOG_LEVEL=DEBUG
```

### Local Development
```bash
# No env vars needed - defaults to SQLite
# Or set DATABASE_URL for local PostgreSQL testing
```

---

## Troubleshooting Commands

### Check Database Type
```bash
# In Python
import os
DATABASE_URL = os.getenv("DATABASE_URL")
USE_POSTGRES = DATABASE_URL and DATABASE_URL.startswith("postgresql")
print(f"Using PostgreSQL: {USE_POSTGRES}")
```

### Verify Migrations
```bash
# Check current version
venv/bin/alembic current

# View history
venv/bin/alembic history

# Run migrations
venv/bin/alembic upgrade head
```

### Test Token Locally
```bash
# Decode JWT token (install pyjwt first)
python -c "
import jwt
token = 'YOUR_TOKEN_HERE'
secret = 'YOUR_SECRET_HERE'
print(jwt.decode(token, secret, algorithms=['HS256']))
"
```

### Check Render Logs
```bash
# From Render dashboard, or use render CLI
# Look for our custom debug messages:
# - [get_current_user]
# - [decode_token]
# - [get_user_by_id]
```

---

## Git Commits Made Today

1. `Fix Alembic migration to work with PostgreSQL` - Removed batch_alter_table
2. `Fix database.py to connect to PostgreSQL` - Added psycopg2 support
3. `Fix PostgreSQL row access compatibility` - Added UniversalRow wrapper
4. `Fix setup endpoint to create default organization` - Organization creation
5. `Add error logging and org existence check to setup` - Better error handling
6. `Fix dict conversion for UniversalRow objects` - dict_from_row fix
7. `Add debug logging to auth functions` - Frontend logging
8. `Add detailed logging to auth token validation` - Backend logging

---

## Resources

- **Render Dashboard:** https://dashboard.render.com
- **Production:** https://food-cost-tracker.onrender.com
- **Dev:** https://food-cost-tracker-dev.onrender.com
- **Swagger Docs (Dev):** https://food-cost-tracker-dev.onrender.com/docs

---

**Status:** Ready to resume debugging tomorrow. All logging is in place - just need to test login and check Render logs for detailed output.
