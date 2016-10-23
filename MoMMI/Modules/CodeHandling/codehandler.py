import os
import time
import shutil
import logging
from typing import Any
from .codeoutput import CodeHandlerState, CodeOutput


logger = logging.getLogger(__name__)  # type: Logger


class CodeHandler(object):
    def __init__(self):
        self.projectpath = ""  # type: str

    async def execute(self, code: str) -> CodeOutput:
        pass

    async def make_project_folder(self) -> str:
        # Even if there's a folder already there, keep trying by adding a number to the end.
        offset = 0  # type: int
        path = ""  # type: str
        while True:
            path = os.path.join(os.getcwd(), "codeprojects", "{}-{}".format(int(time.time()), offset))  # type: str
            try:
                os.mkdir(path)
            except FileExistsError:
                offset += 1
            else:
                break

        self.projectpath = path  # type: str
        return path

    async def cleanup(self):
        if not self.projectpath.startswith(os.path.join(os.getcwd(), "codeprojects")):
            logger.error("Failed to delete project subdirectory because the directory doesn't start with our cwd!")
            return

        shutil.rmtree(self.projectpath)


all_code_handlers = {}  # type: Dict[str, Type[CodeHandler]]


def code_handler(language: str):
    """
    Decorator that marks an implementation of CodeHandler for a specific language.
    """
    global all_code_handlers

    def inner(function):
        global all_code_handlers
        all_code_handlers[language] = function

        return function

    return inner
