import logging
from MoMMI.commloop import comm_event

logger = logging.getLogger(__name__)

@comm_event("gamenudge")
async def gamenudge(channel, message, meta):
    try:
        password, content = message["password"], message["message"]

    except:
        return

    if password != channel.module_config("nudge.password"):
        return

    if content.find("{{PING}}") != -1:
        ping_target = channel.server_config(f"modules.gamenudge.ping.{meta}")
        ping = ""

        if ping_target is None:
            logger.error("Attempted to use a ping escape code, but no roles for it are set for this server route.")

        else:
            role = channel.get_role(ping_target)

            if role is not None and role.mentionable:
                ping = role.mention

        content = content.replace("{{PING}}", ping)

    await channel.send(content)
