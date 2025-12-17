from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

from app.core.config import settings

# @ROUTER_IMPORTS - DO NOT REMOVE THIS LINE
from app.routers import tasks
# The Integrator will inject router imports here
# Example: from app.routers import users, auth

# @MODEL_IMPORTS - DO NOT REMOVE THIS LINE
from app.models import Task
# The Integrator will inject model imports here or we auto-discover

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.mongodb_client = AsyncIOMotorClient(settings.MONGO_URL)
    app.database = app.mongodb_client[settings.DB_NAME]
    
    # Initialize Beanie
    # @BEANIE_MODELS - The Integrator will inject the model list here
    # Example: document_models = [User, Post]
    document_models = [Task] 
    
    if document_models:
        await init_beanie(database=app.database, document_models=document_models)
    
    yield
    # Shutdown
    app.mongodb_client.close()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "version": settings.VERSION}

# @ROUTER_REGISTER - DO NOT REMOVE THIS LINE
app.include_router(tasks.router, prefix='/api/tasks', tags=['tasks'])
# The Integrator will inject app.include_router calls here
# Example: app.include_router(users.router, prefix="/api/users", tags=["users"])


# ---------------------------------------------------------------------------
# ROUTE AUDIT LOG
# ---------------------------------------------------------------------------
print("📊 [Route Audit] Registered Routes:")
for route in app.routes:
    if hasattr(route, "path") and hasattr(route, "methods"):
        methods = ", ".join(route.methods)
        print(f"   - {methods} {route.path}")
