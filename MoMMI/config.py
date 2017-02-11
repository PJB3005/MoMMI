import aiofiles
import asyncio
import logging
import toml
from enum import Enum
from typing import Dict, Any, TypeVar, Optional
from pathlib import Path

logger = logging.getLogger("config")
T = TypeVar(Any)


class ConfigManager(object):
    def __init__(self):
        self.path: Path = None

        self.main: Dict[str, Any] = None
        self.modules: Dict[str, Any] = None
        self.servers: Dict[str, Any] = None

    def get_main(self, key: str, default: Optional[T] = None) -> T:
        """
        Get a config for the *main* config file. That is `main.toml`.
        """

        out: T = get_nested_dict_value(self.main, key)
        if out is None and default is not None:
            out = default

        return out

    async def load_from(self, path: Path):
        self.path = path
        await asyncio.gather(
            self.load_main(path),
            self.load_servers(path),
            self.load_modules(path)
        )

    # I absolutely cannot think of a better way.
    async def load_main(self, path: Path):
        async with aiofiles.open(path.joinpath("main.toml"), "r") as f:
            self.main = toml.loads(await f.read())

    async def load_servers(self, path: Path):
        async with aiofiles.open(path.joinpath("servers.toml"), "r") as f:
            self.servers = toml.loads(await f.read())

    async def load_modules(self, path: Path):
        async with aiofiles.open(path.joinpath("modules.toml"), "r") as f:
            self.modules = toml.loads(await f.read())

# I really can't think of a better name.
def get_nested_dict_value(dictionary: Dict[str, Any], key: str) -> Any:
    tree = key.split(".")

    current = dictionary
    for node in tree:
        if type(current) == dict:
            if node in current:
                current = current[node]

            else:
                # Trying to access a nonexistant key is a None.
                return None

    return current
