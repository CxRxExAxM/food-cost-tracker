# Taxonomy Guided Mapping — Build Plan (v2)

**Status:** Planning → Ready to build
**Priority:** High — blocks trustworthy menu costing, blocks adding more people to product mapping
**Supersedes:** `docs/archive/TAXONOMY_GUIDED_MAPPING_PLAN.md` (March 26, 2026)
**Updated:** June 2026

---

## Why this doc exists

The original guided-mapping plan was written and immediately archived in a docs cleanup without ever being built. The schema and routers it was designed against (`taxonomy.py`, `TaxonomyView.jsx`, migration 025) have not changed since. This version keeps the original design, closes out the open questions, and adds the recipe re-link step that was missing from v1.

**Directive driving this:** menu costs need to be real and defensible before onboarding additional people into product mapping. Every person who creates a Common Product through the current freeform input multiplies the duplicate problem. Fix the creation flow before adding hands.

---

## Problem (unchanged from v1)

1. **Hierarchy is cosmetic only.** The variant tree (`parent_variant_id`) is visual organization. It does not affect how SKUs get matched to Common Products — that's still exact attribute matching, disconnected from what you see in the tree.
2. **No guided onboarding.** The current mapping input (Products page, "Type to search or create...") is freeform text. Nothing stops duplicate or inconsistent Common Products from being created.
3. **Retroactive cleanup is painful.** Renaming/moving items doesn't reliably change their underlying assignment — confirmed firsthand ("I've been working on Chicken now for 10 minutes...").
4. **Variable depth.** Chicken needs 5 levels (Breast → Airline → 8oz → Frenched → IQF); Onion needs 2 (Yellow). The UI has to handle both without forcing depth.

---

## Decisions (resolves v1's open questions)

| Question | Decision | Why |
|---|---|---|
| Delimiter | **Comma** | Already your own naming convention — zero retraining |
| Fresh/Frozen handling | **Variant-level, via existing `state` column** | Schema already has this on `ingredient_variants` — no new design needed |
| Keep the auto-parser? | **Yes — as a suggestion only** | Pre-fills a guessed path from raw vendor text; user still confirms via guided flow |
| Attribute preservation | **Implicit via path position** | Each step down the path is a real variant row with real attribute columns — no separate free-text parsing required |
| Migration strategy | **Clean slate on the *mapping layer only*** | See scope note below — this is not a full data wipe |

---

## Gotchas Claude Code needs to know up front

These are concrete issues found by reviewing the current `taxonomy.py` router, `schemas.py`, and migrations. Each one will trip up implementation if not handled deliberately.

1. **`parent_variant_id` is not in the create flow.** Migration 026 added the column to `ingredient_variants`, but `IngredientVariantBase` in `schemas.py` does not include it, and `POST /variants` does not insert it — nesting only happens via the separate `PATCH /variants/{id}/move` endpoint. The new `create-in-path` endpoint must either: (a) wrap create + move in one transaction internally, or (b) extend `IngredientVariantBase`/Create and the INSERT to accept `parent_variant_id` directly. Option (b) is cleaner; do that and adjust the existing `/variants` endpoint at the same time.

2. **Taxonomy tables are GLOBAL, not org-scoped.** `base_ingredients` and `ingredient_variants` have no `organization_id` column — only `common_products` and `ingredient_mappings` do. This is intentional (see Notion: "Architecture Notes — Ingredient Taxonomy & Data Security", Tier 3: "Fully public — Common name taxonomy"). Currently fine because Fairmont-SCP is effectively the only active tenant, but the Step 5 wipe SQL would affect every org if more existed. Before running the archive in production:
   - Confirm via `SELECT COUNT(*) FROM organizations WHERE is_active = 1` that only the expected org(s) are active.
   - Scope the `common_products` archive by `organization_id`, since that table IS org-scoped.

3. **The "auto-parser as suggestion" means calling `extract_base_and_attributes()` directly.** The existing `reparse` endpoint is post-creation — it modifies an existing common product. For the *guided UI* to pre-fill a path from raw vendor text, call `extract_base_and_attributes()` from `scripts/taxonomy_parser.py` (or the local fallback in `taxonomy.py`) on the raw string, then map its returned `base_name` and attributes into path steps the user can confirm. Don't try to reuse the `reparse` route for this.

4. **Reuse `product_matcher.match_products()` verbatim for Step 7.** It already takes `(ingredient_name, organization_id, conn, max_results)` and returns ranked matches with confidence scores. Don't reimplement matching logic.

5. **Yield % is a separate problem the costing directive also depends on.** `recipe_ingredients.yield_percentage` defaults to 100%. Recipes built before yield was populated will return inflated costs even after taxonomy is clean. Flag this as a parallel task (see Definition of Done).

---

## Critical scope clarification

"Wipe and re-import" applies **only** to:
- `common_products`
- `ingredient_variants`
- `base_ingredients`
- The FK columns on `products` / `ingredient_mappings` pointing at the above

It does **not** touch:
- `products` (vendor SKUs)
- `distributor_products`
- `price_history`
- `recipes` or `banquet_menus` / menu items (records are untouched)

Your actual vendor data and price history — built from months of invoice imports — stays untouched. You are re-linking existing products to a clean taxonomy, not re-importing them from scratch.

**On recipes specifically:** archiving a Common Product (`is_active = 0`) does not delete the `recipe_ingredients` row that points at it — the row and the FK stay intact. The only visible effect is that ingredient temporarily shows no price/cost until it's re-pointed at a clean Common Product in Step 7. No recipe data is lost at any point in this plan.

---

## Build Sequence

### Step 1 — Backend: path search & create endpoints

