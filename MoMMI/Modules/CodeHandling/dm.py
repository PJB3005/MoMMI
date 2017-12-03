import aiofiles
import asyncio
import logging
import os
import time
import shutil
import sys
from distutils import spawn
from typing import Optional
from discord import Message, Embed
from MoMMI.Modules.CodeHandling.codehandling import codehandler, MCodeHandler, COLOR_COMPILE_FAIL, COLOR_RUN_SUCCESS, COLOR_RUN_FAIL
from MoMMI.channel import MChannel

logger = logging.getLogger(__name__)

@codehandler
class PythonCodeHandler(MCodeHandler):
    name = "DM"

    def __init__(self):
        super().__init__()

        self.languages = {"dm", "dreammaker", "byond"}

    async def make_project_folder(self) -> str:
        # Even if there's a folder already there, keep trying by adding a number to the end.
        offset = 0
        path = ""
        while True:
            path = os.path.join(os.getcwd(), "codeprojects", "{}-{}".format(int(time.time()), offset))
            try:
                os.makedirs(path)
            except FileExistsError:
                offset += 1
            else:
                break

        self.projectpath = path
        return path

    async def cleanup(self):
        # Can never be too safe with the equivalent of rm -r
        if not self.projectpath.startswith(os.path.join(os.getcwd(), "codeprojects")):
            logger.error("Failed to delete project subdirectory because the directory doesn't start with our cwd!")
            return

        shutil.rmtree(self.projectpath)

    async def make_project(self, code: str) -> str:
        code = code.replace("\r", "\n").replace("    ", "\t")
        lines = code.split("\n")

        output = ""

        if code.find("/proc/main") == -1:
            # Create a global variable and make it new the dummy type, so it instantly executes on world start.
            output = "var/a/b=new\n/a/New()\n"
            # Indent each line by one so we can put it as a datum's New().s
            for index, line in enumerate(lines):
                if not line.strip():
                    continue

                lines[index] = "\t" + line

            output += "\n".join(lines)

            output += "\nvar/c/d=new\n/c/New()\n\tshutdown()"

        else:
            output = f"\n{code}\nvar/ZZZZZ/zzzzz=new\nZZZZZ/New()\n\tmain()\n\tshutdown()"

        dmepath = os.path.join(self.projectpath, "code.dm")

        async with aiofiles.open(dmepath, "w") as f:
            await f.write(output)

        return dmepath

    async def execute(self, code: str, channel: MChannel, message: Message):
        path = await self.make_project_folder()

        await channel.server.master.client.add_reaction(message, "⌛")

        try:
            dmepath = await self.make_project(code)

            loop = asyncio.get_event_loop()
            logger.debug(type(loop))

            proc = await asyncio.create_subprocess_exec(self.dm_executable_path(channel), dmepath, stdout=asyncio.subprocess.PIPE)
            fail_reason = None
            try:
                await asyncio.wait_for(proc.wait(), timeout=30)
            except asyncio.TimeoutError:
                proc.kill()
                fail_reason = "**Compilation failed** due to **timeout** (30 seconds)."

            data = await proc.stdout.read()
            compile_log = data.decode("Windows-1252", "replace")

            if len(compile_log) > 900: # Discord max size of field is 1024 chars.
                log = compile_log[:900] + "\n<truncated due to size>"


            if fail_reason or proc.returncode:
                embed = Embed()
                embed.color = COLOR_COMPILE_FAIL
                embed.description = fail_reason or "**Compilation failed**"
                embed.add_field(name="Compiler Output", value=f"```{compile_log}```", inline=False)
                await channel.send(embed=embed)
                return

            proc = await asyncio.create_subprocess_exec(self.dd_executable_path(channel), dmepath + "b", "-invisible", "ultrasafe", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            try:
                await asyncio.wait_for(proc.wait(), timeout=30)
            except asyncio.TimeoutError:
                proc.kill()
                fail_reason = "**Execution failed** due to **timeout** (30 seconds)."

            data = await proc.stderr.read() + await proc.stdout.read()
            log = data.decode("Windows-1252", "replace")
            if len(log) > 900: # Discord max size of field is 1024 chars.
                log = log[:900] + "\n<truncated due to size>"


            embed = Embed()
            embed.add_field(name="Compiler Output", value=f"```{compile_log}```", inline=False)
            embed.add_field(name="Execution Output", value=f"```{log}```", inline=False)

            if fail_reason:
                embed.color = COLOR_RUN_FAIL
                embed.description = fail_reason

            else:
                embed.color = COLOR_RUN_SUCCESS

            await channel.send(embed=embed)

        except:
            await channel.send("Unknown error occured while executing code. Check the log files.")
            logger.exception("Exception while executing DM code")

        finally:
            await self.cleanup()

    def dm_executable_path(self, channel: MChannel) -> str:
        try:
            return channel.module_config("dm.dm_path")
        except: pass

        name = "DreamMaker"
        if sys.platform == "win32":
            name = "dm"

        path = self.byond_executable_path(name)

        if path is None:
            raise IOError("Unable to locate Dream Maker compiler binary. Please ensure that it is in your PATH, or set module config dm.dm_path.")

        return path

    def dd_executable_path(self, channel: MChannel) -> str:
        try:
            return channel.module_config("dm.dd_path")
        except: pass

        name = "DreamDaemon"
        is_windows = sys.platform == "win32"
        if sys.platform == "win32":
            name = "dreamdaemon"

        path = self.byond_executable_path(name)

        if path is None:
            raise IOError("Unable to locate Dream Daemon server binary. Please ensure that it is in your PATH, or set module config dm.dd_path.")

        return path

    def byond_executable_path(self, name: str) -> Optional[str]:
        path = spawn.find_executable(name)
        if path == None and sys.platform == "win32":
            # Attempt to look in %ProgramFiles% and %ProgramFiles(x86)% for BYOND.
            for path in (os.environ['ProgramFiles'], os.environ['ProgramFiles(x86)']):
                path = os.path.join(path, "BYOND", "bin", name + ".exe")

                if os.access(path, os.F_OK):
                    return path

        return None
