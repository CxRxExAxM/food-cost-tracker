# Food Cost Tracker

A comprehensive SaaS platform for F&B operations to manage food costs, track distributor prices, and calculate recipe costs with AI-powered recipe parsing.

**Live Production:** https://food-cost-tracker.onrender.com
**Live Demo:** demo@demo.com / demo1234

## Features

### Core Functionality (v1.0)
- **User Authentication** - Role-based access control (Admin, Chef, Viewer)
- **Multi-Distributor Support** - Import and track prices from multiple distributors
  - Sysco, Vesta, SM Seafood, Shamrock, Noble Bread, Sterling
- **Product Management**
  - Inline editing for quick corrections
  - Product-to-common-product mapping with autocomplete
  - Catch weight support
- **Recipe Builder**
  - Folder/category organization with nested categories
  - Live cost calculation with automatic price updates
  - Yield percentage support for prep waste
  - Sub-recipe support (recipes within recipes)
  - Cost breakdown per ingredient with percentages
  - "Refresh Costs" button to update when prices change
- **Allergen & Dietary Tracking**
  - 16 allergen flags per ingredient (Vegan, Vegetarian, Gluten, etc.)
  - Auto-aggregation from recipe ingredients
- **Price History Tracking** - Time-series price data for trend analysis

### Recent Additions
- **PostgreSQL Migration** - Multi-tenant database with Alembic migrations
- **Automatic Database Initialization** - Detects SQLite vs PostgreSQL on startup
- **Dev Environment** - Separate staging environment for testing features

### Upcoming Features
- **AI Recipe Parser** (In Development)
  - Upload Word/PDF recipe documents
  - Claude API extracts ingredients automatically
  - Smart matching to common products
  - Review/confirmation workflow
- **Historical Price Charts** - Visualize price trends
- **Recipe Scaling** - Scale recipes up/down
- **PDF Export** - Print recipe cards

## Tech Stack

### Backend
- **Framework:** FastAPI 0.104+
- **Database:** PostgreSQL (production) / SQLite (local dev)
- **ORM:** SQLAlchemy 2.0+
- **Migrations:** Alembic 1.13+
- **Authentication:** JWT tokens with passlib/bcrypt
- **File Processing:** pandas, openpyxl, xlrd

### Frontend
- **Framework:** React 18 + Vite
- **Routing:** React Router v6
- **HTTP Client:** Axios
- **State Management:** React Context API
- **UI:** Custom CSS with responsive design

### Deployment
- **Platform:** Render.com
- **Environments:**
  - Production (main branch) - https://food-cost-tracker.onrender.com
  - Development (dev branch) - Staging environment
- **Docker:** Multi-stage build (frontend + backend)
- **Database:** Render PostgreSQL (free tier)

## Project Structure

```
Clean_Invoices/
├── api/                      # FastAPI backend
│   ├── app/
│   │   ├── routers/         # API route handlers
│   │   │   ├── auth.py      # User authentication
│   │   │   ├── products.py  # Product management
│   │   │   ├── common_products.py
│   │   │   ├── recipes.py   # Recipe CRUD & costing
│   │   │   ├── uploads.py   # CSV import handling
│   │   │   ├── distributors.py
│   │   │   └── units.py
│   │   ├── main.py          # FastAPI app setup
│   │   ├── database.py      # SQLite connection & init
│   │   ├── db_startup.py    # Auto DB initialization
│   │   ├── models.py        # SQLAlchemy ORM models
│   │   ├── schemas.py       # Pydantic models
│   │   └── auth.py          # JWT auth utilities
│   └── run.py               # Development server
├── frontend/                 # React + Vite frontend
│   ├── src/
│   │   ├── pages/           # Page components
│   │   │   ├── Home.jsx     # Dashboard
│   │   │   ├── Login.jsx    # Authentication
│   │   │   ├── Products.jsx # Product management
│   │   │   ├── Recipes.jsx  # Recipe builder
│   │   │   └── Users.jsx    # User management
│   │   ├── components/      # Reusable components
│   │   ├── context/         # React Context providers
│   │   │   └── AuthContext.jsx
│   │   ├── services/        # API client
│   │   └── App.jsx          # Root component
│   ├── package.json
│   └── vite.config.js
├── alembic/                  # Database migrations
│   ├── versions/            # Migration scripts
│   ├── env.py              # Alembic environment
│   └── alembic.ini         # Alembic configuration
├── db/                       # Local SQLite & utilities
│   ├── setup_db.py         # SQLite initialization
│   └── migrations/         # Legacy migration scripts
├── clean_*.py               # CSV cleaning scripts by distributor
├── import_csv.py            # Generic CSV import tool
├── Dockerfile.render        # Production Docker build
├── render-dev.yaml          # Dev environment config
├── requirements.txt         # Python dependencies
└── project_context.md       # Development roadmap

```

