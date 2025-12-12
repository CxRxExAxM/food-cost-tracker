# Food Cost Tracker

A comprehensive platform for F&B operations to manage food costs, track distributor prices, and calculate recipe costs with real-time pricing updates.

**Live Production:** https://food-cost-tracker.onrender.com
**Dev Environment:** https://food-cost-tracker-dev.onrender.com

## Features

### Core Functionality (v1.0) ✅
- **User Authentication** - Role-based access control (Admin, Chef, Viewer)
- **Multi-Distributor Support** - Import and track prices from multiple distributors
  - Sysco, Vesta, SM Seafood, Shamrock, Noble Bread, Sterling
  - Automated CSV cleaning with vendor-specific rules
- **Product Management**
  - Inline editing for quick corrections
  - Product-to-common-product mapping with autocomplete
  - Catch weight support for variable-weight items
- **Recipe Builder**
  - Folder/category organization with nested categories
  - Live cost calculation with automatic price updates
  - Yield percentage support for prep waste
  - Sub-recipe support (recipes within recipes)
  - Cost breakdown per ingredient with percentages
  - "Refresh Costs" button to update when prices change
- **Allergen & Dietary Tracking**
  - 16 allergen flags per ingredient (Vegan, Vegetarian, Gluten, Dairy, etc.)
  - Auto-aggregation from recipe ingredients
- **Price History Tracking** - Time-series price data for trend analysis

### Recently Completed ✅
- **Multi-Tenancy Support** (Dec 12, 2025)
  - Complete organization-based data isolation
  - Tier-based system (Free, Basic, Pro, Enterprise)
  - Organizations table with subscription management
  - All data scoped to organizations (products, recipes, users, imports)
  - Tested and verified data isolation between organizations
  - See MULTI_TENANCY_DEC12.md for details

- **PostgreSQL Migration** (Dec 11, 2025)
  - Clean PostgreSQL-only architecture
  - Removed dual SQLite/PostgreSQL complexity
  - Production-ready on Render
  - See POSTGRESQL_MIGRATION_DEC11.md for details

### Upcoming Features 📋
- **Organization Admin UI** - Frontend interface for organization management
  - Organization settings page
  - User invitation system
  - Tier limits display and enforcement
- **AI Recipe Parser**
  - Upload Word/PDF recipe documents
  - Claude API extracts ingredients automatically
  - Smart matching to common products
  - Review/confirmation workflow
- **Historical Price Charts** - Visualize price trends over time
- **Recipe Scaling** - Scale recipes up/down
- **PDF Export** - Print recipe cards

## Tech Stack

### Backend
- **Framework:** FastAPI 0.104+
- **Database:** PostgreSQL 16+ (Render PostgreSQL)
- **ORM:** SQLAlchemy 2.0+ with Alembic migrations
- **Authentication:** JWT tokens with passlib/bcrypt
- **File Processing:** pandas, openpyxl, xlrd for CSV/Excel imports

### Frontend
- **Framework:** React 18 + Vite
- **Routing:** React Router v6
- **HTTP Client:** Axios with JWT interceptors
- **State Management:** React Context API
- **UI:** Custom CSS with responsive design

### Deployment
- **Platform:** Render.com
- **Environments:**
  - Production (main branch) - https://food-cost-tracker.onrender.com
  - Development (dev branch) - https://food-cost-tracker-dev.onrender.com
- **Docker:** Multi-stage build (frontend + backend)
- **Database:** Render PostgreSQL (production-grade)

## Project Structure

```
Clean_Invoices/
├── api/                      # FastAPI backend
│   ├── app/
│   │   ├── routers/         # API route handlers
│   │   │   ├── auth.py      # User authentication & JWT
│   │   │   ├── products.py  # Product CRUD & mapping
│   │   │   ├── common_products.py  # Common product library
│   │   │   ├── recipes.py   # Recipe CRUD & costing
│   │   │   ├── uploads.py   # CSV import handling
│   │   │   ├── distributors.py  # Distributor management
│   │   │   └── units.py     # Units of measure
│   │   ├── main.py          # FastAPI app setup
│   │   ├── database.py      # PostgreSQL connection (39 lines!)
│   │   ├── db_startup.py    # Alembic migration runner
│   │   ├── models.py        # SQLAlchemy ORM models
│   │   ├── schemas.py       # Pydantic request/response models
│   │   └── auth.py          # JWT auth utilities
│   └── run.py               # Development server
├── frontend/                 # React + Vite frontend
│   ├── src/
│   │   ├── pages/           # Page components
│   │   │   ├── Home.jsx
│   │   │   ├── Login.jsx
│   │   │   ├── Products.jsx
│   │   │   ├── Recipes.jsx
│   │   │   └── Users.jsx
│   │   ├── components/      # Reusable components
│   │   ├── context/         # React Context providers
│   │   ├── services/        # API client
│   │   └── App.jsx
│   ├── package.json
│   └── vite.config.js
├── alembic/                  # Database migrations
│   ├── versions/
│   │   └── 001_initial_schema.py  # Single clean migration
│   ├── env.py
│   └── alembic.ini
├── clean_*.py               # CSV cleaning scripts by distributor
├── Dockerfile.render        # Production Docker build
├── render-dev.yaml          # Dev environment config
├── requirements.txt
└── POSTGRESQL_MIGRATION_DEC11.md  # Migration documentation

```

