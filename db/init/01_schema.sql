-- Food Cost Tracker Database Schema

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Distributors table
CREATE TABLE distributors (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    code VARCHAR(50) UNIQUE NOT NULL,
    contact_info JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Units of measure
CREATE TABLE units (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    abbreviation VARCHAR(10) UNIQUE NOT NULL,
    unit_type VARCHAR(20) NOT NULL, -- 'weight', 'volume', 'count'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Products catalog
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    brand VARCHAR(100),
    category VARCHAR(100),
    pack INTEGER, -- Number of units per case
    size DECIMAL(10, 3), -- Size of individual unit
    unit_id INTEGER REFERENCES units(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Distributor products (junction table with distributor-specific info)
CREATE TABLE distributor_products (
    id SERIAL PRIMARY KEY,
    distributor_id INTEGER REFERENCES distributors(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
    distributor_sku VARCHAR(100) NOT NULL, -- Distributor's item code/SUPC
    distributor_name VARCHAR(255), -- How distributor names this product
    is_available BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(distributor_id, distributor_sku)
);

-- Price history
CREATE TABLE price_history (
    id SERIAL PRIMARY KEY,
    distributor_product_id INTEGER REFERENCES distributor_products(id) ON DELETE CASCADE,
    case_price DECIMAL(10, 2) NOT NULL,
    unit_price DECIMAL(10, 4), -- Calculated: case_price / (pack * size)
    effective_date DATE NOT NULL,
    import_batch_id UUID,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(distributor_product_id, effective_date)
);

-- Import batches (track CSV imports)
CREATE TABLE import_batches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    distributor_id INTEGER REFERENCES distributors(id),
    filename VARCHAR(255) NOT NULL,
    rows_imported INTEGER,
    rows_failed INTEGER,
    import_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

-- Recipes
CREATE TABLE recipes (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    yield_amount DECIMAL(10, 3), -- How many portions/servings
    yield_unit_id INTEGER REFERENCES units(id),
    prep_time_minutes INTEGER,
    cook_time_minutes INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Recipe ingredients
CREATE TABLE recipe_ingredients (
    id SERIAL PRIMARY KEY,
    recipe_id INTEGER REFERENCES recipes(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES products(id),
    quantity DECIMAL(10, 4) NOT NULL,
    unit_id INTEGER REFERENCES units(id),
    yield_percentage DECIMAL(5, 2) DEFAULT 100.00, -- Account for waste/trim
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_distributor_products_distributor ON distributor_products(distributor_id);
CREATE INDEX idx_distributor_products_product ON distributor_products(product_id);
CREATE INDEX idx_distributor_products_sku ON distributor_products(distributor_sku);
CREATE INDEX idx_price_history_dist_prod ON price_history(distributor_product_id);
CREATE INDEX idx_price_history_date ON price_history(effective_date DESC);
CREATE INDEX idx_recipe_ingredients_recipe ON recipe_ingredients(recipe_id);
CREATE INDEX idx_recipe_ingredients_product ON recipe_ingredients(product_id);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_distributors_updated_at BEFORE UPDATE ON distributors
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_products_updated_at BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_distributor_products_updated_at BEFORE UPDATE ON distributor_products
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_recipes_updated_at BEFORE UPDATE ON recipes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_recipe_ingredients_updated_at BEFORE UPDATE ON recipe_ingredients
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
