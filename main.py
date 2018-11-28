#!/usr/bin/env python3.6
import argparse
import asyncio
import logging
import MoMMI.config
import MoMMI.exceptions
import MoMMI.logsetup
import MoMMI.permissions
from MoMMI.client import client

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config-dir", "-c",
                        default="./config",
                        help="The directory to read config files from.",
                        dest="config")

    parser.add_argument("--server-dir", "-s",
                        default="./servers",
                        help="The directory to use for server data storage.",
                        dest="servers")

    namespace = parser.parse_args()

    logger.info("Loading config files.")
    loop = asyncio.get_event_loop()
    task = asyncio.gather(
        MoMMI.config.parse("config.yml"),
        MoMMI.config.parse("override.yml", override=True)
    )
    loop.run_until_complete(task)

    if not MoMMI.config.get_config("token"):
        logger.critical("Discord auth token is unset, aborting.")
        exit(1)

    logger.info("Starting client.")
    client.run(MoMMI.config.get_config("token"))

if __name__ == "__main__":
    main()
