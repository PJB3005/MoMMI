from ..util import output
from ..permissions import isbanned, ban, unban
from ..commands import command, command_help
from ..config import get_config

@command("ban", role=get_config("mainserver.roles.admin"))
async def ban(content, match, message):
    await output(message.channel, "It worked.")