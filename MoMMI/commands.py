import asyncio
import logging
import random
import re
import traceback
from typing import Callable, Match, Pattern, Awaitable, Optional, List, Any, TYPE_CHECKING
from discord import Message, User, Reaction
from MoMMI.handler import MHandler
from MoMMI.permissions import bantypes
from MoMMI.role import MRoleType

logger = logging.getLogger(__name__)
chatlogger = logging.getLogger("chat")

if TYPE_CHECKING:
    from MoMMI.channel import MChannel

CommandType = Callable[["MChannel", Match, Message], Awaitable[None]]
ReactionCommandType = Callable[["MChannel", Reaction, User], Awaitable[None]]
DeleteCommandType = Callable[["MChannel", Message], Awaitable[None]]


def command(name: str, regex: str, flags: int = re.IGNORECASE, **kwargs: Any) -> Callable[[CommandType], CommandType]:
    def inner(function: CommandType) -> CommandType:
        from MoMMI.master import master
        if not asyncio.iscoroutinefunction(function):
            logger.error(
                f"Attempted to register non-coroutine {function} as command!")
            return function

        pattern = re.compile(regex, flags)
        commandhandler = MCommand(
            name, function.__module__, function, pattern, **kwargs)
        commandhandler.register(master)
        return function
    return inner


def always_command(name: str, **kwargs: Any) -> Callable[[CommandType], CommandType]:
    def inner(function: CommandType) -> CommandType:
        from .master import master
        if not asyncio.iscoroutinefunction(function):
            logger.error(
                f"Attempted to register non-coroutine {function} as always command!")
            return function

        commandhandler = MCommand(
            name, function.__module__, function, prefix=False, **kwargs)
        commandhandler.register(master)
        return function

    return inner


def reaction_command(name: str) -> Callable[[ReactionCommandType], ReactionCommandType]:
    def inner(function: ReactionCommandType) -> ReactionCommandType:
        from .master import master
        if not asyncio.iscoroutinefunction(function):
            logger.error(
                f"Attempted to register non-coroutine {function} as reaction command!")
            return function

        commandhandler = MReactionCommand(name, function.__module__, function)
        commandhandler.register(master)
        return function

    return inner


def delete_command(name: str) -> Callable[[DeleteCommandType], DeleteCommandType]:
    def inner(function: DeleteCommandType) -> DeleteCommandType:
        from .master import master
        if not asyncio.iscoroutinefunction(function):
            logger.error(
                f"Attempted to register non-coroutine {function} as reaction command!")
            return function

        commandhandler = MDeleteCommand(name, function.__module__, function)
        commandhandler.register(master)
        return function

    return inner



class MCommand(MHandler):
    prefix_re: Optional[Pattern]

    def __init__(self,
                 name: str,
                 module: str,
                 func: CommandType,
                 regex: Optional[Pattern] = None,
                 unsafe: bool = False,
                 prefix: bool = True,
                 commandhelp: Optional[str] = None,
                 roles: Optional[List[MRoleType]] = None,
                 bans: Optional[List[bantypes]] = None
                 ) -> None:

        super().__init__(name, module)

        self.func: CommandType = func

        self.regex: Optional[Pattern] = regex

        self.unsafe: bool = unsafe
        self.prefix: bool = prefix

        self.help: Optional[str] = commandhelp
        self.roles: Optional[List[MRoleType]] = roles

    async def try_execute(self, channel: "MChannel", message: Message) -> None:
        message_start = 0
        match = None

        if message.author.id == channel.server.master.client.user.id and not self.unsafe:
            return

        if self.prefix:
            if MCommand.prefix_re is None:
                raise RuntimeError("MCommand.prefix_re has not been set!")

            match = MCommand.prefix_re.match(message.content)
            if not match:
                return

            message_start = match.end()

        if self.regex:
            content = message.content[message_start:]
            match = self.regex.match(content)
            if match is None:
                return

        if self.roles:
            found = False
            for role in self.roles:
                if channel.isrole(message.author, role):
                    found = True
                    break

            if not found:
                choice = random.choice(channel.main_config(
                    "bot.deny-messages", ["*buzz*"]))
                await channel.send(choice)
                return

        try:
            # TODO: type ignore because ALL commands take in a regex match,
            # but that only exists if you give the command decorator an actual regex.
            # Refactor this so that commands that don't take in a match are a different type.
            await self.func(channel, match, message)  # type: ignore
        except:
            traceback.print_exc()
            logger.exception("Exception in command handler!")


class MReactionCommand(MHandler):
    def __init__(self,
                name: str,
                module: str,
                func: ReactionCommandType
                ) -> None:

        super().__init__(name, module)

        self.func: ReactionCommandType = func


class MDeleteCommand(MHandler):
    def __init__(self,
                name: str,
                module: str,
                func: DeleteCommandType
                ) -> None:

        super().__init__(name, module)

        self.func: DeleteCommandType = func

    