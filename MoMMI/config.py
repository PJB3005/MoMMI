import asyncio
import logging
from typing import Dict, Any, TypeVar, Optional, cast
from pathlib import Path
import aiofiles
import toml


logger = logging.getLogger("config")
T = TypeVar("T")


class ConfigManager(object):
    def __init__(self) -> None:
        self.path: Optional[Path] = None

        self.main: Dict[str, Any] = {}
        self.modules: Dict[str, Any] = {}
        self.servers: Dict[str, Any] = {}

    def get_main(self, key: str, default: Optional[T] = None) -> T:
        """
        Get a config for the *main* config file. That is `main.toml`.
        """
        out = cast(Optional[T], get_nested_dict_value(self.main, key))
        if out is not None:
            return out

        if default is None:
            raise ValueError("Unable to find key and no default specified.")

        return default

    def get_module(self, key: str, default: Optional[T] = None) -> T:
        out = cast(Optional[T], get_nested_dict_value(self.modules, key))
        if out is not None:
            return out

        if default is None:
            raise ValueError("Unable to find key and no default specified.")

        return default

    async def load_from(self, path: Path) -> None:
        self.path = path
        await asyncio.gather(
            self.load_main(path),
            self.load_servers(path),
            self.load_modules(path)
        )

    async def load_main(self, path: Path) -> None:
        async with aiofiles.open(path.joinpath("main.toml"), "r") as f:
            self.main = dict(toml.loads(await f.read()))

    async def load_servers(self, path: Path) -> None:
        async with aiofiles.open(path.joinpath("servers.toml"), "r") as f:
            self.servers = dict(toml.loads(await f.read()))

    async def load_modules(self, path: Path) -> None:
        async with aiofiles.open(path.joinpath("modules.toml"), "r") as f:
            self.modules = dict(toml.loads(await f.read()))


def get_nested_dict_value(dictionary: Dict[str, Any], key: str) -> Any:
    tree = key.split(".")

    current = dictionary
    for node in tree:
        if isinstance(current, dict):
            if node in current:
                current = current[node]

            else:
                # Trying to access a nonexistant key is a None.
                return None

    return current


class ConfigError(Exception):
    """
    An exception caused by broken configuration files.
    """
    pass
