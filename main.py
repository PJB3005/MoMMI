#!/usr/bin/env python3
import argparse
import asyncio
import logging
import sys

version = sys.version_info
if version.major < 3 or (version.major == 3 and version.minor < 6):
    logging.critical("You need at least Python 3.6 to run MoMMI.")
    sys.exit(1)

import MoMMI.logsetup
from MoMMI.master import master
from pathlib import Path


def main():
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
