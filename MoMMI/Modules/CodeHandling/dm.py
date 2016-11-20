import sys
import aiofiles
import logging
import os
import asyncio
from typing import List
from asyncio.subprocess import create_subprocess_exec
from .codehandler import CodeHandler, code_handler, CodeHandlerState
from .codeoutput import CodeOutput


logger = logging.getLogger(__name__)  # type: logging.Logger


@code_handler("dm")
class DMCodeHandler(CodeHandler):
    async def make_project(self, code: str) -> str:
        path = await self.make_project_folder()  # type: str

        code = code.replace("\r", "\n").replace("    ", "\t")
        lines = code.split("\n")  # type: List[str]

        # Create a global variable and make it new the dummy type, so it instantly executes on world start.
        output = """var/a/b=new
/a/New()
"""

        # Indent each line by one so we can put it as a datum's New().s
        for index, line in enumerate(lines):
            if not line.strip():
                continue

            lines[index] = "\t" + line

        output += "\n".join(lines)

        output += """
var/c/d=new
/c/New()
\tshutdown()"""

        dmepath = os.path.join(path, "code.dm")  # type: str

        async with aiofiles.open(dmepath, "w") as f:
            await f.write(output)

        logger.info(output)

        return dmepath

    async def execute(self, code: str) -> CodeOutput:
        dmepath = await self.make_project(code)

        proc = await create_subprocess_exec("DreamMaker", dmepath, stdout=asyncio.subprocess.PIPE)  # type: asyncio.Process
        await proc.wait()
        data = await proc.stdout.read()  # type: bytes
        compile_log = data.decode("ascii")  # type: str

        out = CodeOutput()  # type: CodeOutput
        out.compile_output = compile_log
        if proc.returncode:
            out.state = CodeHandlerState.failed_compile
            return out
        else:
            out.state = CodeHandlerState.compiled

        proc = await create_subprocess_exec("DreamDaemon", dmepath + "b", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        await proc.wait()
        data = await proc.stderr.read() + await proc.stdout.read()
        log = data.decode("ascii")  # type: str

        out.output = log

        return out
