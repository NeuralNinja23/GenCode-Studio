from typing import Optional, Sequence, Type

import os
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie, Document

from .models import Task

client: Optional[AsyncIOMotorClient] = None


async def init_db() -> None:
    """
    Initialize MongoDB connection and Beanie document registration.
    This is the canonical pattern GenCode Studio agents should follow.
    """
    global client

    mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017/app_example")
    client = AsyncIOMotorClient(mongo_url)

    # Extract DB name from URL if present, otherwise use "app_example"
    db_name = mongo_url.split("/")[-1].split("?")[0] or "app_example"
    db = client[db_name]

    document_models: Sequence[Type[Document]] = [Task]
    await init_beanie(database=db, document_models=document_models)
