import aiofiles
import asyncio
import logging
import os
import pickle
from collections import defaultdict
from discord import Server, Channel, Member
from typing import Dict, Any, List, DefaultDict, TYPE_CHECKING, TypeVar, Optional, Type
from pathlib import Path

logger = logging.getLogger()
T = TypeVar(Any)


class MServer(object):
    """
    Represents extra metadata for servers, such as config overrides and data stores.
    It's like a context for MoMMI.
    """

    if TYPE_CHECKING:
        from .master import MoMMI

    def __init__(self, server: Server, master: "MoMMI"):
        from .permissions import bantypes
        from .modules import MModule
        from .commands import MCommand

        # The TOML data from the config file, directly.
        self.config = {}  # type: Dict[str, Any]

        # The server snowflake ID.
        self.id = int(server.id)  # type: int

        # Enabled modules for this Server.
        self.modules = {}  # type: Dict[str, MModule]

        # Data storage for modules.
        # As long as the data pickles fine it can be stored.
        self.storage = {}  # type: Dict[str, Any]

        # While we *could* get roles from the config directly, this is sort of easier.
        # String name = snowflake ID.
        self.roles = {}  # type: Dict[str, int]

        # Dict of snowflake ID to the ban types for this shitter.
        self.bans = defaultdict(list)  # type: DefaultDict[int, List[bantypes]]

        # Dict of snowflake ID = MChannel
        self.channels = {}  # type: DefaultDict[int, List[bantypes]]

        self.master = master  # type: MoMMI

        # Name in the config file, not the actual guild name.
        self.name = ""  # type: str

        for channel in self.get_server().channels:
            self.add_channel(channel)

    # Gets passed a section of servers.toml and loads it.
    def load_server_config(self, config: Dict[str, Any]):
        self.config = config
        self.name = config["name"]
        # logger.debug(f"Got name {self.name}")

        self.roles = self.config.get("roles", {})

    async def load_data_storages(self, source: Path):
        await asyncio.gather(*[self.load_single_storage(m, source.joinpath(m)) for m in os.listdir(source)])

    async def load_single_storage(self, module: str, file: Path):
        data: Any
        async with open(file, "rb") as f:
            data = pickle.loads(await f.read())

        # Handle special cases.
        if module[0] == "_":
            if module == "_bans":
                self.bans = data

        else:
            self.storage[module] = data

    def get_channel(self, id: int):
        """
        Get MChannel by Discord snowflake ID.
        """
        return self.channels[id]

    def get_server(self) -> Server:
        return self.master.client.get_server(str(self.id))

    def add_channel(self, channel: Channel):
        self.channels[int(channel.id)] = MChannel(self, channel)

    def remove_channel(self, channel: Channel):
        del self.channels[int(channel.id)]


class MChannel(object):
    """
    Represents extra context for a channel.
    This is the type most commands will be interacting with.
    Handles everything from roles to sending messages.
    """

    def __init__(self, server: MServer, channel: Channel):
        self.id = int(channel.id)  # type: int
        self.server = server  # type: MServer

    def get_channel(self) -> Channel:
        """
        Gets our discord.Channel.
        The channel instance is not permanently stored for reasons.
        """
        return self.server.master.client.get_channel(str(self.id))

    async def send(self, message: str):
        """
        Send a message on this channel.
        """
        channel = self.get_channel()
        await self.server.master.client.send_message(channel, message)

    def module_config(self, module: str, key: str, default: Optional[T] = None) -> T:
        from .config import get_nested_dict_value
        """
        Get global (module level) config data. That means it's from `modules.toml`
        """

        mod = self.server.master.get_module(module)
        ret = get_nested_dict_value(mod.config, key)
        if ret is None:
            return default

        return ret

    def main_config(self, key: str, default: Optional[T] = None) -> T:
        return self.server.master.config.get_main(key, default)

    def isrole(self, member: Member, role: str) -> bool:
        if role == "owner":
            owner_id = self.main_config("bot.owner")
            logger.debug(f"{owner_id}, {member.id}")
            return int(member.id) == owner_id

        if role not in self.server.roles:
            return False

        id = self.server.roles[role]

        for role in member.roles:
            if int(role.id) == id:
                return True

        return False

    def iter_handlers(self, type: Type[T]):
        for module in self.server.modules.values():
            yield from filter(lambda x: isinstance(x, type), module.handlers.values())
