from ..client import client
from ..commands import command, command_help
from ..util import mainserver
import logging
import pickle
import aiofiles

logger = logging.getLogger(__name__)
pingGroups = {}


@command_help("ping", "A system for opt-in ping groups.", "ping (list|create|leave|join|ping) [group name]", """Subcommands:
 * **list**: Lists all pingroups, or the members of a specific group.
 * **create**: Create a ping group with the provided name.
 * **leave**: Leave the ping group with the provided name, deleting the group if it becomes empty.
 * **join**: Join the ping group with the provided name.
 * **ping**: Ping *everybody* in the ping group with the provided name. Yes you need to use ping twice when using this sub command.
""")
@command("ping\s*(?P<action>list|create|leave|join|ping)\s*(?P<name>\S*)")
async def pingcommand(content, match, message):
    action = match.group("action")
    name = match.group("name").lower()

    if action == "list":
        # If a name is provided, list members of a group WITHOUT PINGING THEM.
        if name:
            if name in pingGroups:
                await pingGroups[name].names(message.channel)

            else:
                await client.send_message(message.channel, "That group does not exist.")

        # List every group (without names but with numbers) instead.
        else:
            content = ""
            for group in pingGroups.values():
                content += "%s (%s members)\n" % (group.name, group.amount())

            await client.send_message(message.channel, content or "No groups to list!")

        # Return, so DO NOT save.
        return

    elif action == "create":
        if name in pingGroups:
            await client.send_message(message.channel, "That group already exists.")

        else:
            group = pingGroup(name)
            pingGroups[name] = group
            group.add(message.author)
            await client.send_message(message.channel, "Successfully created the group.")

    elif action == "leave":
        if name in pingGroups:
            if message.author in pingGroups[name].members:
                pingGroups[name].remove(message.author)
                if pingGroups[name].amount() == 0:
                    pingGroups.pop(name)

                await client.send_message(message.channel, "Successfully removed you from the group.")

            else:
                await client.send_message(message.channel, "You aren't even in the group!")

        else:
            await client.send_message(message.channel, "That group does not exist.")

    elif action == "join":
        if name in pingGroups:
            if message.author not in pingGroups[name].members:
                pingGroups[name].add(message.author)
                await client.send_message(message.channel, "Successfully added you to the group.")
            else:
                await client.send_message(message.channel, "You are already in the group!")

        else:
            await client.send_message(message.channel, "That group does not exist.")

    elif action == "ping":
        if name in pingGroups:
            await pingGroups[name].ping(message.channel)

        else:
            await client.send_message(message.channel, "That group does not exist.")

        # Return as to not save.
        return

    await _save()


class pingGroup(object):
    def __init__(self, name):
        self.name = name

        self.members = []

    # Easy serialization with pickle.
    def __getstate__(self):
        return {
            "name": self.name,
            "members": [member and member.id for member in self.members]
        }

    def __setstate__(self, state):
        self.name = state["name"]
        self.members = [mainserver().get_member(x) for x in state["members"]]

    async def ping(self, channel):
        message = " ".join([x.mention for x in self.members])
        await client.send_message(channel, message)

    async def names(self, channel):
        message = ""
        for member in self.members:
            message += "**%s**" % (member.display_name)
            if member.game:
                message += ": playing `%s`" % (member.game.name)
            message += "\n"

        # message = " ".join([x.display_name for x in self.members])
        await client.send_message(channel, message)

    def amount(self):
        return len(self.members)

    def add(self, member):
        self.members.append(member)

    def remove(self, member):
        self.members.remove(member)

async def load():
    global pingGroups
    logger.info("Loading ping groups.")
    byte = None
    async with aiofiles.open("pingdb", "rb") as f:
        byte = await f.read()
    try:
        pingGroups = pickle.loads(byte)
    except EOFError:
        logger.warning("Making new pingdb.")

async def unload(loop=None):
    logger.info("Unloading ping groups.")
    await _save(loop)

async def save():
    logger.info("Saving ping groups.")
    await _save()

async def _save(loop=None):
    byte = pickle.dumps(pingGroups)
    async with aiofiles.open("pingdb", "wb", loop=loop) as f:
        await f.write(byte)
