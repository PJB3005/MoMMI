import logging
import re
from typing import Match, Set, Type, TypeVar, ClassVar
import aiohttp
from discord import Message, Color
from MoMMI.commands import command
from MoMMI.channel import MChannel
from MoMMI.role import MRoleType
from MoMMI.handler import MHandler
from MoMMI.master import master

logger = logging.getLogger(__name__)

FILE_EXTENSION_RE  = re.compile(r".+?(?:\.(.+))?$")
COLOR_RUN_SUCCESS  = Color(0x1ECF25)
COLOR_RUN_FAIL     = Color(0xC0C333)
COLOR_COMPILE_FAIL = Color(0xF90E0E)
#                     ```(?:([^\n]*)\n)?(.*)```
@command("runcode", r"\s*```(?:(?P<Language>[^\r\n]*)\r?\n)?(?P<Code>.*)```", flags=re.DOTALL)
async def runcode_command(channel: MChannel, match: Match, message: Message) -> None:
    language = match.group("Language")
    code = match.group("Code") or ""
    #logger.fatal(language)
    #logger.fatal(code)
    contents = ""
    if language and (" " in language.strip() or not code.strip()):
        contents = match.group("Language") + "\n"
        language = None

    contents += code.strip()

    if not language:
        language = "dm"

    if not await try_execute(contents, language, channel, message):
        await channel.send(f"No language with key: `{language}`. You probably didn't intend this so don't put any code on the same line as the opening backticks. That'll fix it.")


@command("runcode_file", "")
async def runcode_file_command(channel: MChannel, match: Match, message: Message) -> None:
    if not message.attachments:
        return

    async with aiohttp.ClientSession(headers={"User-Agent": "MoMMIv2 (GitHub @PJBot, GitHub @PJB3005)"}) as session:
        for i, attach in enumerate(message.attachments):
            filename = FILE_EXTENSION_RE.match(attach["filename"])
            if filename is None:
                continue

            language = filename.group(1) or "dm"
            url = attach["url"]

            try:
                async with session.get(url) as request:
                    if request.status != 200:
                        await channel.send(f"Got bad HTTP code on attachment #{i}: {request.status}")
                        continue

                    text = await request.text()

            except Exception as e:
                await channel.send("Got an error while downloading the attachment. Is it a text file?")
                logger.exception("Bad codehandling download")
                continue

            if not await try_execute(text, language, channel, message):
                await channel.send(f"No language with key: `{language}`.")


async def try_execute(code: str, language: str, channel: MChannel, message: Message) -> bool:
    for possiblehandler in channel.iter_handlers(MCodeHandler):
        if language in possiblehandler.languages:
            await possiblehandler.execute(code, channel, message)
            return True

    return False

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
