# app/main.py
"""
GenCode Studio Backend - Clean Architecture
"""
import os
import sys
import uvicorn
from contextlib import asynccontextmanager
from pathlib import Path
from datetime import datetime, timezone



from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse, JSONResponse

# Rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from dotenv import load_dotenv
load_dotenv()

# Import from new modular structure
from app.core.config import settings
from app.lib.websocket import ConnectionManager
from app.workflow import run_workflow, resume_workflow

# Set environment for hot reload
os.environ["WATCHFILES_IGNORE_PATHS"] = "workspaces"

# Print environment status
print("🔑 Environment check:")
print(f"  GEMINI_API_KEY loaded: {bool(settings.llm.gemini_api_key)}")
print(f"  OPENAI_API_KEY loaded: {bool(settings.llm.openai_api_key)}")
print(f"  Default provider: {settings.llm.default_provider}")
print(f"  Default model: {settings.llm.default_model}")

# Connection manager instance
manager = ConnectionManager()


# ---------------------------------------------------------------------------
# LIFESPAN
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    print("🚀 GenCode Studio starting...")
    
    # Ensure workspaces directory exists
    settings.paths.workspaces_dir.mkdir(parents=True, exist_ok=True)
    
    # Connect to database
    from app.db import connect_db, disconnect_db
    await connect_db()
    
    yield
    
    print("🔌 Shutting down...")
    await disconnect_db()
    
    # FIX #18: Close HTTP session used for embeddings
    try:
        from app.arbormind.router import close_http_session
        await close_http_session()
    except Exception as e:
        print(f"[SHUTDOWN] HTTP session cleanup error: {e}")


# ---------------------------------------------------------------------------
# APP INITIALIZATION
# ---------------------------------------------------------------------------

app = FastAPI(
    title="GenCode Studio",
    version="2.0.0",
    lifespan=lifespan,
)
app.state.manager = manager

# Monitoring
from app.lib.monitoring import register_monitoring
register_monitoring(app)

# CORS - FIX #9: Use environment variable for allowed origins
# In production, set CORS_ORIGINS to comma-separated list of allowed origins
cors_origins_str = os.getenv("CORS_ORIGINS", "*")
cors_origins = cors_origins_str.split(",") if cors_origins_str != "*" else ["*"]

if cors_origins == ["*"] and not settings.debug:
    print("⚠️ [CORS] Warning: Using allow_origins=['*'] - consider setting CORS_ORIGINS in production")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate Limiting - protect against API abuse
# Default: 100 requests per minute per IP
# Configure via RATE_LIMIT env var (e.g., "50/minute")
rate_limit = os.getenv("RATE_LIMIT", "100/minute")
limiter = Limiter(key_func=get_remote_address, default_limits=[rate_limit])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
print(f"🛡️ [SECURITY] Rate limiting enabled: {rate_limit}")


# ---------------------------------------------------------------------------
# WEBSOCKET
# ---------------------------------------------------------------------------

@app.websocket("/ws/{project_id}")
async def websocket_endpoint(websocket: WebSocket, project_id: str):
    await manager.connect(websocket, project_id)
    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "USER_INPUT":
                msg_project_id = data.get("projectId")
                message = data.get("message")

                if msg_project_id == project_id and message:
                    print(f'[WS] Received input for {project_id}: "{message[:50]}..."')
                    await resume_workflow(
                        project_id, 
                        message, 
                        manager, 
                        settings.paths.workspaces_dir
                    )

    except WebSocketDisconnect:
        await manager.disconnect(websocket, project_id)
    except Exception as e:
        print(f"[WS] Error: {e}")


# ---------------------------------------------------------------------------
# API ROUTES
# ---------------------------------------------------------------------------

print("[Routes] Loading API routes...")

# Import and register routes
from app.api import (
    health,
    projects,
    workspace,
    agents,
    sandbox,
    deployment,
    providers,
    tracking,
)

app.include_router(health.router)
app.include_router(projects.router)
app.include_router(workspace.router)
app.include_router(agents.router)
app.include_router(sandbox.router)
app.include_router(deployment.router)
app.include_router(providers.router)
app.include_router(tracking.router)


# ---------------------------------------------------------------------------
# STATIC FILES
# ---------------------------------------------------------------------------

if settings.paths.frontend_dist.exists():
    print(f"📁 Serving frontend from: {settings.paths.frontend_dist}")
    
    assets_path = settings.paths.frontend_dist / "assets"
    if assets_path.exists():
        app.mount("/assets", StaticFiles(directory=assets_path), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        file_path = settings.paths.frontend_dist / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(settings.paths.frontend_dist / "index.html")
else:
    print(f"⚠️ Frontend not found at {settings.paths.frontend_dist}")


# ---------------------------------------------------------------------------
# RUN
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=True,
        reload_dirs=["app"],
        reload_excludes=["workspaces/**/*", "**/*.log", "**/node_modules/**"],
    )
