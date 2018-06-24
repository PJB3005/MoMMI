import traceback
from discord import Message, Embed
from MoMMI.channel import MChannel
from MoMMI.Modules.CodeHandling.codehandling import codehandler, MCodeHandler, COLOR_COMPILE_FAIL, COLOR_RUN_FAIL
from MoMMI.role import MRoleType

@codehandler
class PythonCodeHandler(MCodeHandler):
    def __init__(self) -> None:
        self.name = "python"
        super().__init__()

        self.languages = {"py", "python"}

    async def execute(self, code: str, channel: MChannel, message: Message) -> None:
        if not channel.isrole(message.author, MRoleType.OWNER):
            await channel.send("Nope. You're not executing unsandboxed Python on my MoMMI!")
            return

        output = "async def __code(message, channel):\n"
        # Indent each line by one so we can put it as the function contents.
        lines = code.split("\n")
        for index, line in enumerate(lines):
            if not line.strip():
                continue

            lines[index] = " " * 4 + line

        output += "\n".join(lines)

        try:
            exec(output)

        except SyntaxError as e:
            embed = Embed()
            embed.color = COLOR_COMPILE_FAIL
            embed.add_field(name="Compiler Output", value=f"```{traceback.format_exc()}```", inline=False)
            await channel.send(embed=embed)
            return

        func = locals()["__code"]
        try:
            await func(message, channel)
        except:
            embed = Embed()
            embed.color = COLOR_RUN_FAIL
            embed.add_field(name="Exception", value=f"```{traceback.format_exc()}```", inline=False)
            await channel.send(embed=embed)
            return

