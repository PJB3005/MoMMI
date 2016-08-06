import aioprocessing.connection
import asyncio
import discord

client = discord.Client()

@client.async_event
def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')

client.run('nope')