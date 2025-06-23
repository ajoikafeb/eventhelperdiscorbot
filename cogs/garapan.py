import discord
from discord.ext import commands
from discord import app_commands, Interaction, SelectOption
from discord.ui import View, Modal, TextInput, Select, Button
import json
import os

GARAPAN_FILE = "garapan.json"
KATEGORI_OPTIONS = ["Testnet", "Depin", "Dapps"]

def load_garapan():
    return json.load(open(GARAPAN_FILE)) if os.path.exists(GARAPAN_FILE) else []

def save_garapan(data):
    json.dump(data, open(GARAPAN_FILE, "w"), indent=4)

class KategoriSelect(Select):
    def __init__(self):
        super().__init__(
            placeholder="Pilih kategori...",
            min_values=1, max_values=1,
            options=[SelectOption(label=k, value=k) for k in KATEGORI_OPTIONS],
            custom_id="kategori_select"
        )

    async def callback(self, interaction: Interaction):
        await interaction.response.send_modal(GarapanInputModal(self.values[0]))

class GarapanInputModal(Modal, title="Tambah Garapan Baru"):
    judul = TextInput(label="Judul Garapan", required=True)
    link = TextInput(label="Link Chat Discord", required=True)

    def __init__(self, kategori):
        super().__init__()
        self.kategori = kategori

    async def on_submit(self, interaction: Interaction):
        data = load_garapan()
        data.append({
            "judul": self.judul.value,
            "kategori": self.kategori,
            "link": self.link.value
        })
        save_garapan(data)
        await interaction.response.send_message(f"✅ Garapan **{self.judul.value}** berhasil ditambahkan!", ephemeral=True)

class HapusSelect(Select):
    def __init__(self, data):
        super().__init__(
            placeholder="Pilih garapan yang ingin dihapus",
            min_values=1, max_values=1,
            options=[SelectOption(label=g["judul"], value=g["judul"]) for g in data],
            custom_id="hapus_select"
        )
        self.data = data

    async def callback(self, interaction: Interaction):
        title = self.values[0]
        new_data = [g for g in self.data if g["judul"] != title]
        save_garapan(new_data)
        await interaction.response.edit_message(content=f"✅ Garapan **{title}** berhasil dihapus.", view=None)

class EditFieldSelect(Select):
    def __init__(self, garapan):
        self.garapan = garapan
        super().__init__(
            placeholder="Pilih field yang ingin diubah",
            min_values=1, max_values=1,
            options=[
                SelectOption(label="Judul", value="judul"),
                SelectOption(label="Kategori", value="kategori"),
                SelectOption(label="Link", value="link")
            ]
        )

    async def callback(self, interaction: Interaction):
        await interaction.response.send_modal(EditFieldModal(self.garapan, self.values[0]))

class EditFieldModal(Modal):
    new_value = TextInput(label="Nilai Baru", required=True)

    def __init__(self, garapan, field):
        super().__init__(title=f"Edit {field} – {garapan['judul']}")
        self.garapan = garapan
        self.field = field
        self.new_value.default = garapan[field]

    async def on_submit(self, interaction: Interaction):
        data = load_garapan()
        for g in data:
            if g["judul"] == self.garapan["judul"]:
                g[self.field] = self.new_value.value
        save_garapan(data)
        await interaction.response.send_message(f"✅ `{self.field}` garapan **{self.garapan['judul']}** diperbarui.", ephemeral=True)

class FilterKategoriSelect(Select):
    def __init__(self, original_data, update_callback):
        self.original_data = original_data
        self.update_callback = update_callback

        super().__init__(
            placeholder="Filter kategori...",
            options=[SelectOption(label=k, value=k) for k in KATEGORI_OPTIONS] +
                    [SelectOption(label="(Semua)", value="all")],
            custom_id="filter_kategori"
        )

    async def callback(self, interaction: Interaction):
        val = self.values[0]
        if val == "all":
            filtered = self.original_data
        else:
            filtered = [g for g in self.original_data if g["kategori"].lower() == val.lower()]
        await self.update_callback(interaction, filtered)

