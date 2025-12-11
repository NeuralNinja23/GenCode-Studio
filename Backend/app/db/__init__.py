# app/db/__init__.py
"""
Database module.
"""
import os
from typing import Optional

# Motor client instance
_client = None
_db = None
_connection_error: Optional[str] = None


async def connect_db():
    """
    Connect to MongoDB.
    
    If MongoDB is not available, stores the error for later retrieval
    rather than silently failing.
    """
    global _client, _db, _connection_error
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        
        mongo_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        _client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=5000)

        # FIX DB-001: Robust database name parsing
        try:
            _db = _client.get_default_database()
        except Exception:
            _db = _client.gencode
        
        # Test connection - this will fail fast if MongoDB is not running
        await _client.admin.command("ping")
        print("✅ [DB] Connected to MongoDB")
        
        # Initialize Beanie
        from beanie import init_beanie
        from app.models import Project, WorkflowStepRecord, Snapshot
        from app.models.deployment import Deployment
        from app.models.workflow import WorkflowSession
        
        await init_beanie(
            database=_db,
            document_models=[Project, WorkflowStepRecord, Snapshot, Deployment, WorkflowSession]
        )
        print("✅ [DB] Beanie ODM Initialized")
        _connection_error = None
    except Exception as e:
        error_msg = str(e)
        print(f"⚠️ [DB] MongoDB not available: {error_msg}")
        print(f"   ℹ️ The system will continue but database features will be disabled.")
        print(f"   ℹ️ To enable MongoDB, ensure it's running on {os.getenv('MONGODB_URL', 'mongodb://localhost:27017')}")
        _client = None
        _db = None
        _connection_error = error_msg


async def disconnect_db():
    """Disconnect from MongoDB."""
    global _client
    if _client:
        _client.close()
        print("[DB] Disconnected from MongoDB")


def get_db():
    """
    Get database instance.
    
    Returns None if MongoDB is not connected.
    Check is_connected() before assuming database operations will work.
    """
    return _db


def is_connected() -> bool:
    """Check if database is connected."""
    return _db is not None


def get_connection_error() -> Optional[str]:
    """Get connection error message if connection failed."""
    return _connection_error


def get_collection(name: str):
    """
    Get a collection by name.
    
    Returns None if database is not connected.
    Caller should check is_connected() first or handle None case.
    """
    if _db is None:
        if _connection_error:
            print(f"⚠️ [DB] Cannot get collection '{name}': {_connection_error}")
        return None
    return _db[name]
