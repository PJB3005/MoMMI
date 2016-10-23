import logging
from ..commands import command, commands, always_commands, unsafe_always_commands
from ..config import get_config
from ..client import client
from ..modules import reload_modules
from ..commloop import events
from ..permissions import isowner

logger = logging.getLogger(__name__)


@command("reload")
async def reload(content, match, message):
    global always_commands, unsafe_always_commands
    if not isowner(message.author):
        await client.send_message(message.channel, "You don't have permission, fuck off.")
        return

    logger.info("Reloading modules! Initiated by %s (%s)", message.author.name, message.author.id)
    commands.clear()
    del(always_commands[:])
    del(events[:])
    del(unsafe_always_commands[:])

    reloaded, errored, new = await reload_modules()

    text_message = "Reloaded %s modules" % (reloaded)

    if new:
        text_message += ", %s new" % (new)

    if errored:
        text_message += ", %s errored" % (errored)

    text_message += "."

    await client.send_message(message.channel, text_message)
