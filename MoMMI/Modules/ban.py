from ..util import output, mainserver
from ..permissions import isbanned, ban, unban, bantypes, bans
from ..commands import command, command_help
from ..config import get_config
from ..client import client


@command_help("ban", "Bans somebody for a specified ban type.", "ban [@mention to member] [ban type]", """Ban types:
* **commands**: Bans somebody from using most commands.
* **markov**: Bans somebody from being listened to for building the markov database. This means their banter won't ever be said by MoMMI.
* **irc**: Prevents a person's messages from showing up on IRC.
* **music**: Bans a person from playing music.
""")
@command(r"ban\s*<@!?(?P<snowflake_id>\d+)>\s*(?P<type>\w+)", role=get_config("mainserver.roles.admin"))
async def ban_command(content, match, message):
    member = message.server.get_member(match.group("snowflake_id"))
    if not member:
        await output(message.channel, "Unable to find the member with ID %s" % (match.group("snowflake_id")))
        return

    try:
        bantype = bantypes[match.group("type")]

    except KeyError:
        await output(message.channel, "That ban type does not exist. Use `help ban` for a list of ban groups.")
        return

    if isbanned(member, bantype):
        await output(message.channel, "That member is already banned on group %s" % (match.group("type")))
        return

    await ban(member, bantype)

    await output(message.channel, "It worked.")


@command_help("unban", "Unbans somebody for a specified ban type.", "unban [@mention to member] [ban type]", "See the `ban` command for a list of ban types.")
@command(r"unban\s*<@!?(?P<snowflake_id>\d+)>\s*(?P<type>\w+)", role=get_config("mainserver.roles.admin"))
async def unban_command(content, match, message):
    member = message.server.get_member(match.group("snowflake_id"))
    if not member:
        await output(message.channel, "Unable to find the member with ID %s" % (match.group("snowflake_id")))
        return

    try:
        bantype = bantypes[match.group("type")]

    except KeyError:
        await output(message.channel, "That ban type does not exist. Use `help ban` for a list of ban groups.")
        return

    if not isbanned(member, bantype):
        await output(message.channel, "That member is not event banned on group %s!", match.group("type"))
        return

    await unban(member, bantype)

    await output(message.channel, "It worked.")


@command(r"bans")
async def output_bans(content, match, message):
    content = ""
    for bantype in bans.keys():
        content += "**__%s__**:\n" % (bantype.name)
        for ban in bans[bantype]:
            member = mainserver().get_member(str(ban))
            if member:
                content += "%s (%s)\n" % (member.name, member.display_name)

    await output(message.author, content)
