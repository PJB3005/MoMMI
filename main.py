#!/usr/bin/env python3.5

import logging
import MoMMI.logsetup
import MoMMI.exceptions
from MoMMI.config import config
from MoMMI.client import client

logger = logging.getLogger(__name__)

if config["token"] == "unset":
    logger.critical("Discord auth token is unset, aborting.")
    exit()

logger.info("Starting client.")
client.run(config["token"])