## Database Schema

### Core Tables

**organizations** 🆕
- Multi-tenant organization management
- Subscription tiers: free, basic, pro, enterprise
- Tier-based limits (max_users, max_recipes)
- All user data scoped to organizations

**users**
- User accounts with role-based permissions (admin, chef, viewer)
- JWT authentication with bcrypt password hashing
- Scoped to organization (organization_id foreign key)

**distributors** (seeded, shared)
- 6 food distributors (Sysco, Vesta, etc.)
- Shared across all organizations

**units** (seeded, shared)
- 23 units of measure (LB, OZ, GAL, QT, EA, etc.)
- Organized by type: weight, volume, count

**common_products**
- Normalized ingredient library (e.g., "Red Onion", "Chicken Breast 6oz")
- Master products with allergen flags
- Used for consistent recipe ingredients
- Scoped to organization (organization_id foreign key)

**products**
- Distributor-specific products with pack size, pricing
- Maps to common_products for normalization
- Tracks brand, catch weight status
- Scoped to organization (organization_id foreign key)

**distributor_products**
- Junction table linking products to distributors
- Stores distributor SKU numbers
- Scoped to organization (organization_id foreign key)

**price_history**
- Time-series pricing data
- effective_date tracks price changes over time

**recipes**
- Recipe definitions with category hierarchy
- Yield amount and unit
- Method stored as JSON
- Scoped to organization (organization_id foreign key)

**recipe_ingredients**
- Recipe components referencing common_products
- Supports sub-recipes for complex builds
- Yield percentage for waste calculation

**import_batches**
- CSV import audit trail
- Scoped to organization (organization_id foreign key)

### Data Model Flow

```
Distributors → Products → Common Products → Recipes
                  ↓              ↓
         Distributor Products    Recipe Ingredients
                  ↓
            Price History
```

**Why this works:**
- Compare prices across multiple distributors
- Recipes stay consistent when switching suppliers
- Historical price tracking per distributor
- Users control their ingredient library

## Quick Start

### Prerequisites
- Python 3.12+
- Node.js 20+
- PostgreSQL 16+ (local or Render)

### Local Development Setup

1. **Clone the repository**
```bash
git clone https://github.com/CxRxExAxM/food-cost-tracker.git
cd food-cost-tracker
```

2. **Set up PostgreSQL database**
```bash
# Create database
createdb food_cost_tracker_local

# Set environment variable
export DATABASE_URL="postgresql://localhost/food_cost_tracker_local"
```

3. **Set up Python virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

4. **Run database migrations**
```bash
venv/bin/alembic upgrade head
```
This creates all tables and seeds distributors/units.

5. **Start the backend**
```bash
cd api
../venv/bin/uvicorn app.main:app --reload --port 8000
```
- API available at http://localhost:8000
- API docs at http://localhost:8000/docs

6. **Start the frontend**
```bash
# New terminal, from project root
cd frontend
npm install
npm run dev
```
Frontend available at http://localhost:5173

7. **Initial Setup**
- Navigate to http://localhost:5173
- Click "Initial Setup"
- Create admin user account
- Login and start using the app

## CSV Import Workflow

### 1. Clean distributor CSV
```bash
# Activate virtual environment
source venv/bin/activate

# Clean based on distributor
python clean_sysco.py sysco_export.csv
python clean_vesta.py vesta_export.csv
python clean_smseafood.py smseafood_export.csv
# etc.
```

### 2. Import via UI
- Navigate to Products page
- Click "Import Products"
- Select distributor from dropdown
- Upload cleaned CSV/Excel file
- View import summary

### 3. Map products
- Products import unmapped initially
- Use autocomplete to map to common products
- Create new common products as needed
- Mapped products auto-populate in recipes

## API Endpoints

### Authentication
- `POST /auth/setup` - Initial admin user creation
- `POST /auth/login` - Login and get JWT token
- `GET /auth/me` - Get current user info
- `PUT /auth/me` - Update current user
- `GET /auth/users` - List all users (admin only)
- `POST /auth/users` - Create new user (admin only)

### Products
- `GET /products` - List products (pagination, filters, search)
- `GET /products/{id}` - Get product details with pricing
- `PATCH /products/{id}` - Update product
- `PATCH /products/{id}/map` - Map to common product
- `PATCH /products/{id}/unmap` - Remove common product mapping

### Common Products
- `GET /common-products` - List common products
- `POST /common-products` - Create common product
- `GET /common-products/{id}` - Get details
- `PATCH /common-products/{id}` - Update (including allergens)
- `DELETE /common-products/{id}` - Soft delete
- `GET /common-products/{id}/products` - Get all distributor products mapped to this

