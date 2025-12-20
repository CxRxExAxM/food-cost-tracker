# Food Cost Tracker - RestauranTek Platform

A comprehensive multi-tenant SaaS platform for F&B operations to manage food costs, track distributor prices, and calculate recipe costs with real-time pricing updates.

**Live Production:** https://www.restaurantek.io
**Dev Environment:** https://food-cost-tracker-dev.onrender.com

---

## Current Status (December 2024)

**Food Cost Tracking MVP:** ✅ **COMPLETE** + Enhanced Recipe Editor

All core features implemented and production-ready:
- ✅ Multi-tenancy & organization management
- ✅ Multi-outlet support with data isolation
- ✅ Outlet-level user access control
- ✅ Super admin management suite
- ✅ Audit logging and compliance tracking
- ✅ Recipe costing with real-time price updates
- ✅ Multi-distributor price tracking
- 🔥 **NEW:** Excel-like recipe ingredient editing with autocomplete

**Latest Update (Dec 18, 2024):** Recipe editor overhaul with inline editing, keyboard navigation, and autocomplete product mapping. See [CHANGELOG.md](CHANGELOG.md) for details.

**Next Steps:** See [FUTURE_PLANS.md](FUTURE_PLANS.md) for post-MVP roadmap (HACCP module, AI recipe parser, advanced features).

---

## Quick Links

- **📝 Changelog:** [CHANGELOG.md](CHANGELOG.md) - Recent updates and release notes
- **📖 Future Roadmap:** [FUTURE_PLANS.md](FUTURE_PLANS.md) - Multi-module platform architecture, HACCP plans
- **🎨 Design Guidelines:** [DESIGN_SYSTEM.md](DESIGN_SYSTEM.md) - UI/UX patterns and styling
- **💻 Developer Guide:** [DEVELOPMENT.md](DEVELOPMENT.md) - Local setup, git workflow, deployment
- **🤖 Claude Instructions:** [CLAUDE_INSTRUCTIONS.md](CLAUDE_INSTRUCTIONS.md) - Guidelines for AI-assisted development
- **📋 Completed Phases:** [docs/completed/](docs/completed/) - Historical phase documentation
- **📚 API Documentation:** https://food-cost-tracker-dev.onrender.com/docs

---

## Core Features

### Multi-Tenant SaaS Platform ✅

**Organizations & Subscriptions**
- Multi-tenant architecture with complete data isolation
- Subscription tiers: Free, Basic, Pro, Enterprise
- Organization-specific settings and branding
- Tier-based limits (users, recipes, outlets)

**User Management**
- Role-based access control (Admin, Chef, Viewer)
- JWT authentication with secure password hashing
- User activation/deactivation
- Password reset functionality

**Multi-Outlet Support** 🔥
- Multiple locations per organization (restaurants, hotels, franchises)
- Outlet-specific products, recipes, and pricing
- Same recipe costs differently at each outlet
- Outlet-level user access control (admins see all, others see assigned outlets only)
- Perfect for hotel groups, multi-location operators, franchises

### Food Cost Tracking ✅

**Product & Price Management**
- Multi-distributor support (Sysco, Vesta, SM Seafood, Shamrock, Noble Bread, Sterling)
- Automated CSV/Excel import with vendor-specific cleaning
- Historical price tracking with trend analysis
- Product-to-common-product mapping for consistency
- Catch weight support for variable-weight items

**Recipe Management** 🔥 *NEW: Excel-like Editing*
- **Inline editing** - Click any cell to edit directly in table
- **Autocomplete product search** - Type to find and map products instantly
- **Keyboard navigation** - Tab, Enter, Escape for rapid data entry
- **Visual mapping indicators** - ✓/× shows ingredient mapping status
- Folder/category organization with nested structure
- Live cost calculation with automatic price updates
- Yield percentage support for prep waste calculation
- Sub-recipe support (recipes within recipes)
- Cost breakdown per ingredient with percentages
- "Refresh Costs" button for instant price updates

