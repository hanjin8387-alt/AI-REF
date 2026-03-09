from contextlib import asynccontextmanager
import logging
import time
from uuid import uuid4

from fastapi import Depends, FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from supabase import Client

from .api.admin import router as admin_router
from .api.auth import router as auth_router
from .api.inventory import router as inventory_router
from .api.notifications import router as notifications_router
from .api.recipes import router as recipes_router
from .api.scans import router as scans_router
from .api.shopping import router as shopping_router
from .api.stats import router as stats_router
from .core.config import get_settings
from .core.database import get_db
from .core.startup_validation import validate_startup_settings

logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address, default_limits=["240/minute"])
REQUEST_ID_HEADER = "X-Request-ID"
DEFAULT_CACHE_CONTROL = "private, max-age=15, stale-while-revalidate=30"


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    validate_startup_settings(settings)
    logging.basicConfig(
        level=logging.DEBUG if settings.debug else logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    logger.info("startup app=%s env=%s model=%s", settings.app_name, settings.environment, settings.gemini_model)
    yield
    logger.info("shutdown app=%s", settings.app_name)


app = FastAPI(
    title="PROMETHEUS API",
    description="""
Smart ingredient management API.

Features:
- Scan ingredients/receipts
- Manage inventory
- Recipe recommendations and favorites
- Cooking history and notifications
""",
    version="1.1.0",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(SlowAPIMiddleware)

settings = get_settings()
cors_origins = settings.parsed_cors_origins
allow_credentials = "*" not in cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=500)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    started = time.perf_counter()
    request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid4())
    request.state.request_id = request_id

    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "request failed method=%s path=%s request_id=%s",
            request.method,
            request.url.path,
            request_id,
        )
        raise

    elapsed = time.perf_counter() - started
    process_time = f"{elapsed:.6f}"

    logger.info(
        "perf.request method=%s path=%s status=%s process_time=%s request_id=%s",
        request.method,
        request.url.path,
        response.status_code,
        process_time,
        request_id,
    )

    response.headers[REQUEST_ID_HEADER] = request_id
    response.headers["X-Process-Time"] = process_time
    response.headers["X-Response-Time"] = process_time
    if request.method == "GET" and response.status_code < status.HTTP_400_BAD_REQUEST:
        response.headers.setdefault("Cache-Control", DEFAULT_CACHE_CONTROL)
    return response


app.include_router(auth_router)
app.include_router(scans_router)
app.include_router(inventory_router)
app.include_router(recipes_router)
app.include_router(notifications_router)
app.include_router(shopping_router)
app.include_router(stats_router)
app.include_router(admin_router)


@app.get("/")
@limiter.limit("30/minute")
async def root(request: Request):
    return {
        "name": "PROMETHEUS API",
        "version": "1.1.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
@limiter.limit("30/minute")
async def health(
    request: Request,
    db: Client = Depends(get_db),
):
    try:
        db.table("devices").select("device_id").limit(1).execute()
    except Exception:
        logger.exception("health check db ping failed")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "degraded",
                "database": "error",
            },
        )

    return {
        "status": "ok",
        "database": "ok",
    }
