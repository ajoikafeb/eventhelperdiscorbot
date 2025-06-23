import discord
from discord.ext import commands
import asyncio
import os

# Ganti ini dengan token asli bot kamu
TOKEN = "Token"

# Setup intents
intents = discord.Intents.default()

# Inisialisasi bot
bot = commands.Bot(command_prefix="!", intents=intents)

# Auto-load semua file .py di folder cogs/
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

# Fungsi utama bot
async def main():
    async with bot:
        await load_all_cogs()
        await bot.start(TOKEN)

# Jalankan bot
asyncio.run(main())

