from .client import client
from .util import output
from .permissions import isrole, isbanned, bantypes
import re
import logging
import asyncio

logger = logging.getLogger(__name__)

commands = {}
help_cache = {}
always_commands = []
unsafe_always_commands = []
is_command_re = None


def setup_commands():
    global is_command_re
    is_command_re = re.compile(r"^<@\!?%s>\s*" % (client.user.id))


def command(command, flags=re.IGNORECASE, role=None, ban_groups=None):
    """
    Decorator that registers a function as a command.
    This is regex.
    """

    def inner(function):
        if not asyncio.iscoroutinefunction(function):
            logger.warning("Attempted to register non-coroutine %s!", function)
            function = asyncio.coroutine(function)

        pattern = re.compile(command, flags)
        commands[pattern] = function
        function.role_requirement = role
        function.ban_groups = ban_groups
        return function

    return inner


def always_command(no_other_commands=False):
    def inner(function):
        global always_commands
        if not asyncio.iscoroutinefunction(function):
            logger.warning("Attempted to register non-coroutine %s!", function)
            function = asyncio.coroutine(function)

        function.no_other_commands = no_other_commands
        always_commands.append(function)

        return function

    return inner


@client.event
async def on_message(message):
    for function in unsafe_always_commands:
        await function(message)

    if message.author.id == client.user.id:
        # Don't listen to ourselves!
        return

    logging.info(u"(%s) %s: %s", message.channel.name, message.author.name, message.content)

    match = is_command_re.match(message.content)
    matched_anything = False
    if match:
        if isbanned(message.author, bantypes.commands):
            await output(message.channel, "You are banned from executing commands.")

        else:
            command = message.content[match.end():]
            for regex in commands:
                match = regex.match(command)
                if match:
                    matched_anything = True
                    function = commands[regex]
                    if function.role_requirement and not isrole(message.author, function.role_requirement):
                        await output(message.channel, "You do not have permission to execute that command.")
                    else:
                        await function(command, match, message)

    for function in always_commands:
        if function.no_other_commands and matched_anything:
            continue

        await function(message)


def command_help(key, shortdesc, usage, longdesc=None):
    """
    Register a command in the help cache.
    """
    def inner(function):
        try:
            permissions = function.role_requirement
        except AttributeError:
            permissions = None

        help_cache[key] = shortdesc, usage, longdesc, permissions

    return inner


def unsafe_always_command():
    def inner(function):
        global unsafe_always_commands
        if not asyncio.iscoroutinefunction(function):
            logger.warning("Attempted to register non-coroutine %s!", function)
            function = asyncio.coroutine(function)

        unsafe_always_commands.append(function)

        return function

    return inner
