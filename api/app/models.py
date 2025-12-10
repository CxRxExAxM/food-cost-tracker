"""
SQLAlchemy models for Food Cost Tracker.
Converted from SQLite schema in database.py
"""
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class Organization(Base):
    __tablename__ = 'organizations'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False)

    # Subscription & tier management
    subscription_tier = Column(String, nullable=False, default='free')
    subscription_status = Column(String, nullable=False, default='active')
    stripe_customer_id = Column(String, unique=True)
    stripe_subscription_id = Column(String, unique=True)

    # Tier limits
    max_users = Column(Integer, default=2)  # Free tier: 2, Basic: 5, Pro: 15, Enterprise: -1 (unlimited)
    max_recipes = Column(Integer, default=5)  # Free tier: 5, Basic: 50, Pro: -1, Enterprise: -1 (unlimited)
    max_distributors = Column(Integer, default=1)  # Free tier: 1, Basic: 3, Pro: -1, Enterprise: -1 (unlimited)
    max_ai_parses_per_month = Column(Integer, default=10)  # Free tier: 10, Basic: 100, Pro: 500, Enterprise: -1 (unlimited)
    ai_parses_used_this_month = Column(Integer, default=0)
    ai_parses_reset_date = Column(DateTime)

    # Contact info
    contact_email = Column(String)
    contact_phone = Column(String)

    # Status
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("subscription_tier IN ('free', 'basic', 'pro', 'enterprise')", name='check_subscription_tier'),
        CheckConstraint("subscription_status IN ('active', 'cancelled', 'past_due', 'trialing')", name='check_subscription_status'),
    )


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(Integer, ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    email = Column(String, unique=True, nullable=False)
    username = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    role = Column(String, nullable=False, default='viewer')
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("role IN ('admin', 'chef', 'viewer')", name='check_role'),
    )


class Distributor(Base):
    __tablename__ = 'distributors'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    code = Column(String, unique=True, nullable=False)
    contact_info = Column(Text)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Unit(Base):
    __tablename__ = 'units'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    abbreviation = Column(String, unique=True, nullable=False)
    unit_type = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class CommonProduct(Base):
    __tablename__ = 'common_products'

    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(Integer, ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    common_name = Column(String, nullable=False)
    category = Column(String)
    subcategory = Column(String)
    preferred_unit_id = Column(Integer, ForeignKey('units.id'))
    notes = Column(Text)
    is_active = Column(Integer, default=1)
    allergen_vegan = Column(Integer, default=0)
    allergen_vegetarian = Column(Integer, default=0)
    allergen_gluten = Column(Integer, default=0)
    allergen_crustation = Column(Integer, default=0)
    allergen_egg = Column(Integer, default=0)
    allergen_mollusk = Column(Integer, default=0)
    allergen_fish = Column(Integer, default=0)
    allergen_lupin = Column(Integer, default=0)
    allergen_dairy = Column(Integer, default=0)
    allergen_tree_nuts = Column(Integer, default=0)
    allergen_peanuts = Column(Integer, default=0)
    allergen_sesame = Column(Integer, default=0)
    allergen_soy = Column(Integer, default=0)
    allergen_sulphur_dioxide = Column(Integer, default=0)
    allergen_mustard = Column(Integer, default=0)
    allergen_celery = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Product(Base):
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(Integer, ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    brand = Column(String)
    category = Column(String)
    pack = Column(Integer)
    size = Column(Float)
    unit_id = Column(Integer, ForeignKey('units.id'))
    common_product_id = Column(Integer, ForeignKey('common_products.id'))
    is_catch_weight = Column(Integer, default=0)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class DistributorProduct(Base):
    __tablename__ = 'distributor_products'

    id = Column(Integer, primary_key=True, autoincrement=True)
    distributor_id = Column(Integer, ForeignKey('distributors.id', ondelete='CASCADE'))
    product_id = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'))
    distributor_sku = Column(String, nullable=False)
    distributor_name = Column(String)
    is_available = Column(Integer, default=1)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint('distributor_id IS NOT NULL AND distributor_sku IS NOT NULL',
                       name='unique_distributor_sku'),
    )


class PriceHistory(Base):
    __tablename__ = 'price_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    distributor_product_id = Column(Integer, ForeignKey('distributor_products.id', ondelete='CASCADE'))
    case_price = Column(Float, nullable=False)
    unit_price = Column(Float)
    effective_date = Column(DateTime, nullable=False)
    import_batch_id = Column(String)
    created_at = Column(DateTime, server_default=func.now())


class ImportBatch(Base):
    __tablename__ = 'import_batches'

    id = Column(String, primary_key=True)
    organization_id = Column(Integer, ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    distributor_id = Column(Integer, ForeignKey('distributors.id'))
    filename = Column(String, nullable=False)
    rows_imported = Column(Integer)
    rows_failed = Column(Integer)
    import_date = Column(DateTime, server_default=func.now())
    notes = Column(Text)


class Recipe(Base):
    __tablename__ = 'recipes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(Integer, ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    category = Column(String)
    category_path = Column(String)
    yield_amount = Column(Float)
    yield_unit_id = Column(Integer, ForeignKey('units.id'))
    servings = Column(Float)
    serving_unit_id = Column(Integer, ForeignKey('units.id'))
    prep_time_minutes = Column(Integer)
    cook_time_minutes = Column(Integer)
    method = Column(Text)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class RecipeIngredient(Base):
    __tablename__ = 'recipe_ingredients'

    id = Column(Integer, primary_key=True, autoincrement=True)
    recipe_id = Column(Integer, ForeignKey('recipes.id', ondelete='CASCADE'))
    common_product_id = Column(Integer, ForeignKey('common_products.id'))
    sub_recipe_id = Column(Integer, ForeignKey('recipes.id'))
    quantity = Column(Float, nullable=False)
    unit_id = Column(Integer, ForeignKey('units.id'))
    yield_percentage = Column(Float, default=100.00)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
