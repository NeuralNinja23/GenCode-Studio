# backend/app/database.py
"""
Database Configuration - Seed Template

Initializes MongoDB connection with Motor (async driver) and Beanie ODM.
Automatically discovers Document models from app.models.

This file is PRE-SEEDED and works out of the box.
Derek only needs to write models.py - database.py auto-discovers them!
"""
import os
import inspect
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie, Document

# Database configuration from environment
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "gencode_app")


def _discover_document_models():
    """
    Automatically discover all Beanie Document subclasses from app.models.
    
    This eliminates the need for Derek to manually edit database.py.
    He just writes models.py and database.py auto-discovers them!
    """
    try:
        import app.models as models_module
        
        discovered = []
        for name, obj in inspect.getmembers(models_module, inspect.isclass):
            # Check if it's a Document subclass (but not Document itself)
            if issubclass(obj, Document) and obj is not Document:
                discovered.append(obj)
        
        return discovered
    except ImportError:
        # models.py doesn't exist yet - return empty list
        return []
    except Exception:
        # Any other error - return empty list
        return []


async def init_db():
    """
    Initialize database connection and Beanie ODM.
    
    Automatically discovers all Document models from app.models.
    Called from main.py lifespan context manager.
    """
    client = AsyncIOMotorClient(MONGO_URL)
    database = client[DB_NAME]
    
    # Auto-discover models (no manual editing required!)
    document_models = _discover_document_models()
    
    if document_models:
        await init_beanie(database=database, document_models=document_models)


async def close_db():
    """
    Close database connection.
    
    Motor handles cleanup automatically when the client closes.
    Called from main.py lifespan context manager.
    """
    pass  # Motor handles cleanup automatically


__all__ = ["init_db", "close_db", "MONGO_URL", "DB_NAME"]
