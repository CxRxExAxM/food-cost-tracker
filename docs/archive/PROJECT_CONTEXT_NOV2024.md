# Food Cost Tracker - Project Context & Roadmap

**Last Updated:** November 28, 2024  
**Project Repository:** https://github.com/CxRxExAxM/food-cost-tracker

## Project Overview

Building a multi-tenant SaaS platform for F&B operations to manage food costs, track distributor prices, and calculate recipe costs. Currently hosted on Render (free tier) with plans to expand into a suite of culinary-focused tools.

## Current State

### Tech Stack
- **Backend:** FastAPI + Python
- **Frontend:** React + Vite
- **Database:** SQLite (migrating to PostgreSQL)
- **Hosting:** Render (free tier)
- **Deployment:** Main branch auto-deploys

### Live Features (v1.0)
- User authentication (demo@demo.com / demo1234)
- Multi-distributor price import (Sysco, Vesta implemented)
- Product management with inline editing
- Common product mapping (with autocomplete)
- Recipe builder with folders/categories
- Live cost calculation with yield % support
- Allergen & dietary tracking (auto-aggregated from ingredients)
- Cost breakdown per ingredient with percentages
- "Refresh Costs" button for price updates

### Current Workflow
1. **Import:** User uploads distributor CSV → selects distributor from dropdown → products imported unmapped
2. **Mapping:** User manually maps distributor products to common products (autocomplete helps)
3. **Recipes:** User creates recipes → adds ingredients → system calculates costs from current prices

## Immediate Priorities

### 1. PostgreSQL Migration (Week 1-2)
**Why Now:**
- SQLite doesn't handle concurrent users
- Need multi-tenancy support for SaaS
- Easier to implement before adding more features

**Action Items:**
- Set up PostgreSQL on Render (free tier available)
- Update SQLAlchemy connection string
- Use Alembic for migrations
- Export SQLite data → import to PostgreSQL
- Test thoroughly before deploying

### 2. AI Recipe Parser (Week 3-4)
**MVP Scope - Ingredients Only:**
- Parse Word/PDF recipe files
- Extract: ingredient name, quantity, unit
- Match to common products in DB (show top 3 matches)
- Set yield % to 100% (user adjusts manually)
- User reviews/confirms before import
- Method steps parsing = future enhancement

**Technical Approach:**
- New FastAPI endpoint: `/api/recipes/parse-file`
- Use `python-docx` for Word, `pypdf` for PDF text extraction
- Send extracted text to Claude API (Anthropic)
- Claude returns structured JSON with ingredients
- Backend queries DB for matching common products
- Frontend shows review/confirmation dialog

**File Upload Flow:**
```
Upload Word/PDF → Extract text → Claude API parses → 
Backend suggests matches → User reviews → Import ingredients
```

**AI Matching Logic:**
- If uncertain, show top 3 product matches
- User selects correct match from dropdown
- If no match, user can search all products or create new

**Claude API Prompt Structure:**
```json
{
  "name": "recipe name",
  "yield": {"quantity": 2, "unit": "quart"},
  "servings": {"quantity": 8, "unit": "portions"},
  "ingredients": [
    {
      "name": "cucumber",
      "quantity": 10,
      "unit": "LB",
      "prep_note": "sliced"
    }
  ]
}
```

**Cost Estimate:**
- ~$0.005-$0.02 per recipe parse
- Free tier: 10 parses/month (~$0.20/month max)
- Paid tier: unlimited (even 100/month = $2)

### 3. Dev Environment Setup (Week 1)
**Set up second Render service:**
- Watch `dev` branch for staging environment
- Test features here before promoting to `main`
- Separate PostgreSQL database for dev

## Git Workflow

### Branch Structure
- `main` - production (deployed on Render)
- `dev` - integration/staging branch
- `feature/*` - individual features

### Feature Development Process
```bash
# Start feature
git checkout dev
git checkout -b feature/feature-name

# Work and commit
git add .
git commit -m "feat: description"

# Push and PR
git push origin feature/feature-name
# Create PR: feature → dev
# Test in dev environment
# Merge dev → main when ready
```

### Sequential Feature Plan
1. `feature/postgresql-migration` → dev → main
2. `feature/ai-recipe-parser` → dev → main
3. Future features build on this foundation

## Product Roadmap

### Free Tier (MVP)
- Import 1 distributor (Sysco only)
- Create up to 5 recipes
- AI recipe parser (10 parses/month)
- Session-based or limited account
- View cost analysis
- No data persistence beyond 30 days

### Paid Tier ($15-20/month)
- Multiple distributors
- Unlimited recipes & AI parsing
- Full recipe library with folders
- Historical price tracking
- Cost trend charts
- Recipe scaling calculator
- Export to PDF
- Team sharing (future)

### Future Modules (Separate Tools)
- Scheduling/Labor Management
- P&L Tracking (daily revenue vs. spend for FC% tracking)
- HACCP/Allergen Labeling with thermal printer integration
- Menu Engineering
- Inventory Management

**Strategy:** Each module as standalone tool. Users adopt incrementally. Not a monolithic suite.

## Technical Decisions & Constraints

### Development Environment
- **Primary:** Mac
- **Company:** Microsoft cloud-embedded
- **Constraint:** Tools must be web-based (no terminal installs for coworkers due to security)
- **Current Hosting:** Unraid server for personal projects
- **Future:** Scale to cloud when needed

### Design Philosophy
- User-first (built by operator for operators)
- Simple, not on rails (unlike existing convoluted SaaS)
- Each tool solves one problem well
- Professional but not corporate-stuffy

### Branding (Future)
- Will need logo package (SVG, PNG, favicon)
- Color palette with HEX codes
- Typography (Google Fonts recommended)
- Consider Fiverr for $100-200 professional package

## Key Architectural Patterns

### Product Data Model
```
distributors (Sysco, Vesta, etc.)
    ↓
products (distributor-specific items with SKUs)
    ↓
common_products (user-defined normalized ingredients)
    ↓
recipes → recipe_ingredients (references common_products)
```

**Why this works:**
- Multi-distributor price comparison
- Users control their ingredient library
- Recipes stay consistent even when switching distributors

### Recipe Costing Engine
- Pulls current prices from mapped products
- Applies yield % for prep loss
- Calculates per-ingredient cost + percentage
- Auto-aggregates allergens from ingredients
- "Refresh Costs" updates when prices change

## Questions Answered in Context

**Import Flow:**
- User selects distributor from dropdown
- Backend runs appropriate cleaning script
- Products imported unmapped
- User maps via autocomplete interface

**Common Products:**
- Created manually or during mapping
- Autocomplete suggests similar existing products
- No AI auto-mapping yet (future enhancement)

**Recipe Import MVP:**
- Focus on ingredients + quantities (accurate parsing critical)
- Method steps = future enhancement
- Yield % defaults to 100%
- Show top 3 product matches if AI uncertain
- Start with Word/PDF (not text paste)

## Next Actions

1. **Set up `feature/postgresql-migration` branch**
2. **Configure dev Render environment**
3. **PostgreSQL migration**
4. **Get Anthropic API key** (console.anthropic.com)
5. **Build AI recipe parser**

## Notes for Claude Code

- Check `/mnt/user-data/uploads` for any reference files
- Working directory: `/home/claude`
- Final outputs go to `/mnt/user-data/outputs`
- Read GitHub repo README for current code structure
- Backend uses FastAPI, check `api/` directory
- Frontend uses React, check `frontend/` directory
