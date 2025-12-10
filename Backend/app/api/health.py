# app/api/health.py
"""
Health check endpoints.
"""
from datetime import datetime, timezone
from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/healthz")
async def healthz():
    """Simple health check."""
    return {"ok": True, "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/api/health")
async def api_health():
    """API health check."""
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}
