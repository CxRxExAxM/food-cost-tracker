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
    # Allergen/Dietary Flags
    allergen_vegan: bool = False
    allergen_vegetarian: bool = False
    allergen_gluten: bool = False
    allergen_crustation: bool = False
    allergen_egg: bool = False
    allergen_mollusk: bool = False
    allergen_fish: bool = False
    allergen_lupin: bool = False
    allergen_dairy: bool = False
    allergen_tree_nuts: bool = False
    allergen_peanuts: bool = False
    allergen_sesame: bool = False
    allergen_soy: bool = False
    allergen_sulphur_dioxide: bool = False
    allergen_mustard: bool = False
    allergen_celery: bool = False


class CommonProductCreate(CommonProductBase):
    pass


class CommonProductUpdate(BaseModel):
    common_name: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    preferred_unit_id: Optional[int] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None
    # Allergen/Dietary Flags
    allergen_vegan: Optional[bool] = None
    allergen_vegetarian: Optional[bool] = None
    allergen_gluten: Optional[bool] = None
    allergen_crustation: Optional[bool] = None
    allergen_egg: Optional[bool] = None
    allergen_mollusk: Optional[bool] = None
    allergen_fish: Optional[bool] = None
    allergen_lupin: Optional[bool] = None
    allergen_dairy: Optional[bool] = None
    allergen_tree_nuts: Optional[bool] = None
    allergen_peanuts: Optional[bool] = None
    allergen_sesame: Optional[bool] = None
    allergen_soy: Optional[bool] = None
    allergen_sulphur_dioxide: Optional[bool] = None
    allergen_mustard: Optional[bool] = None
    allergen_celery: Optional[bool] = None


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
    common_product_name: Optional[str] = None


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
    common_product_id: Optional[int] = None  # Either this...
    sub_recipe_id: Optional[int] = None      # ...or this
    quantity: float
    unit_id: int
    yield_percentage: float = 100.0
    notes: Optional[str] = None


class RecipeIngredient(RecipeIngredientBase):
    id: int
    recipe_id: int

    class Config:
        from_attributes = True


class RecipeMethodStep(BaseModel):
    step_number: int
    instruction: str

class RecipeBase(BaseModel):
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    category_path: Optional[str] = None  # Free-form folder structure
    yield_amount: Optional[float] = None
    yield_unit_id: Optional[int] = None
    prep_time_minutes: Optional[int] = None  # Keeping for backward compatibility
    cook_time_minutes: Optional[int] = None  # Keeping for backward compatibility
    method: Optional[list[RecipeMethodStep]] = None  # List of numbered steps
    notes: Optional[str] = None


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
