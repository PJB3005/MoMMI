import logging
from typing import Callable, Awaitable, Union, Match
from discord import Message
from MoMMI import MChannel, command, master
from MoMMI.handler import MHandler

LOGGER = logging.getLogger(__name__)
callback_type = Callable[[MChannel, Message], Awaitable[str]]


@command("help_command", r"help(?:\s+(\S+))?")
async def help_command(channel: MChannel, match: Match, message: Message) -> None:
    if match[1] is None:
        msg = """Yes hello I'm your ~~un~~friendly neighbourhood MoMMI.
Send @MoMMIv2 help <topic> for more info.
Available topics are: """
        msg += ", ".join((h.topic for h in channel.iter_handlers(HelpHandler)))

        await channel.send(msg)
        return

    found: HelpHandler

    for handler in channel.iter_handlers(HelpHandler):
        print(handler.name)
        if handler.topic == match[1]:
            found = handler
            break

    else:
        await channel.send("Invalid topic")
        return

    if isinstance(found.contents, str):
        await channel.send(found.contents)

    else:
        await channel.send(await found.contents(channel, message))


def register_help(module: str, topic: str, contents: Union[str, callback_type]) -> None:
    """
    Register a help article to a specific module, having a specific topic and contents.
    If the contents is a callback, it will be called and awaited to get the help string.
    """
    handler = HelpHandler(topic, module, contents)
    handler.register(master)
    #print(f"{module}: {topic}")


class HelpHandler(MHandler):
    def __init__(self, topic: str, module: str, contents: Union[str, callback_type]) -> None:
        super().__init__(topic + "__help", module)

        self.contents = contents
        self.topic = topic


register_help(__name__, "help", "How hopeless are you, exactly?")
