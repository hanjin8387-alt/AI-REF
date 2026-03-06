from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class RecipeIngredient(BaseModel):
    name: str
    quantity: float
    unit: str
    available: bool = False
    expiry_days: Optional[int] = None


class Recipe(BaseModel):
    id: str
    title: str
    description: str
    image_url: Optional[str] = None
    cooking_time_minutes: int
    difficulty: str
    servings: int
    ingredients: List[RecipeIngredient]
    instructions: List[str]
    priority_score: float = Field(default=0.0, description="Recommendation priority")
    recommendation_reason: Optional[str] = Field(default=None, description="Why this recipe was recommended")
    is_favorite: bool = False


class RecipeListResponse(BaseModel):
    recipes: List[Recipe]
    total_count: int


class RecommendationJobCreateResponse(BaseModel):
    job_id: str
    status: str


class RecommendationJobStatusResponse(BaseModel):
    job_id: str
    status: str
    recipes: List[Recipe] = Field(default_factory=list)
    total_count: int = 0
    error: Optional[str] = None


class FavoriteRecipeRequest(BaseModel):
    recipe: Optional[Recipe] = None


class FavoriteToggleResponse(BaseModel):
    success: bool
    is_favorite: bool
    message: str


class CookCompleteRequest(BaseModel):
    servings: int = Field(default=1, description="Number of servings cooked")


class CookCompleteResponse(BaseModel):
    success: bool
    message: str
    deducted_items: List[dict[str, Any]]


class CookingHistoryItem(BaseModel):
    id: str
    recipe_id: Optional[str] = None
    recipe_title: str
    servings: int
    deducted_items: List[dict[str, Any]] = Field(default_factory=list)
    cooked_at: datetime


class CookingHistoryResponse(BaseModel):
    items: List[CookingHistoryItem]
    total_count: int
    limit: int
    offset: int
    has_more: bool
