import re
from ..client import client
from ..commands import command
import random

@command(u"\u2708", re.UNICODE)
async def plane(content, match, message):
    choices = ["🛬 💥", "✈ 🏢 🏢 💥 🔥 🚒", "https://camo.githubusercontent.com/e8f0f4cb1cb2250441c54aba8a3e6aef7b607be8/68747470733a2f2f75706c6f61642e77696b696d656469612e6f72672f77696b6970656469612f656e2f662f66352f416972706c616e652532312e6a7067", "https://camo.githubusercontent.com/cffee49b26b9fec2c26fcb646126b8e8e70ff3b8/68747470733a2f2f332e62702e626c6f6773706f742e636f6d2f2d577954314f66705847796b2f554866306c4e66485175492f41414141414141414163342f7a6f43796d336b715375382f733332302f4169722d547261666669632d436f6e74726f6c2e6a7067", "https://camo.githubusercontent.com/8a6e63d58d073e9458c62651435cea41dc3320b8/687474703a2f2f7777772e6163746976697374706f73742e636f6d2f77702d636f6e74656e742f75706c6f6164732f323031362f30322f747769747069632d33352e6a7067", "https://giphy.com/gifs/crash-wtc-killtown-LtNGa3nUw7SJW"]
    await client.send_message(message.channel, random.choice(choices))