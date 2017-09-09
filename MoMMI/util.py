import os
import pickle
from typing import Any
import aiofiles


async def pickle_dump(obj: Any, filename: os.PathLike):
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