**Allergen & Dietary Tracking**
- 16 allergen flags per ingredient (Vegan, Vegetarian, Gluten, Dairy, etc.)
- Auto-aggregation from recipe ingredients
- Compliance-ready allergen reporting

### Super Admin Platform ✅

**Organization Management**
- Platform-wide dashboard with statistics
- Create and manage organizations
- Subscription tier management
- Organization suspend/activate
- Full visibility into all organizations

**User Administration**
- Cross-organization user management
- Edit user details, roles, passwords
- Activate/deactivate users
- Create users for any organization
- Outlet assignment management

**Audit & Compliance**
- Comprehensive audit logging system
- Track subscription changes
- Monitor impersonation sessions
- IP address tracking
- Before/after change tracking

**Organization Impersonation**
- Super admin can impersonate any organization
- Test features as customer
- Debug issues in customer accounts
- Provide hands-on support
- All actions tagged as impersonation in audit logs

---

## Tech Stack

### Backend
- **Framework:** FastAPI 0.104+ (Python 3.12+)
- **Database:** PostgreSQL 16+ (Render PostgreSQL)
- **Authentication:** JWT tokens with bcrypt
- **Migrations:** Alembic
- **File Processing:** pandas, openpyxl for CSV/Excel imports

### Frontend
- **Framework:** React 18 + Vite
- **Routing:** React Router v6
- **HTTP Client:** Axios with JWT interceptors
- **State Management:** React Context API
- **Styling:** Custom CSS with responsive design

### Deployment
- **Platform:** Render.com
- **Environments:** Production (main), Development (dev)
- **Build:** Multi-stage Docker (frontend + backend combined)
- **Migrations:** Auto-run on deploy

---

## Getting Started

### Quick Start (Local Development)

**Prerequisites:**
- Python 3.12+
- Node.js 20+
- PostgreSQL 16+ (local or Render)

**Setup:**

```bash
# 1. Clone repository
git clone https://github.com/CxRxExAxM/food-cost-tracker.git
cd food-cost-tracker

# 2. Set up PostgreSQL
createdb food_cost_tracker_local
export DATABASE_URL="postgresql://localhost/food_cost_tracker_local"

# 3. Set up Python backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
venv/bin/alembic upgrade head

# 4. Start backend (port 8000)
cd api
../venv/bin/uvicorn app.main:app --reload

# 5. Set up frontend (new terminal)
cd frontend
npm install
npm run dev

# 6. Open browser
# Navigate to http://localhost:5173
# Click "Initial Setup" to create admin account
```

**See [DEVELOPMENT.md](DEVELOPMENT.md) for detailed setup instructions, git workflow, and deployment guide.**

---

## Project Structure

```
Clean_Invoices/
├── api/                           # FastAPI backend
│   ├── app/
│   │   ├── routers/              # API endpoints
│   │   │   ├── auth.py           # Authentication & users
│   │   │   ├── products.py       # Product management
│   │   │   ├── recipes.py        # Recipe management
│   │   │   ├── outlets.py        # Outlet management
│   │   │   ├── super_admin.py    # Super admin features
│   │   │   └── uploads.py        # CSV import
│   │   ├── database.py           # PostgreSQL connection
│   │   ├── audit.py              # Audit logging utilities
│   │   └── main.py               # FastAPI app
│   └── ...
├── frontend/                      # React + Vite frontend
│   ├── src/
│   │   ├── pages/                # Page components
│   │   │   ├── Products.jsx
│   │   │   ├── Recipes.jsx
│   │   │   ├── Outlets.jsx
│   │   │   └── SuperAdmin/       # Super admin pages
│   │   ├── components/           # Reusable components
│   │   ├── contexts/             # React contexts
│   │   │   ├── AuthContext.jsx
│   │   │   └── OutletContext.jsx
│   │   └── App.jsx
│   └── ...
├── alembic/                       # Database migrations
├── docs/                          # Documentation
│   ├── archive/                  # Historical planning docs
│   ├── completed/                # Completed phase docs
│   └── recipes/                  # Recipe module docs
├── README.md                      # This file
├── FUTURE_PLANS.md               # Post-MVP roadmap
├── DESIGN_SYSTEM.md              # UI/UX guidelines
├── DEVELOPMENT.md                # Developer guide
└── CLAUDE_INSTRUCTIONS.md        # AI development guidelines
```

