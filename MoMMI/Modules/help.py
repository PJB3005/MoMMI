from ..client import client
from ..commands import command, command_help, help_cache
from ..permissions import isrole


@command_help("help", "Display a list of commands, or usage of a specific command.", "help [command]")
@command("help\s*(\S*)")
async def actually_the_help_command(content, match, message):
    commandname = match.group(1)
    content = ""
    if not commandname:
        content = "Available commands:\n"
        for command in help_cache:
            # Handle permissions.
            if help_cache[command][3]:
                if not isrole(message.author, help_cache[command][3]):
                    continue

            content += "**%s**: %s\n" % (command, help_cache[command][0])
    
    else:
        if commandname not in help_cache:
            content = "That command does not exist!"

        else:
            content = "**%s**: %s\n**Usage**: `%s`" % (commandname, help_cache[commandname][0], help_cache[commandname][1])
            if help_cache[commandname][2]:
                content += "\n" + help_cache[commandname][2]

    await client.send_message(message.author, content)
