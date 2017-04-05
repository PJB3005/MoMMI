from logging import getLogger
from ..commands import command
from ..client import client

logger = getLogger(__name__)


@command("news")
async def news(content, match, message):
    found = False
    for role in message.author.roles:
        if role.id == "287214111379685386":
            found = True
            logger.info("yes")
            break

    role = None

    for s_role in message.server.roles:
        if s_role.id == "287214111379685386":
            role = s_role

    if role is None:
        return

    if found:
        await client.remove_roles(message.author, role)
        await client.send_message(message.channel, "Successfully removed the news role from you.")

    else:
        await client.add_roles(message.author, role)
        await client.send_message(message.channel, "Successfully added the news role to you.")
