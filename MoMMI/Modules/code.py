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
from .codehandler import CodeHandler, all_code_handlers
from .codeoutput import CodeOutput, CodeHandlerState

logger = logging.getLogger(__name__)  # type: logging.Logger


@command(r"```(?P<Language>[^\r\n]*)\r?\n(?P<Code>.*)\r?\n```", flags=re.DOTALL, role=get_config("mainserver.roles.coder"))
async def runcode(content: str, match, message: discord.Message):
    language = match.group("Language").lower() or "dm"  # type: str
    code = match.group("Code")  # type: str

    logger.info(repr(code))

    handler = all_code_handlers[language]()  # type: CodeHandler

    codeoutput = await handler.execute(code, message)  # type: CodeOutput
    await handler.cleanup()
    await codeoutput.output_result(message.channel)
