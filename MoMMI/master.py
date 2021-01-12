# THAT'S IT FUCK GLOBALS!
import asyncio
import importlib
import logging
import os
import pickle
import re
import signal
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Iterable, TYPE_CHECKING, Union, Type, TypeVar
import aiofiles
import discord
from MoMMI.config import ConfigManager
from MoMMI.module import MModule
from MoMMI.types import SnowflakeID

LOGGER: logging.Logger = logging.getLogger("master")
CHAT_LOGGER: logging.Logger = logging.getLogger("chat")

T = TypeVar("T")

# TODO: Reorganize this.
# All of it.
# Dear god.


class MoMMI(object):
    if TYPE_CHECKING:
        from MoMMI.handler import MHandler
        from MoMMI.server import MServer
        from MoMMI.channel import MChannel

    def __init__(self) -> None:
        from MoMMI.commloop import commloop
        from MoMMI.handler import MHandler
        from MoMMI.server import MServer

        self.config = ConfigManager()
        self.modules: Dict[str, MModule] = {}
        # If a handler attempts to register to an unknown module,
        # it gets temporarily stored in here,
        # to prevent race conditions related to load order.
        self.temp_module_handlers: List[MHandler] = []
        # True if we're reloading modules right now.
        self.reloading_modules = False
        self.servers: Dict[SnowflakeID, MServer] = {}
        self.servers_name: Dict[str, MServer] = {}
        self.cache: Dict[str, Any] = {}
        # We do all init as soon as discord.py is ready,
        # so we need to prevent double init.
        self.initialized = False
        self.shutting_down = False
        self.client = discord.Client()
        self.commloop: Optional[commloop] = None
        self.storagedir: Optional[Path] = None
        self.global_storagedir: Optional[Path] = None
        self.global_storage: Dict[str, Any] = {}

        # Find all on_xxx attributes and register them to the client.
        for member in dir(self):
            if member.startswith("on_"):
                self.client.event(getattr(self, member))

    def start(self, configdir: Path, storagedir: Path) -> None:
        self.storagedir = storagedir
        self.global_storagedir = storagedir/"__global__"
        self.global_storagedir.mkdir(parents=True, exist_ok=True)
        loop = asyncio.get_event_loop()

        try:
            loop.run_until_complete(self.config.load_from(configdir))

        except:
            LOGGER.exception("$REDError in the config files")
            LOGGER.critical(
                "$REDCannot start MoMMI due to broken config files.")
            exit(1)

        if not self.config.get_main("bot.token"):
            LOGGER.critical("$REDDiscord auth token is unset, aborting.")
            exit(1)

        LOGGER.info("$GREENMoMMI starting!")
        self.client.run(self.config.get_main("bot.token"))

    async def on_ready(self) -> None:
        from MoMMI.commloop import commloop
        from MoMMI.commands import MCommand
        if self.initialized:
            LOGGER.debug("on_ready called again, ignoring.")
            return

        if sys.platform != "win32":
            self.register_signals()

        self.commloop = commloop(self, self.client.loop)
        await self.commloop.start()

        LOGGER.info(
            f"$BLUELogged in as $WHITE{self.client.user.name}$RESET ($YELLOW{self.client.user.id}$RESET)")

        MCommand.prefix_re = re.compile(rf"^<@\!?{self.client.user.id}>\s*")

        await self.reload_modules()
        LOGGER.info(f"$BLUELoaded $WHITE{len(self.modules)}$BLUE modules.")

        await self.load_all_global_storages()
        LOGGER.info("Loaded global storages.")

        tasks = []
        LOGGER.info("$BLUEConnected servers:")
        for server in self.client.servers:
            LOGGER.info(f"  $WHITE{server.name}")
            tasks.append(self.add_server(server))

        await asyncio.gather(*tasks)

        LOGGER.info("$GREENInitializations complete, *buzz*!")
        self.initialized = True

    async def detect_modules(self) -> List[str]:
        out = []
        path = Path("MoMMI").joinpath("Modules")
        for dirpath_, dirnames, filenames in os.walk(path):
            if "__pycache__" in dirnames:
                dirnames.remove("__pycache__")

            if ".mypy_cache" in dirnames:
                dirnames.remove(".mypy_cache")

            dirpath = Path(dirpath_)

            for filename in filenames:
                filepath = dirpath.joinpath(filename)
                if filepath.name == "__init__.py":
                    continue

                # Crappy hack to make module paths we can import with importlib.
                relativepath = filepath.relative_to(path)
                module_name = relativepath.as_posix()[:-3].replace("/", ".")
                module_name = f"MoMMI.Modules.{module_name}"
                out.append(module_name)

        return out

    async def reload_modules(self) -> bool:
        """
        Returns True if there were any errors.
        """
        self.reloading_modules = True
        newmodules = await self.detect_modules()
        todrop = []
        toload = []

        # Logs!
        errors = False

        for name, module in self.modules.items():
            if module.loaded:
                if hasattr(module.module, "unload"):
                    try:
                        await module.module.unload(self.client.loop)
                    except:
                        LOGGER.exception(
                            f"Hit an exception while unloading module {name}.")
                        errors = True

            if name not in newmodules:
                LOGGER.debug(f"Dropping removed module {name}.")
                if hasattr(module.module, "shutdown"):
                    try:
                        await module.module.shutdown(self.client.loop)
                    except:
                        LOGGER.exception(
                            f"Hit an exception while shutting down module {name}.")
                        errors = True

                todrop.append(module)
                continue

            newmodules.remove(name)
            module.handlers = {}
            try:
                importlib.reload(module.module)

            except:
                LOGGER.exception(
                    f"Hit an exception while reloading module {name}.")
                todrop.append(module)
                errors = True
                continue

            toload.append(module)
            module.loaded = True

        # Loops over NEW modules. Because we can't just reload them.
        for name in newmodules:
            newmod = MModule(name)
            self.modules[name] = newmod

            try:
                mod = importlib.import_module(name)
            except:
                LOGGER.exception(
                    f"Hit an exception while loading module {name}.")
                # Alas it was not meant to be.
                del self.modules[name]
                errors = True
                continue

            newmod.module = mod
            toload.append(newmod)

            newmod.loaded = True
            for server in self.servers.values():
                server.modules[name] = newmod
            #LOGGER.info(f"$BLUESuccessfully loaded module $WHITE{name}$BLUE.")

        for module in toload:
            if hasattr(module.module, "load"):
                try:
                    await module.module.load(self.client.loop)

                except:
                    LOGGER.exception(
                        f"Hit an exception while load()ing module {module.name}.")
                    errors = True

        for module in todrop:
            for server in self.servers.values():
                if module.name in server.modules:
                    del server.modules[module.name]

            del self.modules[module.name]

        self.reloading_modules = False

        for handler in self.temp_module_handlers:
            try:
                if handler.module in self.modules:
                    self.register_handler(handler)

                else:
                    LOGGER.warning(f"Attempted to late-register for nonexistant module: {handler.module}/{handler.name}")

            except:
                LOGGER.exception(
                    f"Exception while registering handler {handler.module}/{handler.name}!")
                errors = True

        self.temp_module_handlers = []

        return errors

    def register_handler(self, handler: "MHandler") -> None:
        if self.reloading_modules:
            self.temp_module_handlers.append(handler)
            return

        if handler.name == "reminders":
            print("EYSSSSS")

        module = self.get_module(handler.module)
        module.handlers[handler.name] = handler

    async def on_message(self, message: discord.Message) -> None:
        from MoMMI.commands import MCommand
        from MoMMI.util import utcnow
        if not self.initialized or self.shutting_down:
            return

        # Ignore IRC messages.
        if message.author.id == self.client.user.id and message.content.startswith("\u200B**IRC:**"):
            return

        server = self.get_server(SnowflakeID(message.server.id))
        channel = server.get_channel(SnowflakeID(message.channel.id))

        logmsg = f"[{utcnow().isoformat()}]({server.name}/{message.channel.name}) {message.author.name}#{message.author.discriminator}: {message.content}"

        if message.attachments:
            logmsg += "[Attachments]"
            for attach in message.attachments:
                logmsg += " " + attach["url"]

        CHAT_LOGGER.info(logmsg)

        for command in channel.iter_handlers(MCommand):
            await command.try_execute(channel, message)

    async def on_reaction_add(self, reaction: discord.Reaction, member: discord.User) -> None:
        from MoMMI.commands import MReactionCommand
        from MoMMI.util import utcnow
        if not self.initialized or self.shutting_down:
            return

        server = self.get_server(SnowflakeID(reaction.message.server.id))
        channel = server.get_channel(SnowflakeID(reaction.message.channel.id))

        for command in channel.iter_handlers(MReactionCommand):
            await command.func(channel, reaction, member)

    async def on_message_delete(self, message: discord.Message) -> None:
        from MoMMI.commands import MDeleteCommand
        from MoMMI.util import utcnow
        if not self.initialized or self.shutting_down:
            return

        server = self.get_server(SnowflakeID(message.server.id))
        channel = server.get_channel(SnowflakeID(message.channel.id))

        for command in channel.iter_handlers(MDeleteCommand):
            await command.func(channel, message)     


    def get_server(self, serverid: Union[SnowflakeID, str]) -> "MServer":
        if isinstance(serverid, str):
            return self.servers_name[serverid]

        elif isinstance(serverid, SnowflakeID):
            return self.servers[serverid]

        raise TypeError("Server ID must be str or SnowflakeID")

    async def on_server_join(self, server: discord.Server) -> None:
        LOGGER.info(f"Joined new server {server.name}.")
        await self.add_server(server)

    async def add_server(self, server: discord.Server) -> None:
        from MoMMI.server import MServer
        if self.storagedir is None:
            raise RuntimeError("No storage dir specified!")

        LOGGER.debug(f"Adding server {server.name}.")
        new = self.servers[SnowflakeID(server.id)] = MServer(server, self)
        new.modules = self.modules.copy()

        # TODO: Figure out a better way for this.
        cfg = None
        for serverconfig in self.config.servers["servers"]:
            if SnowflakeID(serverconfig["id"]) == int(new.id):
                cfg = serverconfig
                break

        if not cfg:
            LOGGER.error(
                f"No configuration present for server {server.name} ({server.id})!")
            return

        new.load_server_config(cfg)
        if new in self.servers_name:
            LOGGER.error(
                f"Duplicate server name '{new.name}, {new.visible_name} <-> {self.servers_name[new.name].visible_name}'")
        else:
            self.servers_name[new.name] = new

        data_path: Path = self.storagedir.joinpath(new.name)
        if not data_path.exists():
            LOGGER.debug(
                f"Data directory for server {new.name} does not exist, creating.")
            data_path.mkdir(parents=True)
        elif not data_path.is_dir():
            LOGGER.error(
                f"Data storage directory for {new.name} exists but is not a file!")
        await new.load_data_storages(data_path)

    async def on_server_remove(self, server: discord.Server) -> None:
        LOGGER.info(f"Left server {server.name}.")
        await self.remove_server(server)

    async def remove_server(self, server: discord.Server) -> None:
        LOGGER.debug(f"Removing server {server.name}")
        # TODO: this probably won't GC correctly, due to circular references.
        # So technically this memleaks, but I don't give a damn because
        # leaving servers is so rare.

        mserver = self.get_server(SnowflakeID(server.id))
        del self.servers_name[mserver.name]
        del self.servers[mserver.id]

    async def shutdown(self) -> None:
        LOGGER.info("$REDShutting down!")
        self.shutting_down = True
        if self.commloop:
            LOGGER.debug("Closing commloop.")
            await self.commloop.stop()

        async def try_unload_module(module: MModule) -> None:
            try:
                if hasattr(module.module, "unload"):
                    await asyncio.wait_for(module.module.unload(self.client.loop), 5, loop=self.client.loop)
            except:
                LOGGER.exception(f"Exception while unloading module {module.name} for shutdown.")

        async def try_shutdown_module(module: MModule) -> None:
            try:
                if hasattr(module.module, "shutdown"):
                    await asyncio.wait_for(module.module.shutdown(self.client.loop), 5, loop=self.client.loop)
            except:
                LOGGER.exception(f"Exception while shutting down module {module.name} for shutdown.")

        tasks = [try_unload_module(module) for module in self.modules.values()]
        await asyncio.gather(*tasks)

        tasks = [try_shutdown_module(module) for module in self.modules.values()]
        await asyncio.gather(*tasks)

        await self.save_all_storage()

        LOGGER.info("Goodbye.")

        await self.client.logout()

    def handle_signal(self) -> None:
        asyncio.ensure_future(self.shutdown(), loop=self.client.loop)

    def register_signals(self) -> None:
        self.client.loop.add_signal_handler(signal.SIGTERM, self.handle_signal)
        self.client.loop.add_signal_handler(signal.SIGINT, self.handle_signal)

    def get_module(self, name: str) -> MModule:
        return self.modules[name]

    def iter_channels(self) -> Iterable["MChannel"]:
        """
        Iterate over all MChannels.
        """
        for server in self.servers.values():
            yield from server.channels.values()

    async def on_channel_delete(self, channel: discord.Channel) -> None:
        if channel.is_private:
            return

        server_id = SnowflakeID(channel.server.id)
        mserver = self.get_server(server_id)
        mserver.remove_channel(channel)

    async def on_channel_create(self, channel: discord.Channel) -> None:
        # TODO: support for PMs.
        # Probably longs ways off shit.
        LOGGER.debug(f"Got new channel! {channel.is_private}, {channel.id}")
        if channel.is_private:
            return

        server_id = SnowflakeID(channel.server.id)
        mserver = self.get_server(server_id)
        mserver.add_channel(channel)

    def set_cache(self, key: str, value: Any) -> None:
        self.cache[key] = value

    def get_cache(self, key: str) -> Any:
        return self.cache[key]

    def del_cache(self, key: str) -> None:
        del self.cache[key]

    def has_cache(self, key: str) -> bool:
        return key in self.cache

    def iter_global_handlers(self, handlertype: Type[T]) -> Iterable[T]:
        for module in self.modules.values():
            yield from (x for x in module.handlers.values() if isinstance(x, handlertype))

    async def save_all_storage(self) -> None:
        """
        Save all storages, including server and global storages.
        """
        await asyncio.gather(*(server.save_all_storages() for server in self.servers.values()))
        await self.save_all_global_storages()

    def get_global_storage(self, name: str) -> Any:
        """
        Fetch a GLOBAL storage.
        """
        return self.global_storage[name]

    def set_global_storage(self, name: str, value: Any) -> None:
        """
        Set a GLOBAL storage.
        """
        self.global_storage[name] = value

    def has_global_storage(self, name: str) -> bool:
        """
        Check whether a GLOBAL storage exists or not.
        """
        return name in self.global_storage

    async def save_global_storage(self, name: str) -> None:
        if self.global_storagedir is None:
            raise RuntimeError("Storage dir has not been set. Cannot save storages!")

        storage = self.get_global_storage(name)
        data = pickle.dumps(storage)
        async with aiofiles.open(self.global_storagedir/name, "wb") as f:
            await f.write(data)

    async def save_all_global_storages(self) -> None:
        for name in self.global_storage.keys():
            await self.save_global_storage(name)

    async def load_all_global_storages(self) -> None:
        if self.global_storagedir is None:
            raise RuntimeError("Storage dir has not been set. Cannot save storages!")

        await asyncio.gather(
            *(self.load_single_global_storage(m.name, m) for m in self.global_storagedir.iterdir())
        )

    async def load_single_global_storage(self, module: str, file: Path) -> None:
        data: Any
        try:
            async with aiofiles.open(file, "rb") as f:
                data = pickle.loads(await f.read())

            self.global_storage[module] = data

        except:
            LOGGER.exception(f"Failed to load global storage {module}")


master = MoMMI()
