import discord
import json

data = json.load(open("Store.json", 'r'))

DELILAH_ID = data["DELILAH_ID"]
MY_ID = data["MY_ID"]
BOT_TOKEN = data["BOT_TOKEN"]

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    messageText = message.content.lower()

    if(("dee" in messageText) or (message.author.id == DELILAH_ID)):
        await message.channel.send("'s nuts!")
        await message.channel.send("HA!")
        await message.channel.send("GOTEEM!")

client.run(BOT_TOKEN)