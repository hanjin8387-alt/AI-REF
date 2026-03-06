from __future__ import annotations

from functools import lru_cache

from fastapi import HTTPException, status
from supabase import Client, create_client

from .config import get_settings


@lru_cache()
def get_supabase_client() -> Client:
    """Get Supabase client instance."""
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase is not configured",
        )
    return create_client(settings.supabase_url, settings.supabase_key)


def get_db():
    """FastAPI dependency for database access."""
    client = get_supabase_client()
    try:
        yield client
    finally:
        pass
