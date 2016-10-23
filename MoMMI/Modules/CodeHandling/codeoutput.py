import enum
from typing import List, Type


class CodeHandlerState(enum.Enum):
    # Didn't pass a compile.
    failed_compile = 1
    # Passed a compile, but failed on execution.
    compiled = 2
    # Finished successfully.
    finished = 3

    def get_name(state) -> str:
        if state == CodeHandlerState.failed_compile:
            return "Compile failed"
        elif state == CodeHandlerState.compiled:
            return "Compiled successfully"
        else:
            return "Finished successfully"


class CodeOutput(object):
    """
    A type for managing the output of a CodeHandler.
    """

    def __init__(self):
        self.output = ""  # type: str
        self.compile_output = ""  # type: str
        self.errors = []  # type: List[str]

        self.state = CodeHandlerState.failed_compile  # type: CodeHandlerState
