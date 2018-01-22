
import asyncio
import logging
import pickle
from typing import Dict, Any, TypeVar, Optional, Union
from pathlib import Path
import aiofiles
from discord import Server, Channel, Member, Role
from MoMMI.types import SnowflakeID, MIdentifier
from MoMMI.master import MoMMI
from MoMMI.module import MModule
from MoMMI.role import MRoleType
from MoMMI.channel import MChannel

logger = logging.getLogger(__name__)
T = TypeVar("T")


class MServer(object):
    """
    Represents extra metadata for servers, such as config overrides and data stores.
    It's like a context for MoMMI.
    """

    def __init__(self, server: Server, master: MoMMI) -> None:
        # The TOML data from the config file, directly.
        self.config: Dict[str, Any] = {}

        # The server snowflake ID.
        self.id: SnowflakeID = SnowflakeID(server.id)

        # Enabled modules for this Server.
        self.modules: Dict[str, MModule] = {}

        # Data storage for modules.
        # As long as the data pickles fine it can be stored.
        self.storage: Dict[str, Any] = {}

        # Cache is persistent through reloads, but not through restarts.
        self.cache: Dict[str, Any] = {}
        self.roles: Dict[MRoleType, SnowflakeID] = {}
        self.channels: Dict[SnowflakeID, MChannel] = {}
        self.channels_name: Dict[str, MChannel] = {}
        self.master: MoMMI = master

        # Name in the config file, not the actual guild name.
        self.name: str = ""

        self.storagedir: Optional[Path] = None

        for channel in self.get_server().channels:
            self.add_channel(channel)

    @property
    def visible_name(self) -> str:
        """
        The name that is displayed to users in the server list and such.
        """
        return self.get_server().name

    @property
    def discordpy_server(self) -> Server:
        """
        The Discord.py server instance used internally.
        """
        return self.get_server()

    def get_discordpy_role(self, identifier: SnowflakeID) -> Role:
        for role in self.discordpy_server.roles:
            if int(role.id) == identifier:
                return role

        raise KeyError(identifier)

    # Gets passed a section of servers.toml and loads it.
    def load_server_config(self, config: Dict[str, Any]) -> None:
        self.config = config
        self.name = config["name"]

        for rolename, snowflake in self.config.get("roles", {}).items():
            self.roles[MRoleType[rolename]] = snowflake

        self.roles = self.config.get("roles", {})
        self.init_channel_names()

    async def load_data_storages(self, source: Path) -> None:
        self.storagedir = source
        await asyncio.gather(*(self.load_single_storage(m.name, m) for m in source.iterdir()))

    async def load_single_storage(self, module: str, file: Path) -> None:
        data: Any
        async with aiofiles.open(file, "rb") as f:
            data = pickle.loads(await f.read())

        self.storage[module] = data

    def get_channel(self, snowflake: MIdentifier) -> MChannel:
        """
        Get MChannel by Discord snowflake ID OR tabled ID.
        """
        if isinstance(snowflake, SnowflakeID):
            return self.channels[snowflake]

        elif isinstance(snowflake, str):
            return self.channels_name[snowflake]

        raise TypeError()

    def get_server(self) -> Server:
        return self.master.client.get_server(str(self.id))

    def add_channel(self, channel: Channel) -> None:
        name = None
        for k, v in self.config.get("channels", {}).items():
            if int(v) == channel.id:
                name = k
                break

        channel = MChannel(self, channel, name)
        self.channels[SnowflakeID(channel.id)] = channel
        if name:
            self.channels_name[name] = channel

    def init_channel_names(self) -> None:
        for k, v in self.config.get("channels", {}).items():
            if SnowflakeID(v) in self.channels:
                self.channels_name[k] = self.channels[SnowflakeID(v)]

    def remove_channel(self, channel: Channel) -> None:
        channel = self.get_channel(SnowflakeID(channel.id))
        if channel.internal_name:
            del self.channels_name[channel.internal_name]

        del self.channels[SnowflakeID(channel.id)]

    def get_storage(self, name: str) -> Any:
        return self.storage[name]

    def set_storage(self, name: str, value: Any) -> None:
        self.storage[name] = value

    def has_storage(self, name: str) -> bool:
        return name in self.storage

    async def set_storage_save(self, name: str, value: Any):
        self.set_storage(name, value)
        await self.save_storage(name)

    async def save_storage(self, name: str):
        if self.storagedir is None:
            raise RuntimeError("Storage dir has not been set. Cannot save storages!")

        storage = self.get_storage(name)
        data = pickle.dumps(storage)
        async with aiofiles.open(self.storagedir.joinpath(name), "wb") as f:
            await f.write(data)

    async def save_all_storages(self) -> None:
        logger.debug(f"Saving storage for server {self.name}!")
        await asyncio.gather(
            *(self.save_storage(x) for x in self.storage)
        )

    def get_cache(self, name: str) -> Any:
        return self.cache[name]

    def set_cache(self, name: str, value: Any) -> None:
        self.cache[name] = value

    def get_member(self, snowflake: SnowflakeID) -> Member:
        return self.get_server().get_member(str(snowflake))
