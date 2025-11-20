-- Seed data for Food Cost Tracker

-- Insert distributors
INSERT INTO distributors (name, code) VALUES
    ('Sysco', 'sysco'),
    ('Vesta', 'vesta'),
    ('SM Seafood', 'smseafood'),
    ('Shamrock', 'shamrock'),
    ('Noble Bread', 'noblebread'),
    ('Sterling', 'sterling');

-- Insert common units
INSERT INTO units (name, abbreviation, unit_type) VALUES
    ('Pound', 'lb', 'weight'),
    ('Ounce', 'oz', 'weight'),
    ('Kilogram', 'kg', 'weight'),
    ('Gram', 'g', 'weight'),
    ('Gallon', 'gal', 'volume'),
    ('Quart', 'qt', 'volume'),
    ('Pint', 'pt', 'volume'),
    ('Cup', 'cup', 'volume'),
    ('Fluid Ounce', 'fl oz', 'volume'),
    ('Liter', 'L', 'volume'),
    ('Milliliter', 'mL', 'volume'),
    ('Tablespoon', 'tbsp', 'volume'),
    ('Teaspoon', 'tsp', 'volume'),
    ('Each', 'ea', 'count'),
    ('Dozen', 'doz', 'count'),
    ('Case', 'case', 'count'),
    ('Box', 'box', 'count'),
    ('Bag', 'bag', 'count'),
    ('Can', 'can', 'count'),
    ('Jar', 'jar', 'count');
