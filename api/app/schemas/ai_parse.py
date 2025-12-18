"""
Pydantic schemas for AI recipe parsing endpoints.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


# ============================================
# Ingredient Schemas
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


# ============================================
# Yield Schemas
# ============================================

class YieldInfo(BaseModel):
    """Recipe yield information."""
    quantity: float
    unit: str
    unit_id: Optional[int] = None


# ============================================
# Usage Stats Schemas
# ============================================

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


# ============================================
# Parse File Response
# ============================================

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


# ============================================
# Create Recipe from Parse
# ============================================

class CreateRecipeIngredient(BaseModel):
    """Ingredient for recipe creation."""
    common_product_id: int
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


# ============================================
# Quick Create Product
# ============================================

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


# ============================================
# Product Search
# ============================================

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


# ============================================
# Error Responses
# ============================================

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
