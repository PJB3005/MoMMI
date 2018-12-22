#!/usr/bin/env python3

import os
import subprocess
from os.path import join as p


def main() -> int:
    files = []
    root = "MoMMI"
    for dirpath, dirnames, filenames in os.walk(root):
        if "__pycache__" in dirnames:
            dirnames.remove("__pycache__")

        if ".mypy_cache" in dirnames:
            dirnames.remove(".mypy_cache")

        for filename in filenames:
            if filename.endswith(".py"):
                files.append(p(dirpath, filename))

    return subprocess.run(["mypy", "--ignore-missing-imports", "--strict", "--allow-subclassing-any", "--allow-any-generics", *files], check=False).returncode

if __name__ == '__main__':
    exit(main())





