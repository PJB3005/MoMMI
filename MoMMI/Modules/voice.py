from typing import re, cast
from logging import getLogger, Logger
from discord import Message, Member, VoiceClient
from asyncio import get_event_loop, AbstractEventLoop, ensure_future
from ..commands import command, command_help
from ..client import client
from ..voice import VoiceManager, get_voice_manager
from ..util import output

logger = getLogger(__name__)  # type: Logger


@command(r"music\s*(stop|(queue|)\s*([^\s]+))\s*")
async def music(content: str, match: re.Match, message: Message):
    url = match.group(3)  # type: str

    if not isinstance(message.author, Member):
        await output(message.channel, "You are not talking to me on a server.")
        return

    member = cast(Member, message.author)  # type: Member
    if member.voice_channel is None:
        await output(message.channel, "You need to be in a voice channel.")
        return

    voice_manager = get_voice_manager(message.server)  # type: VoiceManager
    logger.info(voice_manager)
    if match.group(1) == "stop":
        await voice_manager.leave_voice()
        logger.info("Stopped voice.")
        voice_manager.queue = []

    elif match.group(2) == "queue" and voice_manager.player is not None:
        voice_manager.queue_url(url)
        logger.info("Added URL %s to the queue", url)

    else:
        await voice_manager.start_player(url, member.voice_channel)
        logger.info("Started playing URL %s", url)