## Database Schema

### Core Tables

**users**
- User accounts with role-based permissions
- Roles: admin, chef, viewer

**distributors**
- Food distributors (Sysco, Vesta, etc.)
- Seeded with 6 default distributors

**units**
- Units of measure (LB, OZ, GAL, QT, EA, etc.)
- Organized by type: weight, volume, count

**common_products**
- User-defined normalized ingredients
- Master ingredient library with allergen flags
- Example: "Red Onion", "Chicken Breast 6oz"

**products**
- Distributor-specific products
- Pack size, unit, brand information
- References common_products for mapping

**distributor_products**
- Junction table linking products to distributors
- Stores SKU and distributor-specific names

**price_history**
- Time-series price tracking
- Links to distributor_products with effective dates

**recipes**
- Recipe definitions with yield, servings, method
- Supports nested categories (Sauces/Hot Sauces)

**recipe_ingredients**
- Recipe components referencing common_products
- Supports sub-recipes
- Yield percentage for prep waste calculation

**import_batches**
- Tracks CSV import operations for audit trail

### Data Model Flow

```
Distributors → Products → Common Products → Recipes
                  ↓              ↓
         Distributor Products    Recipe Ingredients
                  ↓
            Price History
```

**Why this works:**
- Multi-distributor price comparison
- Users control their ingredient library
- Recipes stay consistent when switching distributors
- Historical price tracking per distributor

## Quick Start

### Prerequisites
- Python 3.12+
- Node.js 20+
- PostgreSQL (optional, for production-like setup)

### Local Development Setup

1. **Clone the repository**
```bash
git clone https://github.com/CxRxExAxM/food-cost-tracker.git
cd food-cost-tracker
```

2. **Set up Python virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. **Initialize SQLite database**
```bash
python db/setup_db.py
```
This creates `db/food_cost_tracker.db` with all tables, seed data, and a demo user.

4. **Start the backend**
```bash
# From project root
cd api
../venv/bin/uvicorn app.main:app --reload --port 8000
```
API available at http://localhost:8000
API docs at http://localhost:8000/docs

5. **Start the frontend**
```bash
# New terminal, from project root
cd frontend
npm install
npm run dev
```
Frontend available at http://localhost:5173

6. **Login**
- Email: `demo@demo.com`
- Password: `demo1234`

### Using PostgreSQL Locally

1. **Set DATABASE_URL environment variable**
```bash
export DATABASE_URL="postgresql://user:password@localhost/food_cost_tracker"
```

2. **Run migrations**
```bash
venv/bin/alembic upgrade head
```

3. **Start the application** (will auto-detect PostgreSQL)
```bash
cd api
../venv/bin/uvicorn app.main:app --reload --port 8000
```

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

### 2. Import via API
- Navigate to Products page
- Click "Import Products"
- Select distributor from dropdown
- Upload cleaned CSV
- View import summary

### 3. Map products
- Products import unmapped initially
- Use autocomplete to map to common products
- Create new common products as needed

## API Endpoints

### Authentication
- `POST /auth/register` - Create new user (admin only)
- `POST /auth/login` - Login and get JWT token
- `GET /auth/me` - Get current user info
- `PUT /auth/me` - Update current user
- `GET /auth/users` - List all users (admin only)

### Products
- `GET /api/products` - List all products (with filters)
- `GET /api/products/{id}` - Get product details
- `PUT /api/products/{id}` - Update product
- `DELETE /api/products/{id}` - Delete product
- `PUT /api/products/{id}/map` - Map to common product

