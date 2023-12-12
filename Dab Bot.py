import discord
from discord import app_commands
import json
import datetime
import pytz

data = json.load(open("Store.json", 'r'))

DELILAH_ID = data["DELILAH_ID"]
MY_ID = data["MY_ID"]
BOT_TOKEN = data["BOT_TOKEN"]
GUILDS = [discord.Object(guildID) for guildID in data["GUILD_IDS"]]

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)
#bot = commands.Bot(command_prefix='!', intents=intents)

tree = app_commands.CommandTree(client)

@client.event
async def on_ready():
    for guild1 in GUILDS:
        print(guild1)
        await tree.sync(guild=guild1)
    print(f'We have logged in as {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    messageText = message.content.lower()

    if "dee" in messageText:
        await message.channel.send("'s nuts!")
        await message.channel.send("HA!")
        await message.channel.send("GOTEEM!")

@tree.command(name = "birthday", description = "Checks whether the birthday roles need to be updated.", guilds = GUILDS)
async def birthday(interaction):
    await interaction.response.send_message("Working...")
    birthdayRole = None
    for role in interaction.guild.roles:
        if role.name == "Birthday":
            birthdayRole = role
            break
    if birthdayRole is None:
        await interaction.edit_original_response(content="No Birthday role found.")
        return

    birthdays = json.load(open("Birthdays.json", 'r'))
    today = datetime.date.today()
    for person in birthdays:
        member = interaction.guild.get_member(person["ID"])
        if member is None:
            continue

        personBirthday = datetime.datetime.fromisoformat(person["Birthday"])
        if personBirthday.day == today.day and personBirthday.month == today.month:
            try:
                await member.add_roles(birthdayRole, reason = "It's their birthday!")
            except discord.HTTPException as e:
                if e.status == 403:
                    await interaction.edit_original_response(content="I don't have permission to give the Birthday role!")
                    return
                else:
                    await interaction.edit_original_response(content="Unknown error giving role (" + str(e.status) + ")!")
                    return
        else:
            try:
                await member.remove_roles(birthdayRole, reason = "It'sn't their birthday :(")
            except discord.HTTPException as e:
                if e.status == 403:
                    await interaction.edit_original_response(content="I don't have permission to remove the Birthday role!")
                    return
                else:
                    await interaction.edit_original_response(content="Unknown error giving role (" + str(e.status) + ")!")
                    return
    await interaction.edit_original_response(content="Done!")



@tree.command(name="createbirthdayevents", guilds = GUILDS)
async def createBirthdayEvents(interaction):
    birthdays = json.load(open("Birthdays.json", 'r'))
    birthdaysByUserID = {}
    for person in birthdays:
        if interaction.guild.get_member(person["ID"]):
            birthdaysByUserID[person["ID"]] = person
    
    eventCount = 0

    await interaction.response.send_message("Working...")
    events = None
    events = await interaction.guild.fetch_scheduled_events()

    for person in birthdaysByUserID.values():
        print("Checking " + person["Name"])
        hasEvent = False
        for event in events:
            if event.name == person["Name"] + "'s Birthday":
                print(person["Name"] + " already has an event: " + str(event))
                hasEvent = True
                break
        if not hasEvent:
            today = datetime.date.today()
            birthday = datetime.datetime.fromisoformat(person["Birthday"])
            eventDate = datetime.datetime(today.year if ((birthday.month > today.month) or ((birthday.month == today.month) and birthday.day >= today.day)) else today.year+1, birthday.month, birthday.day, hour=0, minute=0, second=0, microsecond=0)
            eventEndDate = eventDate + datetime.timedelta(1.0)
            if eventDate < datetime.datetime.today():
                print(eventDate)
                eventDate = datetime.datetime.today() + datetime.timedelta(minutes=1)
                print(eventDate)
            try:
                print("Making event.")
                await interaction.guild.create_scheduled_event(name = person["Name"] + "'s Birthday", start_time = pytz.timezone("America/Chicago").localize(eventDate), end_time = pytz.timezone("America/Chicago").localize(eventEndDate), privacy_level = discord.PrivacyLevel.guild_only, location = "N/a", entity_type = discord.EntityType.external)
            except discord.HTTPException as e:
                print("Except")
                if e.status == 400:
                    await interaction.edit_original_response(content="Trying to schedule an event in the past!")
                    return
                else:
                    await interaction.edit_original_response(content="Unknown error scheduling event (" + str(e.status) + ")!")
                    return
            eventCount += 1
    await interaction.edit_original_response(content="Done! Created " + str(eventCount) + (" events." if not (eventCount) == 1 else " event."))

client.run(BOT_TOKEN)