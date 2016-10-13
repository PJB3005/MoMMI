from ..permissions import isowner
from ..util import output
from ..client import client
from ..config import get_config
from ..commands import command

@command(r"nick\s*(.*)$")
async def nickname_changer(content, match, message):
    if not isowner(message.author):
        await output(message.channel, "No")
        return

    server = client.get_server(str(get_config("mainserver.id")))
    myself = server.get_member(client.user.id)
    await client.change_nickname(myself, match.group(1))
