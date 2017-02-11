#!/usr/bin/env python3.5
import argparse
import asyncio
import logging
import MoMMI.logsetup
import sys
from MoMMI.master import master
from pathlib import Path

logger = logging.getLogger(__name__)


def main():
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 6):
        logger.critical("You need at least Python 3.6 to run MoMMI.")
        sys.exit(1)

    parser = argparse.ArgumentParser()
    parser.add_argument("--config-dir", "-c",
                        default="./config",
                        help="The directory to read config files from.",
                        dest="config",
                        type=Path)

    parser.add_argument("--storage-dir", "-s",
                        default="./data",
                        help="The directory to use for server data storage.",
                        dest="data",
                        type=Path)

    args = parser.parse_args()

    master.start(args.config, args.data)


if __name__ == "__main__":
    main()
