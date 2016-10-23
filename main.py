#!/usr/bin/env python3.5

import logging
import asyncio
import MoMMI.logsetup
import MoMMI.exceptions
import MoMMI.permissions
from MoMMI.config import get_config
from MoMMI.client import client


loop = asyncio.get_event_loop()
logger = logging.getLogger(__name__)

if get_config("token") == "UNSET":
    logger.critical("Discord auth token is unset, aborting.")
    exit()

logger.info("Starting client.")
try:
    asyncio.ensure_future(client.start(get_config("token")))
    loop.run_forever()
except KeyboardInterrupt:
    pass
