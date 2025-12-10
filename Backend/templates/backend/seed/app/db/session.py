from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.core.config import settings
from typing import List
import importlib
import pkgutil
import inspect
from beanie import Document

# Global client
client: AsyncIOMotorClient = None

def get_all_document_models() -> List[str]:
    """
    Auto-discover all Beanie Document models in app.models package.
    Returns a list of model classes or path strings.
    """
    try:
        import app.models as models_pkg
        document_models = []
        
        # Iterate over all modules in app.models
        path = models_pkg.__path__
        prefix = models_pkg.__name__ + "."
        
        for _, name, _ in pkgutil.iter_modules(path, prefix):
            module = importlib.import_module(name)
            for _, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, Document) and obj != Document:
                    document_models.append(obj)
                    
        return document_models
    except ImportError:
        # If models package doesn't exist yet (early init), return empty
        return []

async def init_db():
    """Initialize MongoDB connection and Beanie ODM."""
    global client
    client = AsyncIOMotorClient(settings.MONGO_URL)
    
    # Auto-discover models so we don't have to manually register them in main.py
    # models = get_all_document_models() # Auto-discovery can be tricky, let's Stick to explicit for now if safer
    # For robust seed, we will let the Agent or Integrator handle model registration list if dynamic
    # Or, we can use a string path list if supported
    
    # For now, we will Initialize with NO models, and rely on lifespan to re-init with models
    # OR better: The Integrator script can inject model imports here.
    
    pass 

async def connect_to_mongo():
    global client
    client = AsyncIOMotorClient(settings.MONGO_URL)
    # Beanie initialization happens in main.py lifespan or specific init function
