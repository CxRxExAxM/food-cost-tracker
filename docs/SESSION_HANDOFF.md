# Session Handoff

**Date:** 2026-06-28
**Status:** Recipe import unblocked & hardened; ready to plan parser refinement next session

---

## Next Session Starts Here

**The user will add a recipe-parser planning doc to `/docs`.** Start by reading it and reconciling it against:
- `docs/TAXONOMY_GUIDED_MAPPING_PLAN_v2.md` (the taxonomy prerequisite — Steps 1-3 done, 4-7 remain)
- The current AI parser state (below) and `FUTURE_PLANS.md` section 2

Key framing: AI parse *extraction* is solid; ingredient→common-product *matching* is the weak point, and it's gated on taxonomy cleanup. Concrete evidence: a real `.doc` parse matched 0 of 6 ingredients.

---

## This Session's Work (all committed to main & deployed)

- **Legacy `.doc` support** in the recipe parser via `antiword` (system pkg in both Dockerfiles). Verified in prod (Guacamole.doc extracted 6 ingredients). Commit `4b54d35`.
- **Recipe save fix:** parsed recipes with unquantified ingredients ("to taste") were 422'ing on save (`quantity`/`unit_id` were required); now optional, null quantity → 0. Also fixed a React #31 crash from rendering FastAPI 422 detail (array of objects) in a toast. Commit `364ea14`.
- **Vendor creation:** `POST /api/distributors` + "Add new vendor" UI + seeded "Internal / Housemade" vendor (migration 047). Unblocks creating priced products before invoices arrive. Commit `d9c9fb3`.
- **Search performance:** debounced all-products search + moved reference data to mount-only load (~28 requests → ~1 while typing); same debounce on super-admin org search. Commits `ce34666`, `36a9e86`.
- **Infra:** Render Postgres upgraded Basic-256mb (0.1 CPU) → Basic-1gb (0.5 CPU); fixed query latency variance (CPU starvation, not indexes).

## Current AI Recipe Parser State

- **Extraction:** `.docx`, `.doc`, `.pdf`, `.xlsx` all supported (`api/app/services/file_processor.py`).
- **Save:** `POST /recipes/create-from-parse` works for drafts with partial/unmatched ingredients.
- **Matching:** multi-strategy (learned → exact → base → contains → fuzzy → semantic) in `product_matcher.py`. Quality limited by messy `common_products` — the taxonomy work is the unlock.
- **Audit trail:** `ai_parse_usage` table logs every parse (filename, status, ingredients_count, matched_count, recipe_id). A row with `recipe_id = NULL` = parsed but never saved.

## Taxonomy-Guided Mapping (prerequisite) — where it stands

Steps 1-3 complete (endpoints + `PathBasedProductMapper.jsx`, per prior handoff). Remaining: Step 4 (trial guided flow), 4.5 (duplicate-analysis on common_products), 5-7 (archive → remap products → re-link recipes), plus parallel yield-% population. Full plan: `docs/TAXONOMY_GUIDED_MAPPING_PLAN_v2.md`.

## Key Files

- `api/app/services/file_processor.py` — text extraction (incl. new `extract_from_doc`)
- `api/app/routers/ai_parse.py` — parse + `create-from-parse` endpoints
- `api/app/services/product_matcher.py` — ingredient matching pipeline
- `frontend/src/components/RecipeImport/` — UploadRecipeModal, ReviewParsedRecipe
- `api/app/routers/taxonomy.py` + `frontend/src/pages/Products/PathBasedProductMapper.jsx` — guided mapping