```
GET /taxonomy/search-path?path=Chicken,Breast&query=air
```
Returns variants and Common Products matching `query` under the given path. Empty `path` searches base ingredients.

```
POST /taxonomy/create-in-path
Body: { path: ["Chicken", "Breast"], name: "Airline", type: "variant" | "common_product" }
```
Creates a new variant or Common Product at the specified path location. Validates the parent path exists before creating.

Add to `api/app/routers/taxonomy.py`, alongside the existing `/variants` and `/common-products/search` endpoints — same patterns (RealDictCursor, audit logging via `log_audit`).

### Step 2 — Frontend: `PathBasedProductMapper.jsx`

New component, `frontend/src/pages/Products/`:
- Single controlled input, path tracked as an array (`["Chicken", "Breast"]`)
- Debounced search as you type (reuse the debounce pattern already in `Products.jsx`)
- Dropdown shows 📁 variants (drill deeper) vs 📦 Common Products (leaf, selectable) vs "+ Create" at current level
- Keyboard: comma/space advances a level, backspace at level start goes up, Enter on a 📦 selects and completes
- Breadcrumb of the current path above the input

### Step 3 — Integration

Replace the current freeform mapping cell in:
- `Products.jsx` — the primary "Type to search or create..." input (lines ~1118–1166)
- `TaxonomyView.jsx` — manual product reassignment flow

Leave the existing reassign endpoint (`PATCH /products/{id}/reassign`) in place — it's still useful for one-off corrections after the guided flow is live.

### Step 4 — Test before archiving

Use the new guided flow on a handful of real products first — don't touch existing taxonomy data yet. Good candidates: a couple of simple 2-level items (onions, lettuce) and one genuinely complex one (chicken breast variants), since that range is where UX problems would show up first. Confirm:
- Path search returns sensible results at each depth
- "Create as variant" vs "create as Common Product" feels right in practice
- Nothing about the keyboard flow (comma/space/backspace) feels janky

Your old data is still fully active and untouched at this point — this is a safe, reversible trial. Only move to Step 5 once the flow itself feels right.

### Step 4.5 — Run a duplicate-analysis pass before archiving

Before committing to a clean-slate wipe, get a real count of how messy the current `common_products` actually is. A script analogous to `scripts/analyze_product_duplicates.py` (which targets `products`) would do this — group `common_products` by `LOWER(common_name)` within `organization_id`, count duplicates, and group by detected base ingredient from the auto-parser. If the count is small (say, <30 messy/duplicate CPs), the existing `MergeCommonProductsModal` plus the `reparse` endpoint may be a faster path than full archive-and-remap. If the count is large, Step 5 stays. This is a 30-minute analysis script, not a build task — but it's the difference between a half-day cleanup and a half-week one.

### Step 5 — Archive existing taxonomy data

Soft-archive, don't delete. **Scope by org for `common_products` (which is org-scoped); the global `ingredient_variants` and `base_ingredients` tables affect every org, so confirm tenant count first (see Gotcha #2).**

```sql
-- Org-scoped: replace :org_id with the actual organization id
UPDATE common_products SET is_active = 0 WHERE organization_id = :org_id;

-- Global: only run after confirming no other active org depends on this data
UPDATE ingredient_variants SET is_active = 0;
UPDATE base_ingredients SET is_active = 0;
```
Keep the rows for reference/rollback. The guided UI only surfaces `is_active = 1` records, so this effectively gives you a clean tree without losing history.

### Step 6 — Remap products

Walk through `products` (your real vendor SKUs) and assign each to a clean Common Product via the new guided flow. The auto-parser can pre-fill a suggested path per product to speed this up — you're confirming, not typing from scratch, for most items.

### Step 7 — Re-link recipes (new in v2 — not in original plan)

`recipe_ingredients.common_product_id` will dangle once old Common Products are archived. Instead of manual re-entry per recipe:
1. For each recipe ingredient pointing at an archived `common_product_id`, pull its old `common_name`.
2. Run it through the existing matching pipeline (`learned → exact → base → contains → fuzzy → semantic`) against the *new* clean Common Products.
3. Surface suggested matches in a review screen (same UX pattern as the AI Recipe Parser's confirm step) rather than blind auto-apply.
4. Confirm in bulk where confidence is high; hand-fix the rest.

This reuses infrastructure you already paid for (pgvector + Voyage embeddings) instead of building something new.

---

## Out of scope for this pass

- Network-effect / shared mapping library (opt-in cross-tenant taxonomy) — separate future initiative, doesn't block menu costing
- Reorganize-by-drag-drop tool — explicitly rejected in favor of clean slate; revisit only if clean slate proves too disruptive mid-build

---

## Definition of done

- [ ] `search-path` and `create-in-path` endpoints live and tested
- [ ] `PathBasedProductMapper.jsx` replaces freeform input in Products.jsx and TaxonomyView.jsx
- [ ] `parent_variant_id` is wired through `IngredientVariantBase` / Create / the INSERT, so nested variants can be created in a single transaction
- [ ] `common_products` duplicate-analysis script run; archive scope decision (clean slate vs. targeted merge) documented before Step 5
- [ ] Old taxonomy data archived (not deleted), scoped correctly per Gotcha #2
- [ ] All active vendor products remapped through guided flow
- [ ] All recipe ingredients re-linked and verified against new Common Products
- [ ] **Parallel task tracked separately:** real yield % values populated on `recipe_ingredients` for top-priority menu recipes — clean taxonomy alone doesn't make costs defensible if yields are still 100% across the board
- [ ] Spot-check 5–10 real menu items' cost % against manual calculation before trusting the numbers for the costing directive
