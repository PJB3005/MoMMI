"""
import logging
import re
from typing import Match, Set, Type, TypeVar, ClassVar
from discord import Message
from MoMMI.commands import command
from MoMMI.channel import MChannel
from MoMMI.role import MRoleType
from MoMMI.handler import MHandler
from MoMMI.master import master

logger = logging.getLogger(__name__)

@command("runcode", r"```(?P<Language>[^\r\n]*)\r?\n(?P<Code>.*)\r?\n```", flags=re.DOTALL, roles=[MRoleType.OWNER])
async def runcode_command(channel: MChannel, match: Match, message: Message):
    language = match.group("Language").lower() or "dm"
    code = match.group("Code")

    for possiblehandler in channel.iter_handlers(MCodeHandler):
        if language in possiblehandler.languages:
            await possiblehandler.execute(code, channel, message)


class MCodeHandler(MHandler):
    name: ClassVar[str] = "ERROR"

    def __init__(self) -> None:
        super().__init__(type(self).name, self.__module__)

        self.languages: Set[str] = {}

    async def execute(self, code: str, channel: MChannel, message: Message):
        raise RuntimeError("This function needs to be overriden.")


CodeHandlerT = TypeVar("CodeHandlerT", Type[MCodeHandler])
def codehandler(handler: CodeHandlerT) -> CodeHandlerT:
    instance = handler()
    master.register_handler(instance)
    return handler
"""
