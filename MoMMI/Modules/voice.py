from typing import re, cast
from logging import getLogger, Logger
from discord import Message, Member, VoiceClient
from asyncio import get_event_loop, AbstractEventLoop, ensure_future
from ..commands import command, command_help
from ..client import client
from ..voice import VoiceManager, get_voice_manager
from ..util import output
from ..permissions import bantypes

logger = getLogger(__name__)  # type: Logger


@command_help("music", "Plays music in the voice channel you're currently in.", "music [queue|stop] <link>", """Plays music in the voice channel you're currently in. Supports queuing too.
A list of sites that you can play links from can be found here: https://rg3.github.io/youtube-dl/supportedsites.html
Giving it a link directly will stop the currently playing track (if any) and then play the URL at the link, provided it is valid.
You can stop the currently music and clear the queue with the `stop` subcommand.
If you want to queue a track you can do so with `queue` and giving it a URL.

For admins: you can ban people from using this with the `music` ban type.
""")
@command(r"music\s*(stop|(queue|)\s*([^\s]+))\s*", ban_groups=[bantypes.music])
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
    if voice_manager.lock:
        await output(message.channel, "Wait a second.")
        return

    voice_manager.lock = True

    try:
        if match.group(1) == "stop":
            await voice_manager.leave_voice()
            logger.info("Stopped voice.")
            voice_manager.queue = []
            logger.debug(voice_manager.player)
            logger.debug(voice_manager.voice)

        elif match.group(2) == "queue" and voice_manager.player is not None:
            voice_manager.queue_url(url)
            logger.info("Added URL %s to the queue", url)

        else:
            await voice_manager.start_player(url, member.voice_channel)
            logger.info("Started playing URL %s", url)

    except:
        logger.exception("SOMETHING happened.")

    finally:
        voice_manager.lock = False
