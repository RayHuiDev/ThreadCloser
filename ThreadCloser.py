import discord
from discord.ext import commands
import aiofiles
import os
import json

ID_FILE = "saved_ids.json"
CONFIG_FILE = "config.json"



with open(CONFIG_FILE, "r") as f:
    config = json.load(f)

TOKEN = config["TOKEN"]
PREFIX = config["PREFIX"]
LOG_CHANNEL_ID = config["LOG_CHANNEL_ID"]

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

async def load_ids():
    if not os.path.exists(ID_FILE):
        return []
    async with aiofiles.open(ID_FILE, "r") as f:
        content = await f.read()
        try:
            data = json.loads(content) if content else []
            return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            return []

async def save_ids(ids):
    async with aiofiles.open(ID_FILE, "w") as f:
        await f.write(json.dumps(ids))

@bot.command()
async def close(ctx, thread_id: int):
    ids = await load_ids()
    if thread_id not in ids:
        ids.append(thread_id)
        await save_ids(ids)

    thread = bot.get_channel(thread_id)
    if isinstance(thread, discord.Thread):
        await thread.edit(archived=True)
        await ctx.send(f"Thread <#{thread_id}> is now closed")

        try:
            log_channel = await bot.fetch_channel(LOG_CHANNEL_ID)
            await log_channel.send(f"Thread <#{thread_id}> was closed by {ctx.author.mention}.")
        except discord.DiscordException as e:
            print(f"Logging error: {e}")
    else:
        await ctx.send(f"Thread with ID <#{thread_id}> not found.")

# Open command
@bot.command()
async def open(ctx, thread_id: int):
    ids = await load_ids()

    if thread_id in ids:
        ids.remove(thread_id)
        await save_ids(ids)

        try:
            thread = await ctx.guild.fetch_channel(thread_id)
            if isinstance(thread, discord.Thread):
                await thread.edit(archived=False)
                await ctx.send(f"Thread <#{thread_id}> has been reopened.")

                try:
                    log_channel = await bot.fetch_channel(LOG_CHANNEL_ID)
                    await log_channel.send(f"Thread <#{thread_id}> was reopened by {ctx.author.mention}.")
                except discord.DiscordException as e:
                    print(f"Logging error: {e}")
            else:
                await ctx.send(f"ID <#{thread_id}> is not a valid thread.")
        except discord.NotFound:
            await ctx.send(f"Thread with ID <#{thread_id}> not found in the guild.")
        except discord.Forbidden:
            await ctx.send("I don't have permission to access the thread.")
        except discord.HTTPException as e:
            await ctx.send(f"An error occurred while fetching the thread: {e}")
    else:
        await ctx.send(f"Thread ID <#{thread_id}> was not found in the list.")

@bot.event
async def on_message(message):
    await bot.process_commands(message)

    if message.channel.type == discord.ChannelType.public_thread:
        try:
            saved_ids = await load_ids()

            print(f"Saved IDs: {saved_ids}")

            if message.channel.id in saved_ids:
                await message.delete()
                await message.channel.edit(archived=True)

                async for msg in message.channel.history(limit=5):
                    if msg.type == discord.MessageType.thread_created:
                        await msg.delete()

        except Exception as e:
            print(f"Error while processing the message: {e}")

bot.run(TOKEN)