### Recipes
- `GET /recipes` - List all recipes with folder structure
- `POST /recipes` - Create recipe
- `GET /recipes/{id}` - Get recipe details with ingredients
- `GET /recipes/{id}/cost` - Calculate recipe cost with breakdown
- `PATCH /recipes/{id}` - Update recipe
- `DELETE /recipes/{id}` - Soft delete recipe
- `GET /recipes/categories` - Get category tree

### Uploads
- `POST /uploads/csv` - Upload and import distributor CSV
- `GET /uploads/distributors` - List available distributors
- `GET /uploads/batches` - Get import history

Full API documentation: http://localhost:8000/docs

## Git Workflow

### Branch Structure
- `main` - Production (auto-deploys to Render)
- `dev` - Staging/testing (auto-deploys to dev environment)
- `feature/*` - Individual features

### Feature Development
```bash
# Start new feature
git checkout dev
git pull origin dev
git checkout -b feature/feature-name

# Work and commit
git add .
git commit -m "feat: description"

# Push and create PR
git push origin feature/feature-name
# Create PR: feature → dev
# Test in dev environment
# Merge dev → main when ready
```

## Deployment

### Automatic Deploys (Render.com)

**Production:**
- Push to `main` → Production deployment
- URL: https://food-cost-tracker.onrender.com

**Development:**
- Push to `dev` → Dev deployment
- URL: https://food-cost-tracker-dev.onrender.com

### Environment Variables (Render Dashboard)
```bash
DATABASE_URL=postgresql://user:pass@host/database  # Auto-provided by Render
JWT_SECRET_KEY=<auto-generated-secret>
PORT=8000  # Set by Render
```

### Startup Process
1. Docker builds frontend (Vite) and backend (Python)
2. `db_startup.py` runs Alembic migrations
3. Uvicorn starts FastAPI server on PORT
4. Static frontend served by FastAPI

### Manual Deploy
```bash
# Trigger redeploy without code changes
git commit --allow-empty -m "Trigger deploy"
git push origin main
```

## Database Management

### Alembic Migrations

```bash
# Create new migration (after model changes)
venv/bin/alembic revision --autogenerate -m "Description of changes"

# Run migrations
venv/bin/alembic upgrade head

# Rollback migration
venv/bin/alembic downgrade -1

# View migration history
venv/bin/alembic history

# Check current version
venv/bin/alembic current
```

### Database Backup
```bash
# Dump database
pg_dump -h <host> -U <user> -d <database> > backup_$(date +%Y%m%d).sql

# Restore database
psql -h <host> -U <user> -d <database> < backup_20251211.sql
```

## Development Tips

### Debugging
- Backend logs: Render dashboard or local terminal
- Frontend errors: Browser console (F12)
- Database queries: Use `/docs` to test API endpoints interactively
- PostgreSQL client: Use pgAdmin, TablePlus, or psql CLI

### Common Issues

**"DATABASE_URL environment variable is required"**
- Set DATABASE_URL pointing to your PostgreSQL instance
- Local: `export DATABASE_URL="postgresql://localhost/food_cost_tracker_local"`

**CORS errors in frontend**
- Backend must be running on port 8000
- Check CORS middleware in `api/app/main.py`

**Migration errors**
- Ensure DATABASE_URL is set correctly
- Check Alembic is using correct database: `alembic current`

**Products not showing prices**
- Verify product is mapped to common_product
- Check price_history has recent entries
- Use "Refresh Costs" button in recipe view

## Roadmap

### Completed ✅
- Multi-distributor import system with CSV cleaning
- Product-to-common-product mapping
- Recipe builder with folder organization
- Live cost calculation with yield percentages
- Allergen auto-aggregation from ingredients
- User authentication with role-based permissions
- PostgreSQL-only architecture (simplified, production-ready)
- Dev/staging environment

### In Progress 🚧
- Multi-tenancy architecture (organization-based data isolation)
- Organization admin interface
- Tier system (Free, Basic, Pro, Enterprise)

### Planned 📋
- AI Recipe Parser (Claude API integration)
  - Upload Word/PDF documents
  - Auto-extract ingredients
  - Smart common product matching
- Historical price charts with trend analysis
- Recipe scaling calculator
- PDF export for recipe cards
- Mobile-responsive improvements

### Future Modules 🔮
- Labor scheduling & cost tracking
- Daily P&L tracking (revenue vs food cost)
- HACCP compliance & allergen labeling
- Menu engineering & profitability analysis
- Inventory management integration

## Performance

### Current Metrics (Dev Environment)
- Average API response time: <200ms
- CSV import: ~1000 products in ~5 seconds
- Recipe cost calculation: Real-time (<100ms)
- Database: Render PostgreSQL (free tier)

### Code Quality
- **39 lines** for database.py (down from 549)
- **~700 lines removed** in PostgreSQL migration
- Clean, maintainable codebase
- Comprehensive error logging

## Contributing

This is a personal project, but suggestions and bug reports are welcome!

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

Proprietary - All Rights Reserved

## Support

For issues or questions:
- Open a GitHub issue
- Check docs: POSTGRESQL_MIGRATION_DEC11.md
- API docs: https://food-cost-tracker-dev.onrender.com/docs

---

**Built with ❤️ by an operator, for operators**
