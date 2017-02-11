import aiofiles
import discord
import logging
import os
import pickle
import re
from typing import Any

logger = logging.getLogger(__name__)


async def pickle_dump(obj: Any, file: os.PathLike):
    """
    Async pickle dump.
    """
    byte = pickle.dumps(obj)
    async with aiofiles.open(filename, "wb") as f:
        await f.write(byte)


async def pickle_load(filename: os.PathLike) -> Any:
    """
    Async pickle load.
    """
    async with aiofiles.open(filename, "rb") as f:
        byte = await f.read()

    return pickle.loads(byte)
