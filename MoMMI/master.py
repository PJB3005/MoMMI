# THAT'S IT FUCK GLOBALS!
import asyncio
import importlib
import logging
import os
import re
import signal
from pathlib import Path
from typing import List, Dict, Any, Optional, Iterable, TYPE_CHECKING
import discord
from MoMMI.config import ConfigManager
from MoMMI.module import MModule
from MoMMI.types import SnowflakeID

LOGGER = logging.getLogger("master")
CHAT_LOGGER = logging.getLogger("chat")

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
        self.client = discord.Client()
        self.commloop: Optional[commloop] = None
        self.storagedir: Optional[Path] = None

        # Find all on_xxx attributes and register them to the client.
        for member in dir(self):
            if member.startswith("on_"):
                self.client.event(getattr(self, member))

    def start(self, configdir: Path, storagedir: Path) -> None:
        self.storagedir = storagedir
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(self.config.load_from(configdir))
        except:
            LOGGER.exception("$REDError in the config files")
            LOGGER.critical("$REDCannot start MoMMI due to broken config files.")
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

        self.register_signals()

        self.commloop = commloop(self)
        await self.commloop.start(self.client.loop)

        LOGGER.info(f"$BLUELogged in as $WHITE{self.client.user.name}$RESET ($YELLOW{self.client.user.id}$RESET)")

        MCommand.prefix_re = re.compile(rf"^<@\!?{self.client.user.id}>\s*")

        await self.reload_modules()
        LOGGER.info(f"$BLUELoaded $WHITE{len(self.modules)}$BLUE modules.")

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

    async def reload_modules(self) -> None:
        self.reloading_modules = True
        newmodules = await self.detect_modules()
        todrop = []
        for name, module in self.modules.items():
            if module.loaded:
                if hasattr(module.module, "unload"):
                    try:
                        await module.module.unload(self.client.loop)
                    except:
                        LOGGER.exception(f"Hit an exception while unloading module {name}.")

            if name not in newmodules:
                LOGGER.debug(f"Dropping removed module {name}.")
                if hasattr(module.module, "shutdown"):
                    try:
                        await module.module.shutdown(self.client.loop)
                    except:
                        LOGGER.exception(f"Hit an exception while shutting down module {name}.")

                todrop.append(module)
                continue

            newmodules.remove(name)
            module.handlers = {}
            try:
                importlib.reload(module.module)

            except:
                LOGGER.exception(f"Hit an exception while reloading module {name}.")
                todrop.append(module)
                continue

            if hasattr(module.module, "load"):
                try:
                    await module.module.load(self.client.loop)

                except:
                    LOGGER.exception(f"Hit an exception while load()ing module {name}.")

            module.loaded = True

        # Loops over NEW modules. Because we can't just reload them.
        for name in newmodules:
            newmod = MModule(name)
            self.modules[name] = newmod

            try:
                mod = importlib.import_module(name)
            except:
                LOGGER.exception(f"Hit an exception while loading module {name}.")
                # Alas it was not meant to be.
                del self.modules[name]
                continue

            newmod.module = mod

            if hasattr(mod, "load"):
                try:
                    await mod.load(self.client.loop) # type: ignore
                except:
                    LOGGER.exception(f"Hit an exception while load()ing module {name}.")

            newmod.loaded = True
            for server in self.servers.values():
                server.modules[name] = newmod
            LOGGER.info(f"$BLUESuccessfully loaded module $WHITE{name}$BLUE.")

        for module in todrop:
            for server in self.servers.values():
                if module.name in server.modules:
                    del server.modules[module.name]

            del self.modules[module.name]

        self.reloading_modules = False

        for handler in self.temp_module_handlers:
            try:
                self.register_handler(handler)

            except:
                LOGGER.exception(f"Exception while registering handler {handler}!")

    def register_handler(self, handler: "MHandler") -> None:
        if self.reloading_modules:
            self.temp_module_handlers.append(handler)
            return

        module = self.get_module(handler.module)
        module.handlers[handler.name] = handler

    async def on_message(self, message: discord.Message) -> None:
        from MoMMI.commands import MCommand
        if not self.initialized:
            return

        # Ignore IRC messages.
        if message.author.id == self.client.user.id and message.content.startswith("\u200B**IRC:**"):
            return

        CHAT_LOGGER.info(f"({message.channel.name}) {message.author.name}: {message.content}")

        server = self.get_server(SnowflakeID(message.server.id))
        channel = server.get_channel(SnowflakeID(message.channel.id))

        for command in channel.iter_handlers(MCommand):
            await command.try_execute(channel, message)

    def get_server(self, serverid: SnowflakeID) -> "MServer":
        return self.servers[serverid]

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
            LOGGER.error(f"No configuration present for server {server.name} ({server.id})!")
            return

        new.load_server_config(cfg)
        data_path: Path = self.storagedir.joinpath(new.name)
        if not data_path.exists():
            LOGGER.debug(f"Data directory for server {new.name} does not exist, creating.")
            data_path.mkdir(parents=True)
        elif not data_path.is_dir():
            LOGGER.error(f"Data storage directory for {new.name} exists but is not a file!")
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
        if self.commloop:
            LOGGER.debug("Closing commloop.")
            await self.commloop.stop()

        await asyncio.gather(*(server.save_all_storages() for server in self.servers.values()))

        tasks = [module.module.unload(self.client.loop) for module in self.modules.values() if hasattr(module.module, "unload")]
        await asyncio.gather(*tasks)

        tasks = [module.module.shutdown(self.client.loop) for module in self.modules.values() if hasattr(module.module, "shutdown")]
        await asyncio.gather(*tasks)

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

    async def on_channel_delete(self, channel: discord.Channel):
        if channel.is_private:
            return

        server_id = SnowflakeID(channel.server.id)
        mserver = self.get_server(server_id)
        mserver.remove_channel(channel)

    async def on_channel_create(self, channel: discord.Channel):
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

master = MoMMI()
