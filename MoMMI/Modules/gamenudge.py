import logging
from typing import Any, Dict
from MoMMI import MChannel, comm_event, SnowflakeID

import json


logger = logging.getLogger(__name__)

@comm_event("gamenudge")
async def gamenudge(channel: MChannel, message: Any, meta: str) -> None:
    logger.debug(json.dumps(message))
    try:
        password = message["pass"]
        content = message["content"]
        ping = message["ping"]

    except KeyError:
        return

    if password != channel.module_config("nudge.password"):
        return

    content = content.replace("@", "@\u200B") # Zero-Width space to prevent pings.

    # This string closes the #ick channel for 10 minutes
    if content == "round_end_thread_remind":
        thread_reminder(MChannel)
        return

    if ping:
        cfg: Dict[str, Any] = channel.server_config("modules.gamenudge.ping", {})
        if not cfg.get(meta):
            logger.warning("Got a ping nudge but no set role ID!")
        else:
            ident = cfg[meta]
            role = channel.server.get_discordpy_role(SnowflakeID(ident))
            content += f" {role.mention}"

    await channel.send(content)
