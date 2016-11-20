import logging
import re
import discord
from typing import Any, Dict, Type
import asyncio
import discord
from ..client import client
from ..commands import command
from ..config import get_config
from ..util import output
from .CodeHandling.codehandler import CodeHandler, all_code_handlers
from .CodeHandling.codeoutput import CodeOutput, CodeHandlerState
from .CodeHandling.dm import DMCodeHandler

logger = logging.getLogger(__name__)  # type: logging.Logger

# , role=get_config("mainserver.roles.coder")
@command(r"```(?P<Language>[^\r\n]*)\r?\n(?P<Code>.*)\r?\n```", flags=re.DOTALL, role=get_config("mainserver.roles.coder"))
async def runcode(content: str, match, message: discord.Message):
    language = match.group("Language").lower() or "dm"  # type: str
    code = match.group("Code")  # type: str

    logger.info(repr(code))

    handler = all_code_handlers[language]()  # type: CodeHandler

    codeoutput = await handler.execute(code)  # type: CodeOutput
    await handler.cleanup()
    logger.info(codeoutput.output)

    await output(message.channel, "Status: **{}**".format(CodeHandlerState.get_name(codeoutput.state)))
    await output(message.channel, "Compiler output:```\n{}```".format(codeoutput.compile_output))
    if codeoutput.state != CodeHandlerState.failed_compile:
        await output(message.channel, "Code Output:```\n{}```".format(codeoutput.output))
