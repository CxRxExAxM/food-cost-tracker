-- Migration: Add allergen/dietary flags and recipe enhancements
-- Date: 2025-11-20

-- Add allergen/dietary flags to common_products
ALTER TABLE common_products ADD COLUMN allergen_vegan INTEGER DEFAULT 0;
ALTER TABLE common_products ADD COLUMN allergen_vegetarian INTEGER DEFAULT 0;
ALTER TABLE common_products ADD COLUMN allergen_gluten INTEGER DEFAULT 0;
ALTER TABLE common_products ADD COLUMN allergen_crustation INTEGER DEFAULT 0;
ALTER TABLE common_products ADD COLUMN allergen_egg INTEGER DEFAULT 0;
ALTER TABLE common_products ADD COLUMN allergen_mollusk INTEGER DEFAULT 0;
ALTER TABLE common_products ADD COLUMN allergen_fish INTEGER DEFAULT 0;
ALTER TABLE common_products ADD COLUMN allergen_lupin INTEGER DEFAULT 0;
ALTER TABLE common_products ADD COLUMN allergen_dairy INTEGER DEFAULT 0;
ALTER TABLE common_products ADD COLUMN allergen_tree_nuts INTEGER DEFAULT 0;
ALTER TABLE common_products ADD COLUMN allergen_peanuts INTEGER DEFAULT 0;
ALTER TABLE common_products ADD COLUMN allergen_sesame INTEGER DEFAULT 0;
ALTER TABLE common_products ADD COLUMN allergen_soy INTEGER DEFAULT 0;
ALTER TABLE common_products ADD COLUMN allergen_sulphur_dioxide INTEGER DEFAULT 0;
ALTER TABLE common_products ADD COLUMN allergen_mustard INTEGER DEFAULT 0;
ALTER TABLE common_products ADD COLUMN allergen_celery INTEGER DEFAULT 0;

-- Add method steps to recipes (stored as JSON)
ALTER TABLE recipes ADD COLUMN method TEXT; -- JSON array of step objects

-- Change category to category_path for nested folder structure
ALTER TABLE recipes ADD COLUMN category_path TEXT;

-- Add sub_recipe_id to recipe_ingredients to support recipes as ingredients
ALTER TABLE recipe_ingredients ADD COLUMN sub_recipe_id INTEGER REFERENCES recipes(id);