### Common Products
- `GET /api/common-products` - List common products
- `POST /api/common-products` - Create common product
- `GET /api/common-products/{id}` - Get details
- `PUT /api/common-products/{id}` - Update
- `DELETE /api/common-products/{id}` - Delete
- `GET /api/common-products/search` - Autocomplete search

### Recipes
- `GET /api/recipes` - List all recipes
- `POST /api/recipes` - Create recipe
- `GET /api/recipes/{id}` - Get recipe details
- `GET /api/recipes/{id}/cost` - Calculate recipe cost
- `PUT /api/recipes/{id}` - Update recipe
- `DELETE /api/recipes/{id}` - Delete recipe
- `GET /api/recipes/categories` - Get category tree

### Uploads
- `POST /api/upload` - Upload and import distributor CSV
- `GET /api/distributors` - List distributors
- `GET /api/units` - List units of measure

Full API documentation: http://localhost:8000/docs

## Git Workflow

### Branch Structure
- `main` - Production (auto-deploys to Render)
- `dev` - Staging/integration (auto-deploys to dev environment)
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

### Production (Render.com)

The application uses a multi-stage Docker build:
1. **Stage 1:** Build React frontend with Vite
2. **Stage 2:** Python backend serves API + static frontend

**Automatic deploys:**
- Push to `main` → Production deployment
- Push to `dev` → Dev environment deployment

**Environment Variables (set in Render dashboard):**
- `DATABASE_URL` - PostgreSQL connection string
- `JWT_SECRET_KEY` - Auto-generated secret for tokens
- `PORT` - Set by Render (default 8000)

**Startup Process:**
1. Docker builds frontend and backend
2. `db_startup.py` detects database type
3. If PostgreSQL: runs Alembic migrations
4. If SQLite: runs init_db() with schema setup
5. Uvicorn starts FastAPI server

### Manual Deploy
```bash
# Trigger redeploy without code changes
git commit --allow-empty -m "Trigger deploy"
git push origin main
```

## Database Management

### SQLite (Local)
```bash
# View database
sqlite3 db/food_cost_tracker.db

# Reset database (deletes all data)
python db/setup_db.py

# Backup database
cp db/food_cost_tracker.db db/food_cost_tracker_backup_$(date +%Y%m%d).db
```

### PostgreSQL (Production)
```bash
# Create new migration
venv/bin/alembic revision --autogenerate -m "Description"

# Run migrations
venv/bin/alembic upgrade head

# Rollback migration
venv/bin/alembic downgrade -1

# View migration history
venv/bin/alembic history
```

## Development Tips

### Debugging
- Backend logs: Check Render dashboard or local terminal
- Frontend errors: Browser console (F12)
- Database queries: Use `/docs` to test API endpoints
- SQLite browser: Use TablePlus, DB Browser, or sqlite3 CLI

### Common Issues

**"No module named 'api'"**
- Ensure you're running from correct directory
- Check virtual environment is activated

**CORS errors in frontend**
- Backend must be running on port 8000
- Check CORS middleware in `api/app/main.py`

**Database locked (SQLite)**
- Close all connections to database
- Ensure only one backend instance running

**Products not showing prices**
- Check product is mapped to common_product
- Verify price_history has recent entries
- Use "Refresh Costs" button in recipe view

## Roadmap

### Completed ✅
- Multi-distributor import system
- Product-to-common-product mapping
- Recipe builder with folders
- Live cost calculation with yield %
- Allergen auto-aggregation
- User authentication & roles
- PostgreSQL migration
- Dev/staging environment

### In Progress 🚧
- AI Recipe Parser (Claude API integration)
  - Upload Word/PDF documents
  - Auto-extract ingredients
  - Smart common product matching

### Planned 📋
- Historical price charts
- Recipe scaling calculator
- PDF export for recipe cards
- Team sharing & collaboration
- Tier system (Free tier: 1 distributor, 5 recipes)
- Mobile-responsive improvements

### Future Modules 🔮
- Labor scheduling & management
- Daily P&L tracking (revenue vs spend)
- HACCP compliance & allergen labeling
- Menu engineering & analysis
- Inventory management

## Contributing

This is a personal project, but suggestions and bug reports are welcome!

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

Proprietary - All Rights Reserved

## Support

For issues or questions, please open a GitHub issue or contact via the repository.

---

**Built with ❤️ by an operator, for operators**
