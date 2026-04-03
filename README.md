# Food Cost Tracker - RestauranTek Platform

A comprehensive multi-tenant SaaS platform for F&B operations to manage food costs, track distributor prices, calculate recipe costs, and plan daily operations with real-time forecasting.

**Live Production:** https://www.restaurantek.io
**Dev Environment:** https://food-cost-tracker-dev.onrender.com

---

## Current Status (April 2026)

**Platform Status:** Production-ready with active development

### Completed Modules

**EHC (Environmental Health Compliance)** - ✅ Complete
- Annual audit cycle management with 6-section hierarchy
- Three-level readiness tracking: Pre-Work, Internal Walk, Audit Walk
- Record management with submission tracking and file uploads
- Due date status indicators (Approved/Due/Past Due/Pending)
- Stacked progress bars showing readiness across sections and NC levels
- Internal verification checkbox for pre-audit practice walks
- Record linking for observational audit points
- **Digital Forms** - Tokenized public signature collection:
  - QR code generation for tablet/phone signing
  - Staff declarations (Record 11) with scroll-to-sign gate
  - Team roster signing (Record 35)
  - Duplicate detection with force override
  - Response tracking with signature previews

**Food Cost Tracking** - ✅ Complete
- Multi-distributor price tracking with automated imports
- Recipe costing with real-time price updates
- Allergen and dietary tracking (16 flags)
- Sub-recipe support
- Banquet menu management with PDF export

**AI Recipe Parser** - ✅ Complete
- Parse Word/PDF/Excel recipe documents
- Claude API-powered ingredient extraction
- Multi-strategy product matching (learned, exact, fuzzy, semantic)
- Learning loop for user corrections

**Potentials Module (F&B Planning)** - ✅ Complete
- Opera PMS integration (forecasts, hit lists)
- Daily occupancy, covers, and group tracking
- Event and BEO management
- Visual dashboards with charts

**Natural Language Chat Agent** - ✅ Complete
- Conversational queries for forecast data
- Claude Haiku-powered tool-based agent
- Supports tables, charts, and rich HTML responses

**Infrastructure:**
- ✅ Multi-tenancy with complete data isolation
- ✅ Multi-outlet support with per-location pricing
- ✅ Role-based access control
- ✅ Super admin management suite
- ✅ Audit logging and compliance tracking
- ✅ Semantic search with pgvector embeddings

---

## Quick Links

- **Changelog:** [CHANGELOG.md](CHANGELOG.md) - Recent updates
- **Future Roadmap:** [FUTURE_PLANS.md](FUTURE_PLANS.md) - Development priorities
- **Design Guidelines:** [DESIGN_SYSTEM.md](DESIGN_SYSTEM.md) - UI/UX patterns
- **Developer Guide:** [DEVELOPMENT.md](DEVELOPMENT.md) - Local setup, deployment
- **Claude Instructions:** [CLAUDE.md](CLAUDE.md) - AI development guidelines
- **API Documentation:** https://food-cost-tracker-dev.onrender.com/docs

---

## Core Features

### AI Recipe Parser

**Automated ingredient extraction:**
- Upload Word, PDF, or Excel recipe documents
- Claude API extracts ingredients, quantities, units
- Multi-strategy product matching:
  1. **Learned** - User's previous selections (highest priority)
  2. **Exact** - Case-insensitive name match
  3. **Base match** - Core ingredient word matching
  4. **Contains** - Partial name matching
  5. **Fuzzy** - String similarity
  6. **Semantic** - pgvector embedding similarity (Voyage AI)
- User reviews and confirms before import
- Corrections recorded for future parses (learning loop)

**Usage limits:**
- Free tier: 10 parses/month
- Basic+: 100 parses/month

### Potentials Module (F&B Planning Dashboard)

**Daily operations forecasting:**
- Import Opera PMS forecasts and hit lists
- Track occupancy, ADR, arrivals/departures
- Monitor group rooms and ALOO
- Event calendar with catered covers
- Visual charts for occupancy and covers trends

**Data fields:**
- In-House Guests (adults + children)
- Leisure guests calculation (transient × 2.5)
- Breakfast/lunch/dinner/reception covers
- Group-level analytics

### Natural Language Chat Agent

**Conversational data queries:**
- "What's the occupancy for next week?"
- "Show me all events with over 100 covers"
- "Compare this month to last month"

**Response formats:**
- Markdown text
- Rich HTML with styled reports
- Data tables
- Line/bar charts

### Food Cost Tracking

**Product & Price Management:**
- Multi-distributor support (Sysco, Vesta, SM Seafood, Shamrock, etc.)
- Automated CSV/Excel import with vendor-specific cleaning
- Historical price tracking
- Catch weight support

