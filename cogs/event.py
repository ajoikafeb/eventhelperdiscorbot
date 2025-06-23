import discord
import json
import re
import datetime
import os
import pytz
from discord import app_commands, Interaction, SelectOption
from discord.ext import commands, tasks
from discord.ui import View, Select, Modal, TextInput

EVENT_FILE = "events.json"
ROLE_MEMBER = 1362625935727399022
ROLE_SBX = 1382262425998594153

DATE_REGEX = re.compile(r"^\d{1,2}/\d{1,2}/\d{4}$")
TIME_REGEX = re.compile(r"^([01]?\d|2[0-3]):[0-5]\d$")

def valid_date(s: str): return bool(DATE_REGEX.match(s)) and valid_dt(s)
def valid_dt(s): 
    try: datetime.datetime.strptime(s, "%d/%m/%Y"); return True
    except: return False
def valid_time(s: str): return bool(TIME_REGEX.match(s))

TIME_ZONES = {
    "WIB": "Asia/Jakarta", "WITA": "Asia/Makassar", "WIT": "Asia/Jayapura",
    "EST": "America/New_York", "PST": "America/Los_Angeles", "CET": "Europe/Berlin",
    "GMT": "GMT", "UTC": "UTC", "AEST": "Australia/Sydney"
}

def load_events():
    return json.load(open(EVENT_FILE)) if os.path.exists(EVENT_FILE) else []

def save_events(events):
    json.dump(events, open(EVENT_FILE, "w"), indent=4)

def is_expired(tanggal, jam):
    try:
        dt = datetime.datetime.strptime(f"{tanggal} {jam}", "%d/%m/%Y %H:%M")
        dt = pytz.utc.localize(dt)
        return dt < datetime.datetime.now(pytz.utc)
    except:
        return False

# ─── UI COMPONENTS ───
class DeleteSelect(Select):
    def __init__(self, events):
        super().__init__(placeholder="Pilih event untuk dihapus",
                         custom_id="delete_select",
                         min_values=1, max_values=1,
                         options=[SelectOption(label=e["nama"],
                                               description=f"{e['hari']} {e['tanggal']} ⏰{e['jam']}",
                                               value=e["nama"]) for e in events])
        self.events = events

    async def callback(self, ctx: Interaction):
        name = self.values[0]
        data = load_events()
        save_events([e for e in data if e["nama"] != name])
        await ctx.response.edit_message(content=f"✅ Event **{name}** berhasil dihapus.", view=None)

class DeleteView(View):
    def __init__(self, events):
        super().__init__(timeout=None)
        self.add_item(DeleteSelect(events))

class EventSelect(Select):
    def __init__(self, events):
        super().__init__(placeholder="Pilih event untuk edit",
                         custom_id="edit_event_select",
                         min_values=1, max_values=1,
                         options=[SelectOption(label=e["nama"],
                                               description=f"{e['hari']} {e['tanggal']} ⏰{e['jam']} 🔐{e['akses']}",
                                               value=e["nama"]) for e in events])
        self.events = events

    async def callback(self, inter: Interaction):
        ev = next(e for e in self.events if e["nama"] == self.values[0])
        await inter.response.send_message("Pilih field untuk diubah:", view=FieldSelectView(ev), ephemeral=True)

class SelectEditView(View):
    def __init__(self, events):
        super().__init__(timeout=None)
        self.add_item(EventSelect(events))

class FieldSelect(Select):
    def __init__(self, ev):
        super().__init__(placeholder="Pilih field",
                         custom_id="field_select",
                         min_values=1, max_values=1,
                         options=[SelectOption(label=field.capitalize(), value=field)
                                  for field in ["nama", "sumber", "hari", "tanggal", "jam", "akses"]])
        self.ev = ev

    async def callback(self, inter: Interaction):
        await inter.response.send_modal(EditOneFieldModal(self.ev, self.values[0]))

class FieldSelectView(View):
    def __init__(self, ev):
        super().__init__(timeout=None)
        self.add_item(FieldSelect(ev))

class EditOneFieldModal(Modal):
    new_val = TextInput(label="Nilai baru", required=True, min_length=1, max_length=100)

    def __init__(self, ev, field):
        super().__init__(title=f"Edit {field} – {ev['nama']}")
        self.ev = ev
        self.field = field
        existing = ev[field].lstrip("@") if field == "akses" else ev[field]
        self.new_val.default = existing

    async def on_submit(self, inter: Interaction):
        val = self.new_val.value.strip()
        f = self.field

        if f == "tanggal" and not valid_date(val):
            return await inter.response.send_message("⚠️ Format tanggal salah (DD/MM/YYYY)", ephemeral=True)
        if f == "jam" and not valid_time(val):
            return await inter.response.send_message("⚠️ Format jam salah (HH:MM)", ephemeral=True)
        if f == "akses":
            vv = val.lower()
            if vv not in ["member", "sbx"]:
                return await inter.response.send_message("⚠️ Akses harus member atau sbx.", ephemeral=True)
            val = vv

        data = load_events()
        for e in data:
            if e["nama"] == self.ev["nama"]:
                e[f] = f"@{val}" if f == "akses" else val
        save_events(data)
        await inter.response.send_message(f"✅ `{f}` event **{self.ev['nama']}** diperbarui.", ephemeral=True)

