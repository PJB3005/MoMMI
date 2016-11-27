import logging
import traceback
from discord import Message, Channel, Embed, Colour
from typing import List
from .codehandler import CodeHandler, code_handler, CodeHandlerState
from .codeoutput import CodeOutput
from ..client import client
from ..permissions import isowner
from ..util import output


class PyCodeOutput(CodeOutput):
    async def output_result(self, channel: Channel):
        embed = Embed()  # type: Embed
        embed.colour = CodeHandlerState.colour(self.state)
        embed.description = "**Status:** {}".format(CodeHandlerState.get_name(self.state))

        if self.state == CodeHandlerState.failed_compile:
            embed.add_field(name="Compiler Output", value="```\n{}\n```".format(self.compile_output), inline=False)
            await client.send_message(channel, embed=embed)
            return

        if self.state == CodeHandlerState.errored:
            embed.add_field(name="Exception", value="```\n{}\n```".format(self.output), inline=False)
            await client.send_message(channel, embed=embed)


@code_handler("py")
class PyCodeHandler(CodeHandler):
    async def execute(self, code: str, message: Message) -> CodeOutput:
        if not isowner(message.author):
            await output(message.channel, "Nope!")
            return

        output = "async def __code(message):\n"  # type: str
        # Indent each line by one so we can put it as the function contents.
        lines = code.split("\n")  # type: List[str]
        for index, line in enumerate(lines):
            if not line.strip():
                continue

            lines[index] = " " * 4 + line

        output += "\n".join(lines)
        logging.info(output)
        out = PyCodeOutput()  # type: PyCodeOutput
        try:
            exec(output)
        except SyntaxError as e:
            out.state = CodeHandlerState.failed_compile
            out.compile_output = traceback.format_exc()
            logging.info(out.state)
            return out
        else:
            # Can't access it directly.
            code_function = locals()["__code"]
            try:
                await code_function(message)
            except:
                out.state = CodeHandlerState.errored
                out.output = traceback.format_exc()
            else:
                out.state = CodeHandlerState.finished

        logging.info(out.state)
        logging.info("hrm")
        return out

    async def cleanup(self):
        pass
