import enum
import logging
from discord import Channel, Embed, Colour
from typing import List, Type
from ..client import client


class CodeHandlerState(enum.Enum):
    # Didn't pass a compile.
    failed_compile = 1
    # Passed a compile.
    # May or may not have failed execution?
    # Unable to correctly determine.
    compiled = 2
    # Compiled but failed execution
    errored = 3
    # Finished successfully.
    finished = 4

    @staticmethod
    def get_name(state) -> str:
        if state == CodeHandlerState.failed_compile:
            return "Compile failed"
        if state == CodeHandlerState.compiled:
            return "Compiled"
        if state == CodeHandlerState.errored:
            return "Execution failed."
        else:
            return "Finished"

    @staticmethod
    def colour(state) -> Colour:
        if state == CodeHandlerState.failed_compile or state == CodeHandlerState.errored:
            return Colour(0xF90E0E)
        if state == CodeHandlerState.compiled:
            return Colour(0xC0C333)
        else:
            return Colour(0x1ECF25)


class CodeOutput(object):
    """
    A type for managing the output of a CodeHandler.
    """

    def __init__(self):
        self.output = ""  # type: str
        self.compile_output = ""  # type: str

        self.state = CodeHandlerState.failed_compile  # type: CodeHandlerState

    async def output_result(self, channel: Channel):
        embed = Embed()
        embed.colour = CodeHandlerState.colour(self.state)
        embed.description = "**Status:** {}".format(CodeHandlerState.get_name(self.state))
        embed.add_field(name="Compiler Output", value="```\n{}\n```".format(self.compile_output), inline=False)
        if self.state != CodeHandlerState.failed_compile:
            embed.add_field(name="Code Output", value="```\n{}\n```".format(self.output), inline=False)

        await client.send_message(channel, embed=embed)
