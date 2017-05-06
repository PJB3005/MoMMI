import asyncio
import logging
import random
import re
from discord import Message
from typing import Callable, re as typing_re, Awaitable, Optional, List
from MoMMI.handler import MHandler
from MoMMI.permissions import bantypes

logger = logging.getLogger(__name__)
chatlogger = logging.getLogger("chat")


def command(name: str, regex: str, flags: re.RegexFlag = re.IGNORECASE, **kwargs):
    """
    Decorator that registers a function as a command.
    This is regex.
    """

    def inner(function):
        from MoMMI.master import master
        if not asyncio.iscoroutinefunction(function):
            logger.error(f"Attempted to register non-coroutine {function}!")
            return

        pattern = re.compile(regex, flags)
        command = MCommand(name, function.__module__, function, pattern, **kwargs)
        command.register(master)
        return function

    return inner

def always_command(name: str, **kwargs):
    def inner(function):
        from .master import master
        if not asyncio.iscoroutinefunction(function):
            logger.error(f"Attempted to register non-coroutine {function}!")
            return

        command = MCommand(name, function.__module__, function, prefix=False, **kwargs)
        command.register(master)
        return function

    return inner

"""
@client.event
async def on_message(message):
    for function in unsafe_always_commands:
        await function(message)

    if message.author.id == client.user.id:
        # Don't listen to ourselves!
        return

    chatlogger.info("(%s) %s: %s", message.channel.name, message.author.name, message.content)

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
                    found_ban = False  # type: bool
                    for bantype in function.ban_groups:
                        if isbanned(message.author, bantype):
                            found_ban = True
                            break

                    if found_ban:
                        await output(message.channel, "You are banned from executing that command.")
                    elif function.role_requirement and not isrole(message.author, function.role_requirement):
                        await output(message.channel, "You do not have permission to execute that command.")
                    else:
                        try:
                            await function(command, match, message)
                        except:
                            logger.exception("Caught exception inside command.")

    for function in always_commands:
        if function.no_other_commands and matched_anything:
            continue

        await function(message)
"""


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

class MCommand(MHandler):
    from MoMMI.server import MChannel

    prefix_re: typing_re.Pattern

    def __init__(self,
                 name: str,
                 module: str,
                 func: Callable[[MChannel, typing_re.Match, Message], Awaitable[None]],
                 regex: Optional[typing_re.Pattern] = None,
                 unsafe: bool = False,
                 prefix: bool = True,
                 help: Optional[str] = None,
                 roles: List[str] = [],
                 bans: List[bantypes] = []):

        super().__init__(name, module)

        self.func = func  # type: Callable[[MChannel, Message, typing_re.Match], Awaitable[None]]

        self.regex = regex  # type: typing_re.Pattern

        self.unsafe = unsafe  # type: bool
        self.prefix = prefix  # type: bool

        self.help = help  # type: Optional[str]
        self.roles = roles  # type: List[str]

    # Gets ran over the message. If it returns True other commands don't run.
    async def try_execute(self, channel: MChannel, message: Message) -> bool:
        message_start = 0
        match = None

        if message.author.id == channel.server.master.client.user.id and not self.unsafe:
            return

        if self.prefix:
            match = MCommand.prefix_re.match(message.content)
            if not match:
                return

            message_start = match.end()

        if self.regex:
            content = message.content[message_start:]
            match = self.regex.match(content)
            if match is None:
                return

        if len(self.roles):
            found = False
            for role in self.roles:
                if channel.isrole(message.author, role):
                    found = True
                    break

            if not found:
                choice = random.choice(channel.main_config("bot.deny-messages", ["*buzz*"]))
                await channel.send(choice)
                return

        await self.func(channel, match, message)