class GarapanPaginator(View):
    def __init__(self, original_data, filtered_data=None, per_page=5):
        super().__init__(timeout=120)
        self.original_data = original_data
        self.data = filtered_data or original_data
        self.per_page = per_page
        self.page = 0
        self.max_page = max((len(self.data) - 1) // self.per_page, 0)

        self.refresh_buttons()
        self.add_item(FilterKategoriSelect(self.original_data, self.apply_filter))

    def refresh_buttons(self):
        self.clear_items()
        for i in range(self.max_page + 1):
            button = Button(label=str(i + 1), style=discord.ButtonStyle.secondary)
            button.callback = self.make_page_callback(i)
            self.add_item(button)

    def make_page_callback(self, target_page):
        async def callback(interaction: Interaction):
            self.page = target_page
            self.refresh_buttons()
            self.add_item(FilterKategoriSelect(self.original_data, self.apply_filter))
            await interaction.response.edit_message(embed=self.get_embed(), view=self)
        return callback

    def get_embed(self):
        start = self.page * self.per_page
        end = start + self.per_page
        embed = discord.Embed(
            title=f"📋 Garapan (Page {self.page + 1}/{self.max_page + 1})",
            color=discord.Color.teal()
        )
        for idx, item in enumerate(self.data[start:end], start=start + 1):
            embed.add_field(
                name=f"{idx}. {item['judul']}",
                value=f"Kategori: {item['kategori']}\n🔗 {item['link']}",
                inline=False
            )
        return embed

    async def apply_filter(self, interaction: Interaction, filtered_data):
        self.data = filtered_data
        self.page = 0
        self.max_page = max((len(self.data) - 1) // self.per_page, 0)
        self.refresh_buttons()
        self.add_item(FilterKategoriSelect(self.original_data, self.apply_filter))
        await interaction.response.edit_message(embed=self.get_embed(), view=self)


class GarapanCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="listgarapan", description="📄 Tampilkan daftar garapan")
    async def listgarapan(self, interaction: Interaction):
        data = load_garapan()
        if not data:
            return await interaction.response.send_message("📭 Tidak ada garapan.", ephemeral=True)

        if len(data) <= 5:
            embed = discord.Embed(title="📋 Daftar Garapan", color=discord.Color.blue())
            for idx, item in enumerate(data, start=1):
                embed.add_field(
                    name=f"{idx}. {item['judul']}",
                    value=f"Kategori: {item['kategori']}\n🔗 {item['link']}",
                    inline=False
                )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            view = GarapanPaginator(original_data=data)
            await interaction.response.send_message(embed=view.get_embed(), view=view, ephemeral=True)

    @app_commands.command(name="inputgarapan", description="➕ Tambah garapan baru")
    async def inputgarapan(self, interaction: Interaction):
        view = View()
        view.add_item(KategoriSelect())
        await interaction.response.send_message("Pilih kategori untuk garapan:", view=view, ephemeral=True)

    @app_commands.command(name="hapusgarapan", description="🗑️ Hapus garapan dari daftar")
    async def hapusgarapan(self, interaction: Interaction):
        data = load_garapan()
        if not data:
            return await interaction.response.send_message("📭 Tidak ada data garapan.", ephemeral=True)
        view = View()
        view.add_item(HapusSelect(data))
        await interaction.response.send_message("Pilih garapan yang ingin dihapus:", view=view, ephemeral=True)

    @app_commands.command(name="editgarapan", description="✏️ Edit data garapan")
    async def editgarapan(self, interaction: Interaction):
        data = load_garapan()
        if not data:
            return await interaction.response.send_message("📭 Tidak ada garapan.", ephemeral=True)

        select = Select(
            placeholder="Pilih garapan yang ingin diedit",
            options=[SelectOption(label=g["judul"], value=g["judul"]) for g in data],
            min_values=1, max_values=1
        )

        async def callback(inter: Interaction):
            selected = next(g for g in data if g["judul"] == select.values[0])
            view = View()
            view.add_item(EditFieldSelect(selected))
            await inter.response.edit_message(content="Pilih field yang ingin diedit:", view=view)

        select.callback = callback

        view = View()
        view.add_item(select)
        await interaction.response.send_message("Pilih garapan yang ingin diedit:", view=view, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(GarapanCog(bot))
