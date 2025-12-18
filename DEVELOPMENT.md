# Development Guide

Complete guide for local development, git workflow, testing, and deployment.

---

## Table of Contents

- [Local Development Setup](#local-development-setup)
- [Git Workflow](#git-workflow)
- [Database Management](#database-management)
- [Testing Guidelines](#testing-guidelines)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)

---

## Local Development Setup

### Prerequisites

- **Python 3.12+**
- **Node.js 20+**
- **PostgreSQL 16+** (local installation or Render)
- **Git**

### Initial Setup

#### 1. Clone Repository

```bash
git clone https://github.com/CxRxExAxM/food-cost-tracker.git
cd food-cost-tracker
```

#### 2. Set Up PostgreSQL Database

**Option A: Local PostgreSQL**

```bash
# Create database
createdb food_cost_tracker_local

# Set environment variable (add to ~/.bashrc or ~/.zshrc)
export DATABASE_URL="postgresql://localhost/food_cost_tracker_local"
```

**Option B: Use Render PostgreSQL (Dev)**

```bash
# Get DATABASE_URL from Render dashboard
export DATABASE_URL="postgresql://user:pass@host/database"
```

#### 3. Set Up Python Backend

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
venv/bin/alembic upgrade head
```

This creates all tables and seeds distributors/units.

#### 4. Start Backend Server

```bash
cd api
../venv/bin/uvicorn app.main:app --reload --port 8000
```

- API available at: http://localhost:8000
- API docs (Swagger): http://localhost:8000/docs
- API docs (ReDoc): http://localhost:8000/redoc

#### 5. Set Up Frontend

```bash
# New terminal, from project root
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend available at: http://localhost:5173

#### 6. Initial Application Setup

1. Navigate to http://localhost:5173
2. Click **"Initial Setup"** button
3. Create admin user account:
   - Email: your@email.com
   - Username: admin
   - Password: secure_password
   - Full Name: Your Name
4. Login with created credentials
5. Start using the application!

---

## Git Workflow

### Branch Strategy (Current)

```
main (production)
  └── dev (development)
      ├── feature/* (short-lived)
      └── fix/* (short-lived)
```

**Branch Purposes:**
- `main` - Production environment (https://food-cost-tracker.onrender.com)
- `dev` - Development environment (https://food-cost-tracker-dev.onrender.com)
- `feature/*` - New features (branch from `dev`)
- `fix/*` - Bug fixes (branch from `dev`)

### Feature Development Process

```bash
# 1. Start from dev branch
git checkout dev
git pull origin dev

# 2. Create feature branch
git checkout -b feature/your-feature-name

# 3. Make changes and commit
git add .
git commit -m "feat: description of your feature"

# 4. Push feature branch
git push origin feature/your-feature-name

# 5. Merge to dev for testing
git checkout dev
git merge feature/your-feature-name
git push origin dev
# Auto-deploys to dev.onrender.com

# 6. Test in dev environment
# Verify functionality at https://food-cost-tracker-dev.onrender.com

# 7. Deploy to production when ready
git checkout main
git merge dev
git push origin main
# Auto-deploys to production
```

### Commit Message Format

Follow conventional commits format:

```
<type>: <description>

[optional body]
[optional footer]
```

**Types:**
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation only
- `refactor:` - Code restructuring (no functionality change)
- `test:` - Adding or updating tests
- `chore:` - Maintenance (dependencies, build, etc.)
- `perf:` - Performance improvements
- `style:` - Code style/formatting

**Examples:**
```bash
git commit -m "feat: Add temperature monitoring UI for HACCP module"
git commit -m "fix: Correct impersonation to use AuthContext.setToken"
git commit -m "docs: Update README with Phase 4 completion status"
git commit -m "refactor: Reorganize docs into archive structure"
```

### Hotfix Process (Critical Production Bugs)

```bash
# 1. Branch from main
git checkout main
git pull origin main
git checkout -b hotfix/critical-issue

# 2. Fix quickly
# ... make changes ...
git commit -m "hotfix: Fix critical payment processing error"

# 3. Deploy to production
git checkout main
git merge hotfix/critical-issue
git push origin main

# 4. Back-merge to dev
git checkout dev
git merge main
git push origin dev
```

---

## Database Management

### Alembic Migrations

#### Create New Migration

```bash
# After modifying models in api/app/models.py
venv/bin/alembic revision --autogenerate -m "Description of changes"

# Or create empty migration for manual SQL
venv/bin/alembic revision -m "Description of changes"
```

#### Run Migrations

```bash
# Upgrade to latest
venv/bin/alembic upgrade head

# Upgrade to specific version
venv/bin/alembic upgrade <revision>

# Rollback one migration
venv/bin/alembic downgrade -1

# Rollback to specific version
venv/bin/alembic downgrade <revision>
```

#### Check Migration Status

```bash
# View current version
venv/bin/alembic current

# View migration history
venv/bin/alembic history

# View pending migrations
venv/bin/alembic history --verbose
```

### Database Backup & Restore

```bash
# Backup database
pg_dump -h <host> -U <user> -d <database> > backup_$(date +%Y%m%d).sql

# Restore database
psql -h <host> -U <user> -d <database> < backup_20241217.sql
```

### Connecting to Render PostgreSQL

```bash
# Get connection details from Render dashboard
# External Database URL format:
# postgresql://user:password@host:port/database

# Connect via psql
psql "postgresql://user:password@host:port/database"

# Or set DATABASE_URL
export DATABASE_URL="postgresql://user:password@host:port/database"
alembic upgrade head
```

---

## Testing Guidelines

### Manual Testing Checklist

Before merging to main, verify:

#### Multi-Tenancy
- [ ] Create test organization
- [ ] Verify data isolation (can't see other org's data)
- [ ] Test with 2+ organizations

#### User Roles
- [ ] Admin - Full organization access
- [ ] Chef - Outlet-specific access
- [ ] Viewer - Read-only access
- [ ] Test outlet assignments work correctly

#### Core Functionality
- [ ] Upload distributor CSV
- [ ] Map products to common products
- [ ] Create recipe with ingredients
- [ ] Verify recipe cost calculation
- [ ] Test allergen auto-aggregation
- [ ] "Refresh Costs" updates recipe costs

#### Multi-Outlet
- [ ] Create multiple outlets
- [ ] Same recipe costs differently per outlet
- [ ] Outlet selector filters data correctly
- [ ] Users see only assigned outlets (non-admins)

#### Super Admin
- [ ] Create organization
- [ ] Update subscription tier
- [ ] Impersonate organization
- [ ] View audit logs
- [ ] Exit impersonation

### Key User Flows

**Flow 1: New Organization Setup**
1. Super admin creates organization
2. Creates first admin user
3. User logs in, creates outlet
4. Uploads price list
5. Creates first recipe

**Flow 2: Recipe Costing**
1. User logs in, selects outlet
2. Creates common products
3. Uploads distributor prices
4. Maps products to common products
5. Creates recipe
6. Verifies cost calculation
7. Changes outlet, costs update

**Flow 3: Multi-Outlet Operations**
1. Admin creates second outlet
2. Uploads price list for new outlet
3. Same recipe shows different cost
4. Creates non-admin user
5. Assigns user to specific outlet
6. User only sees assigned outlet

### Edge Cases to Test

- Empty states (no outlets, no products, no recipes)
- Permissions (non-admin trying to access admin features)
- Missing data (product with no price, recipe with unmapped ingredient)
- Large datasets (1000+ products, 100+ recipes)
- Concurrent users (multiple users editing simultaneously)

---

## Deployment

### Automatic Deploys (Render.com)

**Production Deployment:**
```bash
git checkout main
git merge dev
git push origin main
# Triggers automatic deploy to food-cost-tracker.onrender.com
```

**Development Deployment:**
```bash
git checkout dev
git push origin dev
# Triggers automatic deploy to food-cost-tracker-dev.onrender.com
```

### Deployment Process (Automatic)

1. **Render detects push** to main or dev branch
2. **Docker build starts**:
   - Frontend builds (Vite)
   - Backend prepares (Python)
3. **Migrations run**: `alembic upgrade head`
4. **Server starts**: `uvicorn api.app.main:app --host 0.0.0.0 --port ${PORT}`
5. **Health check** confirms deployment
6. **Traffic switches** to new deployment

### Environment Variables (Render Dashboard)

**Required:**
```bash
DATABASE_URL  # Auto-provided by Render PostgreSQL
JWT_SECRET_KEY  # Auto-generated on first deploy
PORT  # Auto-set by Render
```

**Optional:**
```bash
ANTHROPIC_API_KEY  # For AI recipe parser (future)
PYTHON_ENV=production
```

### Manual Deploy (Force Redeploy)

```bash
# Trigger deploy without code changes
git commit --allow-empty -m "Trigger deploy"
git push origin main
```

### Viewing Deployment Logs

1. Go to Render dashboard
2. Click on service (food-cost-tracker or food-cost-tracker-dev)
3. Click **"Logs"** tab
4. Watch for:
   - Build completion
   - Migration execution
   - Server startup
   - Any errors

### Rollback Deployment

**Option 1: Render Dashboard**
1. Go to service → Events tab
2. Find previous successful deployment
3. Click "Redeploy"

**Option 2: Git Revert**
```bash
# Revert to previous commit
git revert HEAD
git push origin main
```

---

## Troubleshooting

### Common Issues

#### "DATABASE_URL environment variable is required"

**Solution:**
```bash
# Set DATABASE_URL
export DATABASE_URL="postgresql://localhost/food_cost_tracker_local"

# Or add to ~/.bashrc or ~/.zshrc
echo 'export DATABASE_URL="postgresql://localhost/food_cost_tracker_local"' >> ~/.bashrc
source ~/.bashrc
```

#### CORS Errors in Frontend

**Symptoms:** API requests fail with CORS errors in browser console

**Solution:**
- Ensure backend is running on port 8000
- Check CORS middleware in `api/app/main.py`
- Verify frontend is using correct API URL (localhost:8000)

#### Migration Errors

**"Target database is not up to date"**
```bash
# Check current version
venv/bin/alembic current

# Upgrade to latest
venv/bin/alembic upgrade head
```

**"Can't locate revision identified by 'xyz'"**
```bash
# Migration file missing, regenerate
venv/bin/alembic revision -m "Recreate migration"
```

#### Products Not Showing Prices

**Causes:**
- Product not mapped to common_product
- No price_history entries for outlet
- Outlet selector on wrong outlet

**Solution:**
```bash
# Check product mapping
SELECT p.id, p.description, p.common_product_id
FROM products p
WHERE p.id = <product_id>;

# Check price history
SELECT * FROM price_history
WHERE product_id = <product_id> AND outlet_id = <outlet_id>
ORDER BY effective_date DESC LIMIT 1;
```

#### Frontend Build Errors

**"Module not found" errors**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

**Port 5173 already in use**
```bash
# Kill process on port 5173
lsof -ti:5173 | xargs kill -9

# Or use different port
npm run dev -- --port 5174
```

#### Backend Won't Start

**"Port 8000 already in use"**
```bash
# Find and kill process
lsof -ti:8000 | xargs kill -9
```

**"No module named 'app'"**
```bash
# Ensure you're in api directory
cd api
../venv/bin/uvicorn app.main:app --reload
```

### Debug Mode

**Backend Debug Logging:**
```python
# In api/app/main.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Frontend Debug Mode:**
```javascript
// In frontend/src/lib/axios.js
axios.interceptors.request.use(request => {
  console.log('Request:', request);
  return request;
});
```

---

## Development Tools

### Recommended VS Code Extensions

- **Python** - Microsoft
- **Pylance** - Microsoft
- **ES7+ React/Redux/React-Native snippets**
- **Prettier - Code formatter**
- **ESLint**
- **PostgreSQL** - cweijan

### Database GUI Tools

- **TablePlus** (Mac/Windows) - https://tableplus.com
- **pgAdmin** (Cross-platform) - https://www.pgadmin.org
- **DBeaver** (Cross-platform) - https://dbeaver.io

### API Testing

- **Swagger UI** - Built-in at http://localhost:8000/docs
- **Postman** - https://www.postman.com
- **HTTPie** - https://httpie.io (CLI)

---

## Performance Tips

### Backend Optimization

- Use database indexes for frequently queried columns
- Implement pagination for large datasets
- Cache expensive calculations
- Use database connection pooling

### Frontend Optimization

- Lazy load routes and components
- Debounce search inputs
- Use React.memo for expensive components
- Optimize images and assets

### Database Optimization

- Regularly vacuum and analyze tables
- Monitor slow queries
- Use appropriate data types
- Add indexes on foreign keys

---

## Quick Reference

### Start Development

```bash
# Terminal 1: Backend
cd api
../venv/bin/uvicorn app.main:app --reload

# Terminal 2: Frontend
cd frontend
npm run dev
```

### Run Migrations

```bash
venv/bin/alembic upgrade head
```

### Deploy to Production

```bash
git checkout main
git merge dev
git push origin main
```

### View Logs

- **Local Backend:** Terminal output
- **Local Frontend:** Browser console (F12)
- **Production:** Render dashboard → Logs tab

---

**For more information:**
- **Project Overview:** [README.md](README.md)
- **Future Roadmap:** [FUTURE_PLANS.md](FUTURE_PLANS.md)
- **UI Guidelines:** [DESIGN_SYSTEM.md](DESIGN_SYSTEM.md)
- **AI Development:** [CLAUDE_INSTRUCTIONS.md](CLAUDE_INSTRUCTIONS.md)

---

**Last Updated:** December 17, 2024
