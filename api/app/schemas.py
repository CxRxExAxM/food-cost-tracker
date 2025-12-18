from pydantic import BaseModel, Field
from typing import Optional, List
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
    is_catch_weight: bool = False


class Product(ProductBase):
    id: int
    organization_id: int
    outlet_id: int
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
    common_product_id: Optional[int] = None  # Map to product (for costing)
    sub_recipe_id: Optional[int] = None      # OR map to sub-recipe
    ingredient_name: Optional[str] = None    # OR use text-only name (no costing)
    quantity: float
    unit_id: int
    yield_percentage: float = 100.0
    notes: Optional[str] = None


class RecipeIngredient(RecipeIngredientBase):
    id: int
    recipe_id: int
    # Joined fields
    common_name: Optional[str] = None
    unit_abbreviation: Optional[str] = None
    sub_recipe_name: Optional[str] = None

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
    yield_amount: Optional[float] = None  # Physical yield (e.g., 2 lbs, 1 gal)
    yield_unit_id: Optional[int] = None   # Unit for yield_amount
    servings: Optional[float] = None      # Number of portions or serving size amount
    serving_unit_id: Optional[int] = None # Unit for servings (None = portions)
    prep_time_minutes: Optional[int] = None  # Keeping for backward compatibility
    cook_time_minutes: Optional[int] = None  # Keeping for backward compatibility
    method: Optional[list[RecipeMethodStep]] = None  # List of numbered steps
    notes: Optional[str] = None


class RecipeCreate(RecipeBase):
    ingredients: list[RecipeIngredientBase] = []


class Recipe(RecipeBase):
    id: int
    organization_id: int
    outlet_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RecipeWithIngredients(Recipe):
    """Recipe with full ingredient details."""
    ingredients: list[RecipeIngredient] = []


class IngredientWithCost(BaseModel):
    """Ingredient with cost calculation details."""
    id: int
    recipe_id: int
    common_product_id: Optional[int] = None
    sub_recipe_id: Optional[int] = None
    ingredient_name: Optional[str] = None    # Text-only ingredient name
    quantity: float
    unit_id: Optional[int] = None
    yield_percentage: Optional[float] = None
    notes: Optional[str] = None
    common_name: Optional[str] = None
    unit_abbreviation: Optional[str] = None
    sub_recipe_name: Optional[str] = None
    sub_recipe_yield: Optional[float] = None
    # Cost fields
    unit_price: Optional[float] = None
    cost: Optional[float] = None
    cost_percentage: Optional[float] = None
    has_price: bool = False
    price_source: Optional[str] = None

    class Config:
        from_attributes = True


class AllergenSummary(BaseModel):
    """Allergen summary for a recipe."""
    contains: list[str] = []
    vegan: bool = False
    vegetarian: bool = False
    by_ingredient: list[dict] = []


class RecipeWithCost(Recipe):
    """Recipe with cost calculation."""
    total_cost: float
    cost_per_serving: Optional[float] = None
    yield_unit_abbreviation: Optional[str] = None
    serving_unit_abbreviation: Optional[str] = None  # None = portions
    ingredients: list[IngredientWithCost] = []
    allergens: Optional[AllergenSummary] = None


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


# Organizations
class OrganizationBase(BaseModel):
    name: str
    slug: str
    subscription_tier: str
    subscription_status: Optional[str] = 'active'
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    subscription_tier: Optional[str] = None
    subscription_status: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    is_active: Optional[int] = None


class OrganizationResponse(OrganizationBase):
    id: int
    max_users: int
    max_recipes: int
    max_distributors: int
    max_ai_parses_per_month: int
    ai_parses_used_this_month: int
    is_active: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Outlets
class OutletBase(BaseModel):
    name: str
    location: Optional[str] = None
    description: Optional[str] = None


class OutletCreate(OutletBase):
    pass


class OutletUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[int] = None


class OutletResponse(OutletBase):
    id: int
    organization_id: int
    is_active: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Users
class UserBase(BaseModel):
    email: str
    username: str
    full_name: Optional[str] = None
    role: str = 'viewer'


class UserCreate(UserBase):
    password: str
    organization_id: int


