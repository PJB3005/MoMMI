import asyncio
import logging
import os
import time
import shutil
import sys
import aiofiles
import tempfile
import re
from distutils import spawn
from pathlib import Path
from random import choice
from string import ascii_lowercase
from typing import Optional, List
from discord import Message, Embed
from MoMMI.Modules.CodeHandling.codehandling import codehandler, MCodeHandler, COLOR_COMPILE_FAIL, COLOR_RUN_SUCCESS, COLOR_RUN_FAIL
from MoMMI.Modules.help import register_help
from MoMMI import MChannel

logger = logging.getLogger(__name__)

INCLUDE_REGEX = re.compile(r"include")


@codehandler
class DMCodeHandler(MCodeHandler):
    def __init__(self) -> None:
        super().__init__()

        self.name = "DM"
        self.languages = {"dm", "dreammaker", "byond"}

    async def make_project_folder(self) -> Path:
        # Even if there's a folder already there, keep trying by adding a number to the end.
        offset = 0
        path = Path()
        while True:
            path = Path.cwd()/"codeprojects"/"{}-{}".format(int(time.time()), offset)
            try:
                path.mkdir(parents=True, exist_ok=False)
            except FileExistsError:
                offset += 1
            else:
                break

        return path

    async def cleanup(self, path: Path) -> None:
        # Can never be too safe with the equivalent of rm -r
        try:
            path.relative_to(Path.cwd()/"codeprojects")
        except ValueError:
            logger.error(
                "Failed to delete project subdirectory because the directory doesn't start with our cwd!")
        else:
            shutil.rmtree(path)


    async def make_project(self, code: str, path: Path) -> Path:
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

            output += "\nvar/c/d=new\n/c/New()\n\teval(\"\")\n\tshutdown()"

        else:
            output = f"\n{code}\nvar/ZZZZZ/zzzzz=new\nZZZZZ/New()\n\tmain()\n\teval(\"\")\n\tshutdown()"

        # You may have noticed that eval("") call before the shutdown calls.
        # I absolutely have no god damn idea why, but DD reliably hangs for 20+ seconds before shutting down when running in a sandbox.
        # eval("") fixes this.
        # Literally what the fuck.

        dmepath = path/"code.dm"

        async with aiofiles.open(str(dmepath), "w") as f:
            await f.write(output)

        return dmepath

    async def execute(self, code: str, channel: MChannel, message: Message) -> None:
        if INCLUDE_REGEX.search(code) is not None:
            await channel.send("#include is not allowed for security reasons")
            return

        if sys.platform == "win32" or sys.platform == "cygwin":
            # Attempting to run DD command line on Windows just makes it open a window, run the code, hide the window
            # code then finishes, but the Window and as such process doesn't close
            # and on top of that it NEVER outputs to stdout.
            # Probably some code hacks can be done around this, I hope?
            # Fresh from #coderbus: -close and -log file should solve it!
            await channel.send("Unable to execute DM code, since this MoMMI is hosted on Windows.")
            return

        with tempfile.TemporaryDirectory() as dirname:
            path = Path(dirname)

            me = channel.server.get_server().me

            #asyncio.ensure_future(channel.server.master.client.add_reaction(message, "⌛"))

            try:
                firejail: List[str] = []
                firejail_name = ""

                # Use firejail if at all possible.
                if channel.module_config("dm.firejail", "") != "":
                    firejail_profile: str = channel.module_config("dm.firejail")
                    firejail_name = "mommi_dm_" + DMCodeHandler.random_string()
                    firejail = ["firejail", "--quiet",
                                f"--profile={firejail_profile}",
                                f"--private={path}",
                                f"--name={firejail_name}"]

                dmepath = await self.make_project(code, path)

                proc = await asyncio.create_subprocess_exec(*firejail, self.dm_executable_path(channel), str(dmepath), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                fail_reason = None
                try:
                    await asyncio.wait_for(proc.wait(), timeout=30)
                except asyncio.TimeoutError:
                    if firejail_name:
                        fjail_proc = await asyncio.create_subprocess_exec("firejail", f"--shutdown={firejail_name}")
                        await fjail_proc.wait()
                    else:
                        proc.kill()

                    fail_reason = "**Compilation failed** due to **timeout** (30 seconds)."

                assert proc.stdout is not None
                data = await proc.stdout.read()
                compile_log = data.decode("UTF-8", "replace")

                # Discord max size of field is 1024 chars.
                if len(compile_log) > 900:
                    log = compile_log[:900] + "\n<truncated due to size>"

                if fail_reason or proc.returncode:
                    embed = Embed()
                    embed.color = COLOR_COMPILE_FAIL
                    embed.description = fail_reason or "**Compilation failed**"
                    embed.add_field(name="Compiler Output",
                                    value=f"```{compile_log}```", inline=False)
                    await channel.send(embed=embed)
                    return

                #asyncio.ensure_future(channel.server.master.client.remove_reaction(message, "⌛", me))
                #asyncio.ensure_future(channel.server.master.client.add_reaction(message, "🔨"))

                proc = await asyncio.create_subprocess_exec(*firejail, self.dd_executable_path(channel), str(dmepath.with_name("code.dmb")), "-invisible", "-ultrasafe", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                try:
                    await asyncio.wait_for(proc.wait(), timeout=30)
                except asyncio.TimeoutError:
                    if firejail_name:
                        fjail_proc = await asyncio.create_subprocess_exec("firejail", f"--shutdown={firejail_name}")
                        await fjail_proc.wait()
                    else:
                        proc.kill()

                    fail_reason = "**Execution failed** due to **timeout** (30 seconds)."

                assert proc.stdout is not None and proc.stderr is not None
                data = await proc.stderr.read() + await proc.stdout.read()
                log = data.decode("UTF-8", "replace")
                if len(log) > 900:  # Discord max size of field is 1024 chars.
                    log = log[:900] + "\n<truncated due to size>"

                embed = Embed()
                embed.add_field(name="Compiler Output",
                                value=f"```{compile_log}```", inline=False)
                embed.add_field(name="Execution Output",
                                value=f"```{log}```", inline=False)

                #asyncio.ensure_future(channel.server.master.client.remove_reaction(message, "🔨", channel.server.get_server().me))

                if fail_reason:
                    embed.color = COLOR_RUN_FAIL
                    embed.description = fail_reason
                    #asyncio.ensure_future(channel.server.master.client.add_reaction(message, "❌"))

                else:
                    embed.color = COLOR_RUN_SUCCESS
                    #asyncio.ensure_future(channel.server.master.client.add_reaction(message, "✅"))

                await channel.send(embed=embed)

            except:
                await channel.send("Unknown error occured while executing code. Tell PJB to check the log files.")
                logger.exception("Exception while executing DM code")
                #await channel.server.master.client.remove_reaction(message, "🔨", me)
                #await channel.server.master.client.remove_reaction(message, "⌛", me)
                #await channel.server.master.client.add_reaction(message, "❌")


    def dm_executable_path(self, channel: MChannel) -> str:
        try:
            return channel.module_config("dm.dm_path")
        except:
            pass

        name = "DreamMaker"
        if sys.platform == "win32":
            name = "dm"

        path = self.byond_executable_path(name)

        if path is None:
            raise IOError(
                "Unable to locate Dream Maker compiler binary. Please ensure that it is in your PATH, or set module config dm.dm_path.")

        return path

    def dd_executable_path(self, channel: MChannel) -> str:
        try:
            return channel.module_config("dm.dd_path")
        except:
            pass

        name = "DreamDaemon"
        is_windows = sys.platform == "win32"
        if sys.platform == "win32":
            name = "dreamdaemon"

        path = self.byond_executable_path(name)

        if path is None:
            raise IOError(
                "Unable to locate Dream Daemon server binary. Please ensure that it is in your PATH, or set module config dm.dd_path.")

        return path

    def byond_executable_path(self, name: str) -> Optional[str]:
        path = spawn.find_executable(name)
        if path == None and sys.platform == "win32":
            # Attempt to look in %ProgramFiles% and %ProgramFiles(x86)% for BYOND.
            for path in (os.environ['ProgramFiles'], os.environ['ProgramFiles(x86)']):
                path = os.path.join(path, "BYOND", "bin", name + ".exe")

                if os.access(path, os.F_OK):
                    return path

        return path

    @staticmethod
    def random_string() -> str:
        return ''.join(choice(ascii_lowercase) for i in range(20))


async def load(loop: asyncio.AbstractEventLoop) -> None:
    register_help(__name__, "dm", """INTRODUCING THE BYOND-EXEC 5000™!

With the BYOND-Exec 5000™ you too can test BYOND code from the comfort of your Discord client!
Simply run the following command to be delighted by BYOND's ~~stupid fucking edge cases Lummox why~~ stability and consistency:

@MoMMI \\`\\`\\`
var/godwhy = .....
world.log << "[godwhy]"
\\`\\`\\`

Your code will automatically be wrapped in a proc and be ready for execution!
If this is not desired, simply put `/proc/main()` in your code, and MoMMI will put it at root level, auto executing `main()`.""")
