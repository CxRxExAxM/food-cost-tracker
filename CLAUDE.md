# Instructions for Claude Code Sessions

**Purpose:** Guidelines to help Claude maintain project consistency across sessions.

---

## Documentation Structure

### Active Documentation (Root Directory)

**Keep only these 4 files in root:**

1. **README.md** - "Start here" guide
   - Current project status
   - Feature list with accurate completion status
   - Quick start guide
   - Links to other documentation

2. **FUTURE_PLANS.md** - Roadmap and architecture
   - Current development priorities
   - Completed vs planned features
   - Multi-module architecture plans
   - Technical debt and enhancements

3. **DESIGN_SYSTEM.md** - UI/UX guidelines
   - Color palette
   - Typography
   - Component patterns
   - Keep as reference, don't modify often

4. **DEVELOPMENT.md** - Developer guide
   - Local setup instructions
   - Git workflow
   - Deployment process
   - Testing guidelines

**Any other .md files in root = needs justification or archival**

### Documentation Archive (`docs/`)

```
docs/
├── archive/        # Historical planning documents
├── completed/      # Completed phase documentation
└── recipes/        # Recipe module specific docs
```

**Rules:**
- Outdated planning docs → `docs/archive/`
- Completed major phases → `docs/completed/`
- Module-specific implementation → `docs/<module>/`

---

## Before Starting a Major Feature

**STOP and document BEFORE writing code when:**
- Adding a new module/page (e.g., new dashboard, new management area)
- Adding 3+ related API endpoints
- Creating new database tables
- Integrating external services (PMS systems, AI APIs, etc.)
- Making architectural changes

**Required steps:**

1. **Create planning doc** `docs/[feature-name]_PLAN.md` with:
   - Problem being solved
   - Proposed solution approach
   - Database schema changes (if any)
   - API endpoints planned
   - UI components/pages needed
   - Dependencies and integrations

2. **Update FUTURE_PLANS.md:**
   - Move feature from "planned" to "in progress"
   - Note approximate start date

3. **THEN begin implementation**

**Why this matters:**
- Forces thinking before coding
- Creates searchable project history
- Prevents documentation debt
- Helps Claude understand context in future sessions
- Makes handoffs and reviews easier

**Exceptions (no planning doc needed):**
- Bug fixes
- Minor UI tweaks
- Small enhancements to existing features
- Refactoring without behavior changes

---

## When Completing a Major Phase

1. **Create completion doc** in `docs/completed/`
   ```
   docs/completed/PHASE#_NAME.md
   ```

2. **Required sections:**
   - Completed date
   - Features implemented
   - Files modified (backend + frontend)
   - Database changes
   - Testing completed

3. **Update README.md:**
   - Move feature from "Upcoming" to "Completed"
   - Update current status section

4. **Update FUTURE_PLANS.md if needed:**
   - Remove completed items
   - Add new insights from implementation

---

## Git Workflow

### Branch Strategy (Current: Two-Branch)

```
main (production)
  └── dev (development)
      ├── feature/* (short-lived)
      └── fix/* (short-lived)
```

**Rules:**
- `main` = production (manual deploys only)
- `dev` = active development (auto-deploys to dev.onrender.com)
- All work happens in feature branches off `dev`
- Merge `dev` → `main` when ready for production

**Future (Three-Branch - When Starting HACCP):**
```
main (production)
  ├── staging (pre-production)
      └── dev (development)
```

See FUTURE_PLANS.md for when/how to implement.

### Commit Message Format

```
<type>: <description>

[optional body]
```

**Types:**
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation only
- `refactor:` - Code restructuring (no functionality change)
- `test:` - Adding tests
- `chore:` - Maintenance (dependencies, etc.)

**Examples:**
```
feat: Add temperature monitoring UI for HACCP module
fix: Correct impersonation to use AuthContext.setToken
docs: Update README with Phase 4 completion status
```

---

## Code Organization

### ⚠️ CRITICAL: Design System Compliance

**BEFORE creating any new component, page, modal, or CSS file:**

1. **READ `DESIGN_SYSTEM.md` FIRST** - This is mandatory, not optional
2. **Use CSS variables ONLY** - Never hardcode colors, spacing, or borders
3. **Reference existing patterns** - Check if similar components exist
4. **Test in dark mode** - All components must work with the dark theme

