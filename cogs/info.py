import discord
from discord.ext import commands
from discord import app_commands, Interaction

class InfoCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="📖 Lihat daftar perintah bot")
    async def help_cmd(self, interaction: Interaction):
        help_text = (
            "**📖 Daftar Perintah:**\n"
            "🕒 `/convert` – Konversi zona waktu.\n"
            "🔢 `/hitung` – Hitung ekspresi matematika.\n"
            "📅 `/input`, `/event`, `/eventedit`, `/eventdelete` – Manajemen event.\n"
            "📋 `/listgarapan`, `/inputgarapan`, `/editgarapan`, `/hapusgarapan` – Manajemen garapan.\n"
            "ℹ️ `/about` – Info tentang bot.\n"
            "📊 `/stats` – Statistik bot."
        )
        await interaction.response.send_message(help_text, ephemeral=True)

    @app_commands.command(name="about", description="ℹ️ Tampilkan info tentang bot")
    async def about_cmd(self, interaction: Interaction):
        embed = discord.Embed(title="🤖 Tentang Bot", color=discord.Color.blurple())
        embed.add_field(name="Versi", value="1.0.0", inline=True)
        embed.add_field(name="Creator", value="Ajoika_Feb & Kucingnya", inline=True)
        embed.add_field(name="Framework", value="discord.py (Cogs)", inline=False)
        embed.set_footer(text="Dibuat dengan ❤️ dan kopi")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="stats", description="📊 Statistik bot (server & user)")
    async def stats_cmd(self, interaction: Interaction):
        total_guilds = len(self.bot.guilds)
        total_users = len(set(self.bot.get_all_members()))
        embed = discord.Embed(title="📊 Statistik Bot", color=discord.Color.green())
        embed.add_field(name="Server", value=str(total_guilds))
        embed.add_field(name="Pengguna unik", value=str(total_users))
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(InfoCog(bot))
