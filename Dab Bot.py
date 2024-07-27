import discord
from discord import app_commands
import json
import datetime
import pytz
import re

data = json.load(open("Store.json", 'r'))

managedMessages: list[tuple[discord.Message, discord.TextChannel]] = []

DELILAH_ID = data["DELILAH_ID"]
MY_ID = data["MY_ID"]
BOT_TOKEN = data["BOT_TOKEN"]
GUILDS = [discord.Object(guildID) for guildID in data["GUILD_IDS"]]

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.guild_reactions = True
intents.message_content = True

client = discord.Client(intents=intents)
#bot = commands.Bot(command_prefix='!', intents=intents)

tree = app_commands.CommandTree(client)

@client.event
async def on_ready():
    for guild1 in GUILDS:
        print(guild1)
        await tree.sync(guild=guild1)
    print(f'We have logged in as {client.user}')
    await init()
    print("Setup done")

@client.event
async def on_message(message: discord.Message):
    return
    if message.author == client.user:
        return

    messageText = message.content.lower()

    if "dee" in messageText:
        await message.channel.send("'s nuts!")
        await message.channel.send("HA!")
        await message.channel.send("GOTEEM!")

@client.event
async def on_guild_channel_delete(channel: discord.GroupChannel):
    i = 0
    while i < len(managedMessages):
        if managedMessages[i][1].id == channel.id:
            managedMessages.pop(i)
            return
        i += 1

@client.event
async def on_raw_reaction_add(event: discord.RawReactionActionEvent):
    if event.user_id == client.user.id:
        return
    if not (str(event.emoji) == "👺"):
        #print("Wrong emoji")
        return
    for message, channel in managedMessages:
        if event.message_id == message.id:
            try:
                await channel.set_permissions(target = event.member, overwrite=discord.PermissionOverwrite(read_messages = True))
            except discord.HTTPException as e:
                if e.status == 403:
                    await message.reply("I don't have permission to edit channel permissions!", mention_author=False)
                    return
                else:
                    await message.reply(f"Unknown error editing permissions: {int(e.status)}!", mention_author=False)
                    return
            return

@client.event
async def on_raw_reaction_remove(event: discord.RawReactionActionEvent):
    if event.user_id == client.user.id:
        return
    if not (str(event.emoji) == "👺"):
        #print("Wrong emoji")
        return
    for message, channel in managedMessages:
        if event.message_id == message.id:
            try:
                await channel.set_permissions(target = await channel.guild.fetch_member(event.user_id), overwrite=None)
            except discord.HTTPException as e:
                if e.status == 403:
                    await message.reply("I don't have permission to edit channel permissions!", mention_author=False)
                    return
                else:
                    await message.reply(f"Unknown error editing permissions: {int(e.status)}!", mention_author=False)
                    return
            return

async def getManagedMessage(channel: discord.TextChannel) -> discord.Message | None:
    text = channel.topic
    if text is None:
        return
    messageId: list[str] = re.findall(pattern = "Linked message: https://discord.com/channels/\\d+/\\d+/\\d+", string = text)
    #print(messageId, text)
    if len(messageId) > 0:
        #print(messageId[0].split("/"))
        return await (await channel.guild.fetch_channel(int(messageId[0].split("/")[-2]))).fetch_message(int(messageId[0].split("/")[-1]))
    
async def updateChannelPerms(channel: discord.TextChannel, message: discord.Message):
    async for member in channel.guild.fetch_members():
        if not (member.id == client.user.id):
            try:
                await channel.set_permissions(member, overwrite=None)
            except discord.HTTPException as e:
                if e.status == 403:
                    await channel.send("I don't have permission to edit channel permissions!")
                    return
                else:
                    await channel.send(f"Unknown error editing permissions: {int(e.status)}!")
                    return
    
    for reaction in message.reactions:
        if str(reaction.emoji) == "👺":
            users = [user async for user in reaction.users()]
            for user in users:
                if user.id == client.user.id:
                    continue
                try:
                    await channel.set_permissions(user, overwrite = discord.PermissionOverwrite(read_messages = True))
                except discord.HTTPException as e:
                    if e.status == 403:
                        await channel.send("I don't have permission to edit channel permissions!")
                        return
                    else:
                        await channel.send(f"Unknown error editing permissions: {int(e.status)}!")
                        return

async def init():
    async for guild in client.fetch_guilds():
        for channel in (await guild.fetch_channels()):
            if isinstance(channel, discord.TextChannel):
                managedMessage = await getManagedMessage(channel)
                if managedMessage is None:
                    continue
                managedMessages.append((managedMessage, channel))
                await updateChannelPerms(channel, managedMessage)

async def makeScheduledEventChannel(name: str, day: datetime.date, guild: discord.Guild, message: discord.Message):
    channels = await guild.fetch_channels()
    plans = None
    for channel in channels:
        if isinstance(channel, discord.CategoryChannel) and channel.name.lower() == "plans":
            plans = channel
            break
    
    if plans is None:
        plans = await guild.create_category_channel("plans", overwrites={guild.default_role: discord.PermissionOverwrite(read_messages = False), guild.me: discord.PermissionOverwrite(read_messages=True, manage_channels=True)},reason=None, position=0)

    return await guild.create_text_channel(name = name, reason = "Making scheduled event", category=plans, news=False, overwrites={guild.default_role: discord.PermissionOverwrite(read_messages=False), guild.me: discord.PermissionOverwrite(read_messages=True, manage_channels=True)},
                                           position = len(plans.text_channels), topic=f"Managed by {guild.me.mention}\nPlan channel for {name} on {day}.\nLinked message: {message.jump_url}",
                                           slowmode_delay=0, nsfw=False)

@tree.command(name = "plan", description = "Makes a plan channel whose permissions are linked to a message's reactions.", guilds = GUILDS)
@app_commands.describe(name="The name of the event", date = "The date of the event")
async def plan(interaction: discord.Interaction, name: str, date: str):
    day = None
    await interaction.response.send_message("Working...")
    try:
        day = datetime.date.fromisoformat(date)
    except ValueError:
        await interaction.edit_original_response("Error: Invalid date!")
        return
    
    message = await interaction.channel.send(f"React with 👺 to get access to the channel for {name}")
    await message.add_reaction("👺")

    try:
        channel = await makeScheduledEventChannel(name, day, interaction.guild, message)
        managedMessages.append((message, channel))
        await interaction.edit_original_response(content="Done!")
    except discord.HTTPException as e:
        if e.status == 403:
            await interaction.edit_original_response(content="I don't have permission to make channels!")
            return
        else:
            await interaction.edit_original_response(content="Unknown error making channel (" + str(e.status) + ")!")
            return


@tree.command(name = "birthday", description = "Checks whether the birthday roles need to be updated.", guilds = GUILDS)
async def birthday(interaction: discord.Interaction):
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
async def createBirthdayEvents(interaction: discord.Interaction):
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
            if (person["Name"].lower() in event.name.lower()) and ("birthday" in event.name.lower()):
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