**Recipe Management:**
- Inline editing with autocomplete
- Live cost calculation
- Yield percentage for prep waste
- Sub-recipe support
- Cost breakdown with percentages
- Allergen aggregation

### Multi-Tenant Platform

**Organizations & Subscriptions:**
- Complete data isolation
- Tier-based limits (users, recipes, AI parses)
- Organization-specific settings

**Multi-Outlet Support:**
- Per-location products and pricing
- Same recipe costs differently at each outlet
- Outlet-level user access control

**Super Admin Platform:**
- Organization management
- Subscription tier control
- Impersonation for support
- Audit logging

---

## Tech Stack

### Backend
- **Framework:** FastAPI (Python 3.12+)
- **Database:** PostgreSQL 16+ with pgvector extension
- **AI:** Claude API (Anthropic), Voyage AI (embeddings)
- **Migrations:** Alembic (auto-runs on deploy)

### Frontend
- **Framework:** React 19 + Vite 7
- **Routing:** React Router v7
- **HTTP Client:** Axios with JWT interceptors
- **State:** React Context API

### Deployment
- **Platform:** Render.com
- **Build:** Multi-stage Docker (frontend + backend)
- **Environments:** Production (main), Development (dev)

---

## Getting Started

### Quick Start (Local Development)

**Prerequisites:**
- Python 3.12+
- Node.js 20+
- PostgreSQL 16+ with pgvector extension

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

**Environment Variables:**
- `DATABASE_URL` - PostgreSQL connection string
- `ANTHROPIC_API_KEY` - For AI recipe parser
- `VOYAGE_API_KEY` - For semantic search (optional)

See [DEVELOPMENT.md](DEVELOPMENT.md) for detailed setup.

---

## Project Structure

```
Clean_Invoices/
├── api/                           # FastAPI backend
│   ├── app/
│   │   ├── routers/              # API endpoints
│   │   │   ├── ehc.py            # Environmental Health Compliance
│   │   │   ├── ai_parse.py       # AI recipe parser
│   │   │   ├── potentials.py     # F&B planning dashboard
│   │   │   ├── recipes.py        # Recipe management
│   │   │   ├── products.py       # Product management
│   │   │   └── ...
│   │   ├── services/             # Business logic
│   │   │   ├── chat_agent.py     # NL chat agent
│   │   │   ├── recipe_parser.py  # Claude API integration
│   │   │   ├── product_matcher.py # Multi-strategy matching
│   │   │   ├── ingredient_mapper.py # Learning loop
│   │   │   └── ...
│   │   ├── utils/
│   │   │   └── embeddings.py     # Voyage AI / pgvector
│   │   └── ...
├── frontend/                      # React + Vite frontend
│   ├── src/
│   │   ├── pages/
│   │   │   ├── EHC/              # Environmental Health Compliance
│   │   │   ├── Potentials/       # F&B planning dashboard
│   │   │   └── ...
│   │   ├── components/
│   │   │   ├── Chat/             # NL chat interface
│   │   │   ├── RecipeImport/     # AI parser UI
│   │   │   └── ...
│   │   └── ...
├── alembic/                       # Database migrations
├── docs/                          # Documentation
└── ...
```

---

## Database Schema

### Key Tables

**Core:**
- `organizations` - Tenants with subscription tiers
- `users` - Role-based access control
- `outlets` - Multi-location support

**Food Cost:**
- `recipes`, `recipe_ingredients`
- `products`, `common_products`
- `price_history`

**AI & Search:**
- `common_products.embedding` - pgvector for semantic search
- `ingredient_mappings` - Learning loop storage
- `ai_parse_history` - Parse tracking and limits

**Potentials:**
- `property_events` - BEOs, hit list items
- `forecast_metrics` - Daily occupancy, ADR, IHG
- `group_rooms` - Group arrivals/departures

**EHC (Environmental Health Compliance):**
- `ehc_audit_cycle` - Annual audit cycles
- `ehc_section`, `ehc_subsection`, `ehc_audit_point` - Audit hierarchy
- `ehc_record`, `ehc_record_submission` - Record tracking
- `ehc_point_record_link` - Links records to audit points
- `ehc_form_link` - Tokenized public form links with QR codes
- `ehc_form_response` - Signatures with audit trail (IP, user agent)

---

## Development Roadmap

### Current Priorities
- EHC Module Restructure (Forms tab, Settings tab, outlet management)
- EHC PDF Export (completed signature sheets)
- AI Recipe Parser enhancements (method step parsing)
- Potentials Phase 2 (group resume ingestion)

### Future Considerations
- EHC Monthly Outlet Checks (automated email distribution)
- HACCP & Temperature Monitoring
- Inventory Management
- Labor Scheduling

See [FUTURE_PLANS.md](FUTURE_PLANS.md) for detailed roadmap.

---

## License

Proprietary - All Rights Reserved

---

**Built by an operator, for operators**
