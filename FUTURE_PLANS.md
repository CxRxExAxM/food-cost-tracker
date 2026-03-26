# Future Plans: RestauranTek Platform

**Date:** March 26, 2026
**Status:** Active Development
**Timeline:** Ongoing

---

## Overview

This document outlines the technical roadmap for RestauranTek, covering both near-term enhancements and long-term platform evolution.

**Current Focus:**
1. Enhance AI Recipe Parser with method step parsing
2. Potentials Phase 2 - Group resume ingestion and daily briefs
3. Database refactor - Ingredient taxonomy and attribute-based schema

---

## Recently Completed (Reference)

### AI Recipe Parser ✅
- Word/PDF/Excel parsing with Claude API
- Multi-strategy product matching (learned → exact → base → contains → fuzzy → semantic)
- Learning loop for user corrections
- Usage limits per subscription tier

### Potentials Module ✅
- Opera PMS integration (forecasts, hit lists)
- Daily operations dashboard
- Event/BEO management
- NL Chat Agent for querying data

### Semantic Search ✅
- pgvector embeddings (Voyage AI voyage-3.5-lite)
- 1024-dimension vectors with IVFFlat index
- Integrated into product matching pipeline

---

## Near-Term Priorities

### 1. AI Recipe Parser Enhancements

**Method Step Parsing (Next):**
- Extract cooking instructions from documents
- Parse into numbered steps
- Link ingredients mentioned in steps
- Store in `recipes.method` JSON field

**Better Unit Handling:**
- Expand unit normalization rules
- Handle fractional quantities ("1/2 cup")
- Support recipe-specific unit preferences

### 2. Potentials Phase 2: Group Intelligence

**Group Resume Ingestion:**
- Upload group resume PDFs
- Extract: VIP preferences, dietary requirements, special requests
- Link to upcoming events
- Surface in daily briefs

**Automated Daily Briefs:**
- Morning operational summary
- Highlight key events and groups
- Flag potential issues (large groups, dietary concerns)
- Deliver via chat or email

**Agent Write Tools:**
- Add notes to events
- Update operational flags
- Create action items

### 3. Database Refactor: Ingredient Taxonomy

**Three-Phase Plan (See Notion for full design):**

**Phase 1 - Preparation:**
- Create `base_ingredients` table (tomato, chicken, etc.)
- Create `ingredient_variants` table (cherry tomato, roma tomato)
- Map existing `common_products` to base ingredients

**Phase 2 - Migration:**
- Update recipe ingredients to reference variants
- Migrate learned mappings
- Preserve existing cost relationships

**Phase 3 - Features:**
- Attribute-based search (find all "dairy" items)
- Substitution suggestions
- Cross-recipe ingredient analysis

**Three-Tier Security Model:**
1. **Tenant-private:** Pricing, volumes, costs (never shared)
2. **Anonymized shared:** Ingredient mappings (opt-in network effect)
3. **Fully public:** Base taxonomy, unit normalizations

---

## Medium-Term Enhancements

### Food Cost Module

**Recipe Features:**
- [ ] Recipe scaling (adjust quantities)
- [ ] Shopping list generation
- [ ] Price trend charts per recipe
- [ ] Recipe history/versioning
- [ ] Print/export recipe cards (PDF)
- [ ] Recipe search (by ingredients, allergens)

**Product Features:**
- [ ] Manual product entry form
- [ ] Price history charts
- [ ] Product merge/deduplication tool
- [ ] Bulk editing

**Tech Debt:**
- [ ] Move virtual folders from localStorage to database
- [ ] Improve error handling with user feedback
- [ ] Add comprehensive test coverage
- [ ] Optimize tree rendering for large datasets

### Potentials Module

**Advanced Analytics:**
- [ ] Forecast accuracy tracking
- [ ] Historical comparison reports
- [ ] Occupancy vs actual revenue correlation
- [ ] Labor cost integration

**Integrations:**
- [ ] Additional PMS systems (beyond Opera)
- [ ] Reservation system connections
- [ ] Weather data correlation

---

## Long-Term Platform Evolution

### Multi-Module Architecture

When adding significant new modules, implement:

**Three-Branch Workflow:**
```
main (production)
  ├── staging (pre-production testing)
      └── dev (active development)
```

**Feature Flag System:**
```python
# Backend
if not has_feature(org_id, "new_module"):
    raise HTTPException(403, "Module not enabled")

# Frontend
{hasFeature('new_module') && <NewModuleNav />}
```

**Modular Code Organization:**
```
frontend/src/modules/
  ├── food-cost/
  ├── potentials/
  └── [future-modules]/

api/app/routers/
  ├── food_cost/
  ├── potentials/
  └── [future-modules]/
```

### Potential Future Modules

**HACCP & Temperature Monitoring:**
- Temperature logging with alerts
- Checklist management
- Corrective action tracking
- Compliance reporting

**Inventory Management:**
- Par level tracking
- Inventory counts
- Waste logging
- Automated ordering suggestions

**Labor Management:**
- Schedule creation
- Time tracking integration
- Labor cost analysis
- Coverage optimization

**Menu Engineering:**
- Item profitability analysis
- Menu mix optimization
- Pricing recommendations
- Seasonal menu planning

---

## Technical Considerations

### Database Scaling

**Current Setup:**
- PostgreSQL 16 on Render
- pgvector for embeddings
- Alembic migrations (auto-run on deploy)

**Future Considerations:**
- Read replicas for analytics queries
- Separate analytics database
- Time-series storage for metrics

### API Performance

**Current:**
- Synchronous FastAPI endpoints
- Direct database queries

**Future Considerations:**
- Background task processing (Celery/Redis)
- Query caching for common patterns
- API rate limiting improvements

### AI/ML Enhancements

**Current:**
- Claude API for parsing
- Voyage AI for embeddings

**Future Considerations:**
- Fine-tuned models for F&B domain
- Local embedding generation (cost reduction)
- Automated training from user corrections

---

## Decision Log

### Q1 2026 Decisions

**Learning Loop Implementation (Mar 2026):**
- Decision: Store user corrections in `ingredient_mappings` table
- Rationale: Enables future network effect without schema change
- Impact: 95%+ confidence for learned matches

**Semantic Search with Voyage AI (Feb 2026):**
- Decision: Use voyage-3.5-lite (1024 dims) over OpenAI embeddings
- Rationale: Better cost/performance ratio, lower latency
- Impact: ~$0.001 per query, sub-100ms search

---

## Action Items

### This Month
- [ ] Method step parsing for AI parser
- [ ] Group resume ingestion planning
- [ ] Ingredient taxonomy design review

### Next Quarter
- [ ] Potentials Phase 2 implementation
- [ ] Database refactor Phase 1
- [ ] Recipe scaling feature

### This Year
- [ ] Complete database refactor
- [ ] Evaluate HACCP module demand
- [ ] Three-branch workflow (if needed)

---

**Document Version:** 2.0
**Last Updated:** March 26, 2026
**Next Review:** After Potentials Phase 2 completion
