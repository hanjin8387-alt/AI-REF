from fastapi import APIRouter, Depends

from ..core.security import require_app_token
from .shopping_mutations import router as shopping_mutations_router
from .shopping_queries import router as shopping_queries_router

router = APIRouter(
    prefix="/shopping",
    tags=["shopping"],
    dependencies=[Depends(require_app_token)],
)

router.include_router(shopping_queries_router)
router.include_router(shopping_mutations_router)
