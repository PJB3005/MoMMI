import logging
from ..commands import command
from ..util import output
from ..permissions import isowner
from ..modules import modules
from ..client import client

@command("shutdown")
async def shutdown(content, match, message):
    if not isowner(message.author):
        return
    
    count = 0
    for module in modules:
        if hasattr(module, "save"):
            await module.save()
            count += 1 
    
    await output(message.channel, "Saved %s modules and shutting down!", count)
    await client.logout()
