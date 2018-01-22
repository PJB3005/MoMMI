import logging
from typing import Any
from MoMMI.channel import MChannel
from MoMMI.commloop import comm_event
from MoMMI.types import SnowflakeID

import json


logger = logging.getLogger(__name__)

@comm_event("gamenudge")
async def gamenudge(channel: MChannel, message: Any, meta: str):
    # logger.debug(json.dumps(message))
    try:
        password = message["pass"]
        content = message["content"]
        ping = message["ping"]

    except KeyError:
        return

    if password != channel.module_config("nudge.password"):
        return

    content = content.replace("@", "@\u200B") # Zero-Width space to prevent pings.

    if ping:
        cfg = channel.server_config("modules.gamenudge.ping", {})
        if not cfg.get(meta):
            logger.warning("Got a ping nudge but no set role ID!")
        else:
            ident = cfg[meta]
            role = channel.server.get_discordpy_role(SnowflakeID(ident))
            content += f" {role.mention}"

    await channel.send(content)