# ─── MAIN COG ───
class EventCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cleanup_expired.start()

    @tasks.loop(seconds=60)
    async def cleanup_expired(self):
        data = load_events()
        new_data = [e for e in data if not is_expired(e["tanggal"], e["jam"])]
        if len(new_data) != len(data):
            save_events(new_data)
            print("🗑️ Event expired dibersihkan.")

    @cleanup_expired.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.tree.sync()
        self.bot.add_view(DeleteView(load_events()))
        self.bot.add_view(SelectEditView(load_events()))
        print(f"✅ Bot siap! Logged in as {self.bot.user}")

    @app_commands.command(name="convert", description="🕒 Konversi waktu antar zona waktu")
    @app_commands.describe(dari="Zona waktu sumber", ke="Zona waktu target", jam="HH:MM")
    async def convert(self, interaction: Interaction, dari: str, ke: str, jam: str):
        try:
            if dari not in TIME_ZONES or ke not in TIME_ZONES:
                return await interaction.response.send_message("⚠ Zona waktu tidak valid!", ephemeral=True)
            if not valid_time(jam):
                return await interaction.response.send_message("⚠ Format waktu salah!", ephemeral=True)

            today = datetime.datetime.now().strftime("%d/%m/%Y")
            source_dt = datetime.datetime.strptime(f"{today} {jam}", "%d/%m/%Y %H:%M")
            source_dt = pytz.timezone(TIME_ZONES[dari]).localize(source_dt)
            target_dt = source_dt.astimezone(pytz.timezone(TIME_ZONES[ke]))

            await interaction.response.send_message(
                f"⏱ **Konversi Waktu**\n🔄 Dari {dari} {source_dt.strftime('%d/%m/%Y %H:%M')}\n"
                f"➡️ Ke {ke} {target_dt.strftime('%d/%m/%Y %H:%M')}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"⚠ Terjadi kesalahan: {str(e)}", ephemeral=True)

    @convert.autocomplete("dari")
    @convert.autocomplete("ke")
    async def autocomplete_tz(self, interaction: Interaction, current: str):
        return [app_commands.Choice(name=tz, value=tz) for tz in TIME_ZONES if current.lower() in tz.lower()]

    @app_commands.command(name="hitung", description="🔢 Hitung ekspresi matematika.")
    @app_commands.describe(expr="Ekspresi matematika")
    async def hitung(self, interaction: Interaction, expr: str):
        try:
            result = eval(expr, {"__builtins__": None}, {})
            await interaction.response.send_message(f"Hasil: `{result:,.0f}`", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"⚠ Terjadi kesalahan: {str(e)}", ephemeral=True)

    @app_commands.command(name="input", description="➕ Tambah event baru")
    @app_commands.describe(nama="Nama", sumber="Sumber", hari="Hari",
                           tanggal="DD/MM/YYYY", jam="HH:MM", akses="member/sbx")
    async def cmd_input(self, inter: Interaction, nama: str, sumber: str, hari: str, tanggal: str, jam: str, akses: str):
        if not valid_date(tanggal): 
            return await inter.response.send_message("⚠️ Tanggal salah.", ephemeral=True)
        if not valid_time(jam): 
            return await inter.response.send_message("⚠️ Jam salah.", ephemeral=True)
        if akses.lower() not in ["member", "sbx"]:
            return await inter.response.send_message("⚠️ Akses hanya member atau sbx.", ephemeral=True)

        data = load_events()
        data.append({
            "nama": nama.strip(), "sumber": sumber.strip(), "hari": hari.strip(),
            "tanggal": tanggal, "jam": jam, "akses": f"@{akses.lower()}"
        })
        save_events(data)
        await inter.response.send_message(f"✅ Event **{nama}** berhasil ditambahkan.", ephemeral=True)

    @app_commands.command(name="event", description="📅 Tampilkan daftar event")
    async def cmd_event(self, inter: Interaction):
        roles = [r.id for r in inter.user.roles]
        events = load_events()
        if ROLE_SBX in roles:
            filtered = events
        elif ROLE_MEMBER in roles:
            filtered = [e for e in events if e["akses"] == "@member"]
        else:
            return await inter.response.send_message("⚠️ Tidak punya akses.", ephemeral=True)

        filtered.sort(key=lambda e: datetime.datetime.strptime(f"{e['tanggal']} {e['jam']}", "%d/%m/%Y %H:%M"))

        if not filtered:
            return await inter.response.send_message("📭 Tidak ada event.", ephemeral=True)

        emb = discord.Embed(title="📅 Event List", color=discord.Color.green())
        for e in filtered:
            emb.add_field(
                name=e["nama"],
                value=f"💬 {e['sumber']}\n{e['hari']}, {e['tanggal']} ⏰{e['jam']} 🔐{e['akses']}",
                inline=False
            )
        await inter.response.send_message(embed=emb, ephemeral=True)

    @app_commands.command(name="eventdelete", description="🗑️ Hapus event lewat dropdown")
    async def cmd_eventdelete(self, inter: Interaction):
        events = load_events()
        if not events:
            return await inter.response.send_message("📭 Tidak ada event.", ephemeral=True)
        await inter.response.send_message("Pilih event untuk dihapus:", view=DeleteView(events), ephemeral=True)

    @app_commands.command(name="eventedit", description="✏️ Edit event dari dropdown")
    async def cmd_eventedit(self, inter: Interaction):
        events = load_events()
        if not events:
            return await inter.response.send_message("📭 Tidak ada event.", ephemeral=True)
        await inter.response.send_message("Pilih event untuk diedit:", view=SelectEditView(events), ephemeral=True)

# ─── SETUP FUNCTION ───
async def setup(bot: commands.Bot):
    await bot.add_cog(EventCog(bot))