class UserUpdate(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[int] = None


class UserResponse(UserBase):
    id: int
    organization_id: int
    organization_name: Optional[str] = None
    organization_tier: Optional[str] = None
    is_active: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ============================================
# AI Recipe Parser Schemas
# ============================================

class ProductMatch(BaseModel):
    """Suggested product match for an ingredient."""
    common_product_id: int
    common_name: str
    category: Optional[str] = None
    subcategory: Optional[str] = None
    confidence: float = Field(..., ge=0, le=1, description="Match confidence 0-1")
    exact_match: bool
    match_type: str = Field(..., description="exact, contains_in_product, product_in_ingredient, fuzzy")


class ParsedIngredient(BaseModel):
    """Single ingredient parsed from recipe."""
    parsed_name: str = Field(..., description="Original ingredient name from document")
    quantity: float
    unit: str
    unit_id: Optional[int] = None
    normalized_quantity: float
    normalized_unit: str
    normalized_unit_id: Optional[int] = None
    prep_note: Optional[str] = None
    suggested_products: List[ProductMatch] = []
    needs_review: bool = Field(..., description="True if no confident match found")


class YieldInfo(BaseModel):
    """Recipe yield information."""
    quantity: float
    unit: str
    unit_id: Optional[int] = None


class UsageStats(BaseModel):
    """Monthly usage statistics."""
    tier: str
    used: int
    limit: str | int  # Can be int or "unlimited"
    remaining: str | int


class ParseHistoryItem(BaseModel):
    """Single parse attempt history."""
    filename: str
    status: str
    ingredients_count: Optional[int] = None
    created_at: Optional[str] = None
    error: Optional[str] = None


class UsageStatsResponse(BaseModel):
    """Full usage statistics response."""
    organization_id: int
    tier: str
    current_month: dict
    can_parse: bool
    recent_history: List[ParseHistoryItem]


class ParseFileResponse(BaseModel):
    """Response from parse-file endpoint."""
    parse_id: int
    recipe_name: str
    yield_info: Optional[YieldInfo] = None
    description: Optional[str] = None
    category: Optional[str] = None
    ingredients: List[ParsedIngredient]
    usage: UsageStats
    credits_used: bool = Field(..., description="True if this parse counted toward limit")


class CreateRecipeIngredient(BaseModel):
    """Ingredient for recipe creation from AI parser."""
    common_product_id: Optional[int] = None  # Map to product (for costing)
    ingredient_name: Optional[str] = None     # OR use text-only name
    quantity: float
    unit_id: int
    notes: Optional[str] = None


class CreateRecipeFromParseRequest(BaseModel):
    """Request to create recipe from parse results."""
    parse_id: int
    name: str
    outlet_id: int
    yield_quantity: Optional[float] = None
    yield_unit_id: Optional[int] = None
    description: Optional[str] = None
    category: Optional[str] = None
    ingredients: List[CreateRecipeIngredient]


class CreateRecipeFromParseResponse(BaseModel):
    """Response from create recipe."""
    recipe_id: int
    name: str
    status: str = "draft"
    message: str


class QuickCreateProductRequest(BaseModel):
    """Request to quickly create a common product."""
    common_name: str
    category: str
    subcategory: Optional[str] = None
    organization_id: int


class QuickCreateProductResponse(BaseModel):
    """Response from quick create."""
    common_product_id: int
    common_name: str
    category: str
    message: str


class ProductSearchResult(BaseModel):
    """Single product search result."""
    common_product_id: int
    common_name: str
    category: Optional[str] = None
    subcategory: Optional[str] = None


class ProductSearchResponse(BaseModel):
    """Product search results."""
    results: List[ProductSearchResult]
    count: int


class ParseErrorResponse(BaseModel):
    """Error response from parsing."""
    detail: str
    parse_status: Optional[str] = "failed"
    credits_used: bool = False
    usage: Optional[UsageStats] = None


class RateLimitErrorResponse(BaseModel):
    """Rate limit exceeded error."""
    detail: str
    attempts: int
    limit: int = 10
    reset_in_minutes: int


class MonthlyLimitErrorResponse(BaseModel):
    """Monthly limit exceeded error."""
    detail: str
    usage: UsageStats
    upgrade_url: str = "/settings/subscription"
