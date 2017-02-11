# THAT'S IT FUCK GLOBALS!
import asyncio
import discord
import importlib
import logging
import os
import re
import signal
from pathlib import Path
from typing import List, Dict, Tuple
from .commands import MCommand
from .config import ConfigManager
from .modules import MModule
from .server import MServer

logger = logging.getLogger()

# TODO: Reorganize this.
# All of it.
# Dear god.
class MoMMI(object):
    def __init__(self):
        self.config: ConfigManager = ConfigManager()
        self.modules: Dict[str, MModule] = {}
        self.servers: Dict[int, MServer] = {}
        self.servers_name: Dict[str, MServer] = {}
        # We do all init as soon as discord.py is ready,
        # so we need to prevent double init.
        self.initialized: bool = False
        self.client: discord.Client = discord.Client()

        # Find all on_xxx attributes and register them to the client.
        for x in (getattr(self, x) for x in dir(self) if x.startswith("on_")):
            self.client.event(x)

    def start(self, configdir: Path, storagedir: Path):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.config.load_from(configdir))

        if not self.config.get_main("bot.token"):
            logger.critical("Discord auth token is unset, aborting.")
            exit(1)

        logger.info("Starting client.")
        self.client.run(self.config.get_main("bot.token"))

    async def on_ready(self):
        if self.initialized:
            logger.debug("on_ready called again, ignoring.")
            return

        self.register_signals()

        logger.info(f"Logged in as {self.client.user.name} ({self.client.user.id})")
        logger.info("Connected servers:")

        MCommand.prefix_re = re.compile(rf"^<@\!?{self.client.user.id}>\s*")

        tasks = []

        for server in self.client.servers:
            logger.info(f"  {server.name}")
            tasks.append(self.add_server(server))

        await asyncio.gather(*tasks)

        await self.reload_modules()
        logger.info(f"Loaded {len(self.modules)} modules.")
        logger.info("Initializations complete, *buzz*!")
        self.initialized = True

    async def detect_modules(self) -> List[str]:
        out = []
        path = Path("MoMMI").joinpath("Modules")
        for dirpath, dirnames, filenames in os.walk(path):
            if "__pycache__" in dirnames:
                dirnames.remove("__pycache__")

            dirpath = Path(dirpath)

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

    async def reload_modules(self):
        newmodules = await self.detect_modules()
        todrop = []
        for name, module in self.modules.items():
            if module.loaded:
                if hasattr(module.module, "unload"):
                    try:
                        await module.module.unload()
                    except:
                        logger.exception(f"Hit an exception while unloading module {name}.")

            if name not in newmodules:
                logger.debug(f"Dropping removed module {name}.")
                todrop.append(module)
                continue

            newmodules.remove(name)
            try:
                importlib.reload(module.module)

            except:
                logger.exception(f"Hit an exception while reloading module {name}.")
                todrop.append(module)
                continue

            if hasattr(module.module, "load"):
                try:
                    await module.module.load()

                except:
                    logger.exception(f"Hit an exception while load()ing module {name}.")

            module.loaded = True

        # Loops over NEW modules. Because we can't just reload them.
        for name in newmodules:
            newmod = MModule(name)
            self.modules[name] = newmod
            # Get module name without the MoMMI.Modules for figuring out config.
            # Config also needs to be loaded into the MModule before the import is done.
            shortname = name[len("MoMMI.Modules")+1:]
            if shortname in self.config.modules:
                await newmod.load_config(self.config.modules[shortname])

            try:
                mod = importlib.import_module(name)
            except:
                logger.exception(f"Hit an exception while loading module {name}.")
                # Alas it was not meant to be.
                del self.modules[name]
                continue

            newmod.module = mod

            if hasattr(mod, "load"):
                try:
                    await mod.load()
                except:
                    logger.exception(f"Hit an exception while load()ing module {name}.")

            newmod.loaded = True
            for server in self.servers.values():
                server.modules[name] = newmod
            logger.info(f"Successfully loaded module {name}.")

    def register_command(self, command: MCommand):
        module = self.modules[command.module]
        module.commands[command.name] = command

    async def on_message(self, message: discord.Message):
        if not self.initialized:
            return

        server = self.get_server(int(message.server.id))
        channel = server.get_channel(int(message.channel.id))

        for module in server.modules.values():
            for command in module.commands.values():
                await command.try_execute(channel, message)

    def get_server(self, id: int) -> MServer:
        return self.servers[id]

    async def on_server_join(self, server: discord.Server):
        logger.info(f"Joined new server {server.name}.")
        await self.add_server(server)

    async def add_server(self, server: discord.Server):
        logger.debug(f"Adding server {server.name}.")
        new = self.servers[int(server.id)] = MServer(server, self)
        new.modules = self.modules.copy()

        # TODO: Figure out a better way for this.
        cfg = None
        for serverconfig in self.config.servers["servers"]:
            if serverconfig["id"] == int(new.id):
                cfg = serverconfig
                break

        if not cfg:
            logger.warning(f"No configuration present for server {server.name} ({server.id})!")

        new.load_server_config(cfg)


    async def on_server_remove(self, server: discord.Server):
        logger.info(f"Left server {server.name}.")
        await self.remove_server(server)

    async def remove_server(self, server: discord.Server):
        logger.debug(f"Removing server {server.name}")
        # TODO: this probably won't GC correctly, due to circular references.
        # So technically this memleaks, but I don't give a damn because
        # leaving servers is so rare.

        mserver = get_server(int(server.id))
        del self.servers_name[mserver.name]
        del self.servers[mserver.id]

    async def shutdown(self):
        logger.info("Shutting down!")
        tasks = [module.unload() for module in self.modules if hasattr(module, "unload")]
        await asyncio.gather(*tasks)

        await self.client.logout()

    def handle_signal(self):
        asyncio.ensure_future(self.shutdown(), loop=self.client.loop)

    def register_signals(self):
        self.client.loop.add_signal_handler(signal.SIGTERM, self.handle_signal)
        self.client.loop.add_signal_handler(signal.SIGINT, self.handle_signal)

    def get_module(self, name: str) -> MModule:
        return self.modules[name]

master: MoMMI = MoMMI()