---

## Database Schema Overview

### Multi-Tenancy Structure

```
organizations (tier, subscription_status, limits)
    ├── users (role, assigned outlets)
    ├── outlets (location, active status)
    │   ├── products (distributor items, prices)
    │   └── recipes (costs vary per outlet)
    └── common_products (shared ingredient library)
```

**Key Relationships:**
- **Organizations** contain users, outlets, and common products
- **Outlets** have specific products and recipes
- **Users** can be org-wide (admin) or outlet-specific (chef/viewer)
- **Common Products** are shared across organization but products/recipes are outlet-specific
- **Price History** is outlet-specific, enabling per-location recipe costing

**Multi-Outlet Benefits:**
- Same recipe costs differently at each location
- Price comparison across outlets
- Data isolation between locations
- Perfect for hotel groups and franchises

---

## Git Workflow

**Current Branch Strategy:**
```
main (production)
  └── dev (development)
      ├── feature/* (short-lived)
      └── fix/* (short-lived)
```

**Development Process:**
```bash
# Create feature branch from dev
git checkout dev
git pull origin dev
git checkout -b feature/your-feature

# Work and commit
git add .
git commit -m "feat: description"

# Push and test in dev environment
git push origin feature/your-feature
git checkout dev
git merge feature/your-feature
git push origin dev  # Auto-deploys to dev.onrender.com

# Deploy to production when ready
git checkout main
git merge dev
git push origin main  # Auto-deploys to production
```

**See [DEVELOPMENT.md](DEVELOPMENT.md) for detailed git workflow and deployment guide.**

---

## Roadmap

### ✅ MVP Complete (December 2024)

**Food Cost Tracking:**
- Multi-distributor price import and tracking
- Recipe builder with live cost calculation
- Allergen and dietary tracking
- Historical price tracking

**Multi-Tenant Platform:**
- Organization management with subscription tiers
- Multi-outlet support with data isolation
- Outlet-level user access control
- Super admin management suite
- Audit logging and compliance tracking

### 📋 Next Phase (Post-MVP)

**See [FUTURE_PLANS.md](FUTURE_PLANS.md) for comprehensive roadmap:**

**High Priority:**
- AI Recipe Parser (Claude API integration)
- Advanced features (recipe scaling, shopping lists, price trend charts)

**Future Modules:**
- HACCP & Temperature Monitoring
- Inventory Management
- Labor Scheduling & Cost Tracking
- Menu Engineering & Profitability

**Platform Evolution:**
- Three-branch workflow (main/staging/dev)
- Feature flag system for module access
- Modular architecture for multi-module platform

---

## Key Competitive Advantages

1. **🔥 Multi-Outlet Support** - True per-location pricing and costing (most competitors fake it)
2. **💰 Real-Time Cost Calculation** - Instant recipe cost updates when prices change
3. **🏢 Multi-Tenant SaaS** - Complete data isolation, tier-based access
4. **📊 Super Admin Platform** - Full platform oversight and customer support tools
5. **🔍 Audit Logging** - Complete compliance trail for all critical actions
6. **👥 Outlet-Level Access Control** - Flexible permissions for multi-location operations

---

## Documentation

- **[FUTURE_PLANS.md](FUTURE_PLANS.md)** - Post-MVP roadmap, multi-module architecture, HACCP plans
- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Local setup, git workflow, deployment, testing
- **[DESIGN_SYSTEM.md](DESIGN_SYSTEM.md)** - UI/UX guidelines, color palette, component patterns
- **[CLAUDE_INSTRUCTIONS.md](CLAUDE_INSTRUCTIONS.md)** - Guidelines for AI-assisted development
- **[docs/completed/](docs/completed/)** - Completed phase documentation
- **[docs/recipes/](docs/recipes/)** - Recipe module implementation details

---

## License

Proprietary - All Rights Reserved

---

**Built by an operator, for operators** 🍽️
