"""
Thin wrapper module that exposes connect_db / disconnect_db for tests.
Tests import:

    from app.db import connect_db, disconnect_db

GenCode Studio backend models step should generate an identical structure
when creating real projects.
"""

import asyncio
from typing import Optional

from .database import init_db

_db_initialized: bool = False


async def connect_db() -> None:
    global _db_initialized
    if not _db_initialized:
        await init_db()
        _db_initialized = True


async def disconnect_db() -> None:
    # In simple examples we don't close the client explicitly.
    # Real projects may want to call client.close().
    await asyncio.sleep(0)
