import logging
import re
from typing import Match, Set, Type, TypeVar, ClassVar
from discord import Message, Color
from MoMMI.commands import command
from MoMMI.channel import MChannel
from MoMMI.role import MRoleType
from MoMMI.handler import MHandler
from MoMMI.master import master

logger = logging.getLogger(__name__)

COLOR_RUN_SUCCESS  = Color(0x1ECF25)
COLOR_RUN_FAIL     = Color(0xC0C333)
COLOR_COMPILE_FAIL = Color(0xF90E0E)

@command("runcode", r"```(?P<Language>[^\r\n]*)\r?\n(?P<Code>.*)\r?\n```", flags=re.DOTALL)
async def runcode_command(channel: MChannel, match: Match, message: Message) -> None:
    language = match.group("Language").lower() or "dm" # Default to DM
    code = match.group("Code")

    for possiblehandler in channel.iter_handlers(MCodeHandler):
        if language in possiblehandler.languages:
            await possiblehandler.execute(code, channel, message)
            return

    await channel.send(f"No language with key: `{language}`")

class MCodeHandler(MHandler):
    def __init__(self) -> None:
        super().__init__("ERROR", self.__module__)

        self.languages: Set[str] = set()

    async def execute(self, code: str, channel: MChannel, message: Message) -> None:
        raise RuntimeError("This function needs to be overriden.")


def codehandler(handler: Type[MCodeHandler]) -> Type[MCodeHandler]:
    instance = handler()
    master.register_handler(instance)
    return handler