**CSS Variable Checklist:**
```css
/* Always use these, NEVER hardcoded values */
--bg-primary, --bg-secondary, --bg-tertiary, --bg-elevated
--text-primary, --text-secondary, --text-tertiary
--border-subtle, --border-default, --border-strong
--color-red, --color-yellow, --color-green (+ -dim, -bright)
--space-1 through --space-20
--radius-sm, --radius-md, --radius-lg
```

**If you write hardcoded colors (`#ffffff`, `rgb()`, etc.), it WILL break the theme.**

See `DESIGN_SYSTEM.md` for complete reference.

---

### Frontend Structure

**Current (Good - Don't Change Yet):**
```
frontend/src/
  ├── pages/           # Page components
  ├── components/      # Shared components
  ├── contexts/        # React contexts
  └── lib/             # Utilities
```

**Future (When Starting HACCP):**
```
frontend/src/
  ├── modules/
  │   ├── food-cost/   # Move Products, Recipes here
  │   └── haccp/       # New module
  ├── shared/          # Move Navigation, contexts here
  └── pages/
      ├── Home.jsx     # Module selector
      └── Login.jsx
```

**⚠️ Do NOT restructure until HACCP development starts!**

### Backend Structure

**Current (Good - Don't Change Yet):**
```
api/app/
  ├── routers/         # API endpoints
  ├── database.py
  ├── audit.py
  └── main.py
```

**Future (When Starting HACCP):**
```
api/app/
  ├── routers/
  │   ├── food_cost/   # Move products, recipes
  │   ├── haccp/       # New module
  │   └── shared/      # Auth, users, outlets
  └── ...
```

**⚠️ Do NOT restructure until HACCP development starts!**

---

## Database Migrations

### Creating Migrations

```bash
# Run from project root
alembic revision -m "description"
```

### Migration Naming

Format: `<sequential>_<description>.py`

Examples:
- `001_initial_schema.py`
- `002_add_missing_organization_columns.py`
- `5e7f498e6bd8_add_audit_logs_table.py`

### Running Migrations

**Local:**
```bash
alembic upgrade head
```

**Production (Render):**
- Runs automatically on deploy via Dockerfile.render
- Command: `alembic upgrade head && uvicorn ...`

### Migration Guidelines

1. **Always test locally first**
2. **Make migrations backward compatible when possible**
3. **Document schema changes in migration file docstring**
4. **Never edit merged migrations** - create new ones

---

## Common Patterns

### Feature Flags (Future)

When implementing organization features:

```python
# Backend
from api.app.features import has_feature

if not has_feature(org_id, "haccp"):
    raise HTTPException(403, "HACCP module not enabled")
```

```javascript
// Frontend
const { hasFeature } = useFeatures();

{hasFeature('haccp') && (
  <Link to="/haccp">HACCP Module</Link>
)}
```

**⚠️ Feature flag system doesn't exist yet!**
- Implement when starting HACCP module
- See FUTURE_PLANS.md for design

### Audit Logging

All critical actions should be logged:

```python
from api.app.audit import log_audit, AuditAction, EntityType

log_audit(
    action=AuditAction.SUBSCRIPTION_UPDATED,
    user_id=current_user["id"],
    organization_id=org_id,
    entity_type=EntityType.ORGANIZATION,
    entity_id=org_id,
    changes={"tier": {"from": "free", "to": "basic"}},
    ip_address=request.client.host if request else None
)
```

**Critical actions to log:**
- Subscription changes
- User role changes
- Impersonation start/end
- Organization settings changes
- Outlet assignments

---

## Testing Guidelines

### Manual Testing Checklist

Before marking a phase complete:

1. **Happy path** - Primary user flow works
2. **Edge cases** - Empty states, no data scenarios
3. **Permissions** - Admin vs non-admin access
4. **Multi-tenant** - Test with 2+ organizations
5. **Error handling** - Invalid inputs, network failures

### Key User Flows

Test these regularly:

1. **Organization Admin:**
   - Create outlet
   - Create user
   - Assign user to outlet
   - Upload price list
   - Create recipe

2. **Super Admin:**
   - Create organization
   - Update subscription
   - Impersonate organization
   - View audit logs

3. **Non-Admin User:**
   - Login
   - See only assigned outlets
   - Access restrictions work

---

## Documentation Maintenance

### When to Update README.md

- ✅ Phase completed
- ✅ New major feature deployed
- ✅ Tech stack changes
- ✅ Deployment URLs change
- ❌ Small bug fixes
- ❌ Minor tweaks

### When to Update FUTURE_PLANS.md

- ✅ New module planned
- ✅ Architecture decisions made
- ✅ Roadmap changes
- ❌ Individual feature ideas (use GitHub Issues)
- ❌ Bug tracking

### When to Create Completion Doc

**Create `docs/completed/PHASE#_NAME.md` when:**
- Major feature set complete (3+ related features)
- Database schema changes
- New module/section added
- Significant architectural change

**Don't create for:**
- Bug fixes
- Minor feature additions
- UI tweaks
- Refactoring

---

## Common Mistakes to Avoid

### ❌ Don't Do This:

1. **Use hardcoded colors in CSS** - ALWAYS use CSS variables from DESIGN_SYSTEM.md
2. **Create new .md files in root** without archiving old ones
3. **Restructure code** before HACCP development starts
4. **Force push to main or dev branches**
5. **Implement features without testing multi-tenancy**
6. **Skip audit logging for critical actions**
7. **Modify completed migrations**
8. **Use `localStorage` directly** (use AuthContext.setToken)
9. **Add emojis to code** unless explicitly requested
10. **Create new components without checking DESIGN_SYSTEM.md first**

### ✅ Do This Instead:

1. **Use CSS variables from DESIGN_SYSTEM.md** for all styling
2. **Check DESIGN_SYSTEM.md BEFORE creating components** - every time
3. **Update existing docs** or archive outdated ones
4. **Wait for modular restructure** per FUTURE_PLANS.md
5. **Use normal git workflow** (commits, PRs)
6. **Test with multiple orgs/outlets**
7. **Log all subscription, user, impersonation changes**
8. **Create new migrations** for schema changes
9. **Use React contexts and hooks** for state management
10. **Keep code professional** and clean

---

## Quick Reference

### Important Files

**Configuration:**
- `api/app/database.py` - Database connection
- `api/app/main.py` - FastAPI app setup
- `frontend/src/lib/axios.js` - API client
- `alembic.ini` - Migration config
- `Dockerfile.render` - Deployment config

**Core Contexts:**
- `AuthContext` - User authentication, token management
- `OutletContext` - Current outlet selection

**Key Utilities:**
- `api/app/audit.py` - Audit logging helpers
- `api/app/auth.py` - JWT token handling

### Environment Variables

**Backend:**
- `DATABASE_URL` - PostgreSQL connection
- `JWT_SECRET_KEY` - Token signing (auto-generated on Render)
- `PYTHON_ENV` - "production" on Render

**Frontend:**
- `VITE_API_URL` - Backend URL (empty = relative paths)

### Deployment URLs

- **Production:** https://food-cost-tracker.onrender.com
- **Dev:** https://food-cost-tracker-dev.onrender.com

---

## Natural Language Reporting (Chat Agent)

### Overview
Conversational AI interface for querying potentials, forecasts, and events data using Claude Haiku 4.5.

### Key Components

**Backend (`api/app/services/chat_agent.py`):**
- Tool-based agent using Anthropic SDK
- 7 tools for querying forecast, events, and potentials data
- Session-based conversation history (last 10 messages)
- Returns structured responses: text, html, table, charts

**Frontend (`frontend/src/components/Chat/`):**
- Slide-out panel (800px wide)
- Markdown and HTML rendering support
- Table and chart renderers for structured data
- Message persistence per session

### Agent Tools

1. `get_forecast_summary` - Occupancy, ADR, rooms metrics
2. `get_upcoming_events` - Events/BEOs with filtering
3. `get_event_detail` - Specific event lookup
4. `get_daily_summary` - Combined forecast + events by day
5. `compare_periods` - Period-over-period comparison
6. `get_groups_summary` - Group-level analytics
7. `get_high_aloo_periods` - Large group ALOO identification

### Data Fields Available

**Forecast Metrics:**
- `forecasted_rooms`, `occupancy_pct`, `adr`
- `adults_children` (IHG - In-House Guests)
- `kids` (children count)
- `leisure_guests` (transient_rooms × 2.5) - **Added Mar 2026**
- `arrivals`, `departures`

**Event Data:**
- Catered covers by meal period (breakfast/lunch/dinner/reception)
- Group names, venues, times, attendees
- Notes field (user-added operational context)

### Response Types

**Text (Markdown):**
```python
return {"text": "markdown text", "render_type": "text", "render_data": {}}
```

**HTML (Custom Styling):**
```python
return {"text": "<div>...</div>", "render_type": "html", "render_data": {}}
```

**Table:**
```python
return {
    "text": "Summary text",
    "render_type": "table",
    "render_data": {"columns": [...], "rows": [...]}
}
```

**Charts:**
```python
return {
    "text": "Chart description",
    "render_type": "line_chart" | "bar_chart" | "comparison_bar",
    "render_data": {"labels": [...], "datasets": [...]}
}
```

### HTML Renderer Classes

Pre-styled classes for rich reports:
- `.metric-card` - Display key metrics
- `.report-section` - Styled content blocks
- `.highlight` - Highlighted text
- `.positive` / `.negative` - Color-coded values

### Adding New Tools

1. Define tool schema in `TOOLS` array
2. Add case to `execute_tool()` dispatcher
3. Implement query function (use `build_daily_summary` for consistency)
4. Update tool description to list available fields

### Current Limitations

- Read-only access (no write tools)
- Synchronous execution (Anthropic SDK is sync)
- Session history limited to 10 messages
- Requires `ANTHROPIC_API_KEY` environment variable

### Future Enhancements (Planned)

See Notion: "Phase 2 — Group Resume Ingestion & Automated Daily Briefs"
- Write tools (add notes to events)
- Document ingestion (group resumes)
- Automated daily operational briefs

---

## Potentials Module (F&B Planning Dashboard)

### Overview
Forecasting and event planning dashboard for F&B operations. Integrates with Opera PMS data exports to provide daily operational insights.

### Key Components

**Backend (`api/app/routers/potentials.py`):**
- 20+ endpoints for events, forecasts, and group data
- File import handling (Excel-based forecasts and hit lists)
- Daily summary aggregation

**Frontend (`frontend/src/pages/Potentials/`):**
- `Potentials.jsx` - Main dashboard (~50KB)
- Charts for occupancy, covers, group activity
- Date range navigation
- Event detail views

### Database Tables

```sql
property_events      -- BEOs, hit list items, local events
forecast_metrics     -- Daily occupancy, ADR, rooms, IHG, arrivals
group_rooms          -- Group arrivals/departures by day
import_logs          -- Track file imports and processing
```

### Data Fields

**Forecast Metrics:**
- `forecasted_rooms`, `occupancy_pct`, `adr`
- `adults_children` (IHG - In-House Guests)
- `kids` (children count)
- `leisure_guests` (transient_rooms × 2.5)
- `arrivals`, `departures`

**Events:**
- Catered covers by meal period (breakfast/lunch/dinner/reception)
- Group names, venues, times, attendees
- Notes field for operational context

### Integration Points
- Opera PMS exports (forecast, hit list)
- Feeds into NL Chat Agent for querying

---

## AI Recipe Parser

### Overview
Automates recipe ingredient entry by parsing Word/PDF/Excel documents using Claude API, with semantic matching to existing products.

### Key Components

**Backend:**
- `api/app/routers/ai_parse.py` - Main endpoints
- `api/app/services/recipe_parser.py` - Claude API integration
- `api/app/services/product_matcher.py` - Multi-strategy matching
- `api/app/services/file_processor.py` - Text extraction

**Frontend:**
- `frontend/src/components/RecipeImport/UploadRecipeModal.jsx`
- `frontend/src/components/RecipeImport/ReviewParsedRecipe.jsx`

### Matching Strategies (Priority Order)

1. **Learned** (0.90+) - User previously selected this mapping
2. **Exact** (1.0) - Case-insensitive exact match
3. **Base match** (0.85+) - Core ingredient word matches (handles plurals)
4. **Contains** (0.95+) - Ingredient in product name or vice versa
5. **Fuzzy** (0.95+) - String similarity
6. **Semantic** (0.70+) - pgvector embedding similarity

### Auto-Match Thresholds
- `learned` ≥ 0.90 → auto-select
- `base_match` ≥ 0.85 → auto-select
- `semantic` ≥ 0.70 → auto-select
- Others ≥ 0.95 → auto-select

### Usage Limits
- Free tier: 10 parses/month
- Basic+: 100 parses/month
- Rate limit: 10 uploads/hour per org
- Only successful/partial parses count toward limit

---

## Semantic Search (pgvector)

### Overview
Vector similarity search for ingredient matching using Voyage AI embeddings stored in PostgreSQL with pgvector.

### Configuration
- **Model:** Voyage AI `voyage-3.5-lite`
- **Dimensions:** 1024
- **Index:** IVFFlat with cosine distance
- **Table:** `common_products.embedding` column

### Key Files
- `api/app/utils/embeddings.py` - Voyage API, embedding generation, similarity search
- Migration `023_add_pgvector_embeddings.py` - Schema setup

### Usage
```python
from api.app.utils.embeddings import search_similar_products

results = search_similar_products(
    cursor,
    query_text="cilantro",
    organization_id=org_id,
    limit=5,
    threshold=0.5
)
```

### Environment Variables
- `VOYAGE_API_KEY` - Required for semantic search (falls back to string matching if not set)

---

## Learning Loop (Ingredient Mappings)

### Overview
Records user ingredient→product corrections to improve future AI recipe parsing. Designed for future network effect across tenants.

### Database Table
```sql
ingredient_mappings
  - organization_id    -- Tenant isolation
  - raw_name           -- Normalized parsed text ("cilantro")
  - common_product_id  -- What user selected
  - is_shared          -- Opt-in for network effect (default FALSE)
  - confidence_score   -- Match quality when recorded
  - match_type         -- 'user_selected', 'accepted_suggestion', 'search'
  - use_count          -- Times this mapping applied
```

### Three-Tier Security Model
1. **Tenant-private:** Pricing, volumes (never shared)
2. **Anonymized shared:** Ingredient mappings (opt-in via `is_shared`)
3. **Fully public:** Taxonomy, unit normalizations

### Key Files
- `api/app/services/ingredient_mapper.py` - Record/retrieve mappings
- Migration `024_add_ingredient_mappings.py` - Schema

### How It Works
1. User parses recipe with "cilantro"
2. No match found, user searches and selects "Herb, Cilantro"
3. Mapping recorded: `cilantro → Herb, Cilantro`
4. Next recipe with "cilantro" → auto-matches with "🧠 Remembered" badge

---

## Questions to Ask User

Before making significant changes, confirm:

1. **Major feature?** "This looks like a new module/feature. Should I create a planning doc in `docs/` first per the documentation guidelines?"

2. **New documentation?** "Should I create a new .md file or add to existing documentation?"

3. **Breaking changes?** "This change affects existing functionality. How should we handle backward compatibility?"

4. **Architecture decision?** "This involves a significant technical choice. Want me to document the options and tradeoffs first?"

---

## Session Handoff

At the end of each session, provide:

1. **Summary of work completed**
2. **Files modified** (with line references if significant)
3. **Commits made** (with commit hashes)
4. **Next recommended steps**
5. **Any blockers or questions**

**Format:**
```
## Session Summary

**Work Completed:**
- Fixed impersonation banner (Navigation.jsx:60-77 removed)
- Updated audit logging (audit.py:61 - use bool() not int)

**Commits:**
- 8752bbd - fix: Remove duplicate impersonation banner
- 66e4922 - fix: Use boolean type for audit logs

**Next Steps:**
1. Wait for Render deploy
2. Test impersonation workflow
3. Verify audit logs populating

**Status:** ✅ Ready for testing
```

---

## Project Philosophy

### Keep It Simple
- Minimal .md files in root
- Don't over-engineer for future needs
- Use existing patterns before creating new ones

### Multi-Tenant First
- Every feature must work with multiple organizations
- Test with 2+ orgs and outlets
- Data isolation is critical

### Document Major Changes Only
- Completion docs for phases, not individual features
- README stays current, not exhaustive
- FUTURE_PLANS.md for strategic decisions

### Professional Code
- No emojis in code
- Clear variable names
- Comments explain "why" not "what"
- Follow existing patterns

---

**Last Updated:** March 26, 2026
**Next Review:** After next major feature completion
