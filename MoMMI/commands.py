from .client import client
import re
import logging
import asyncio

logger = logging.getLogger(__name__)

commands = {}
is_command_re = None

def setup_commands():
    global is_command_re
    is_command_re = re.compile("^<\!?@%s>\s*" % (client.user.id))

def command(command, flags=re.IGNORECASE):
    """
    Decorator that registers a function as a command.
    This is regex.
    """

    def inner(function):
        if not asyncio.iscoroutinefunction(function):
            logger.warning("Attempted tor register non-coroutine %s!", function)
            function = asyncio.coroutine(function)
        
        pattern = re.compile(command, flags)
        commands[pattern] = function
        return function

    return inner

@client.event
async def on_message(message):
    if message.author.id == client.user.id:
        # Don't listen to ourselves!
        return

    logging.info(u"(%s) %s: %s", message.channel.name, message.author.name, message.content)
    match = is_command_re.match(message.content)
    if not match:
        return
    
    command = message.content[match.end():]
    for regex in commands:
        match = regex.match(command)
        if match:
            function = commands[regex]
            await function(command, match, message)
