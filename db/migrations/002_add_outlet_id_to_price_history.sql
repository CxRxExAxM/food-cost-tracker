-- Migration: Add outlet_id to price_history table
-- Date: 2024-12-14
-- Purpose: Enable per-outlet pricing for shared products

-- Add outlet_id column (nullable initially for migration)
ALTER TABLE price_history ADD COLUMN outlet_id INTEGER;

-- Populate outlet_id from import_batches for existing records
UPDATE price_history ph
SET outlet_id = ib.outlet_id
FROM import_batches ib
WHERE ph.import_batch_id = ib.id;

-- Set outlet_id to NOT NULL
ALTER TABLE price_history ALTER COLUMN outlet_id SET NOT NULL;

-- Add foreign key constraint
ALTER TABLE price_history
ADD CONSTRAINT fk_price_history_outlet
FOREIGN KEY (outlet_id) REFERENCES outlets(id) ON DELETE CASCADE;

-- Drop old unique constraint
ALTER TABLE price_history DROP CONSTRAINT IF EXISTS price_history_distributor_product_id_effective_date_key;

-- Add new unique constraint including outlet_id
-- This allows same product to have different prices per outlet per date
ALTER TABLE price_history
ADD CONSTRAINT unique_price_per_outlet_product_date
UNIQUE (distributor_product_id, outlet_id, effective_date);

-- Create index for faster filtering by outlet
CREATE INDEX idx_price_history_outlet ON price_history(outlet_id);

COMMENT ON COLUMN price_history.outlet_id IS 'Which outlet this price belongs to - allows different outlets to have different prices for same product';
