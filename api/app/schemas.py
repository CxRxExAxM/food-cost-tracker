from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date


# Common Products
class CommonProductBase(BaseModel):
    common_name: str
    category: Optional[str] = None
    subcategory: Optional[str] = None
    preferred_unit_id: Optional[int] = None
    notes: Optional[str] = None


class CommonProductCreate(CommonProductBase):
    pass


class CommonProductUpdate(BaseModel):
    common_name: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    preferred_unit_id: Optional[int] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class CommonProduct(CommonProductBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Products
class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    pack: Optional[int] = None
    size: Optional[float] = None
    unit_id: Optional[int] = None
    common_product_id: Optional[int] = None


class Product(ProductBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProductWithPrice(Product):
    """Product with latest price information."""
    distributor_name: Optional[str] = None
    distributor_sku: Optional[str] = None
    case_price: Optional[float] = None
    unit_price: Optional[float] = None
    effective_date: Optional[date] = None
    unit_abbreviation: Optional[str] = None


class ProductMapping(BaseModel):
    """Map a product to a common product."""
    product_id: int
    common_product_id: int


# Distributors
class Distributor(BaseModel):
    id: int
    name: str
    code: str
    is_active: bool


# Units
class Unit(BaseModel):
    id: int
    name: str
    abbreviation: str
    unit_type: str


# Recipes
class RecipeIngredientBase(BaseModel):
    common_product_id: int
    quantity: float
    unit_id: int
    yield_percentage: float = 100.0
    notes: Optional[str] = None


class RecipeIngredient(RecipeIngredientBase):
    id: int
    recipe_id: int

    class Config:
        from_attributes = True


class RecipeBase(BaseModel):
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    yield_amount: Optional[float] = None
    yield_unit_id: Optional[int] = None
    prep_time_minutes: Optional[int] = None
    cook_time_minutes: Optional[int] = None


class RecipeCreate(RecipeBase):
    ingredients: list[RecipeIngredientBase] = []


class Recipe(RecipeBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RecipeWithIngredients(Recipe):
    """Recipe with full ingredient details."""
    ingredients: list[RecipeIngredient] = []


class RecipeWithCost(Recipe):
    """Recipe with cost calculation."""
    total_cost: float
    cost_per_serving: Optional[float] = None
    ingredients: list[dict] = []  # Ingredients with prices


# Price History
class PriceHistory(BaseModel):
    id: int
    distributor_product_id: int
    case_price: float
    unit_price: Optional[float] = None
    effective_date: date
    created_at: datetime

    class Config:
        from_attributes = True
