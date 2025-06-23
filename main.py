import discord
from discord.ext import commands
import asyncio
import os


TOKEN = "Token"

intents = discord.Intents.default()

bot = commands.Bot(command_prefix="!", intents=intents)

async def load_all_cogs():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py") and not filename.startswith("_"):
            module = f"cogs.{filename[:-3]}"
            try:
                await bot.load_extension(module)
                print(f"✅ Loaded: {module}")
            except Exception as e:
                print(f"❌ Gagal load {module}: {e}")

@bot.event
async def on_ready():
    print(f"✅ Bot aktif sebagai {bot.user} (ID: {bot.user.id})")

async def main():
    async with bot:
        await load_all_cogs()
        await bot.start(TOKEN)

asyncio.run(main())

