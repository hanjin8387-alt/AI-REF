from fastapi import APIRouter, Depends

from ..core.security import require_app_token
from .backups import router as backups_router
from .bootstrap import router as bootstrap_router
from .device_auth import router as device_auth_router

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    dependencies=[Depends(require_app_token)],
)

router.include_router(bootstrap_router)
router.include_router(device_auth_router)
router.include_router(backups_router)
