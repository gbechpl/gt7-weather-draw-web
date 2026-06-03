import random
import discord
from discord import app_commands


# --- INICJALIZACJA BOTA ---
class GT7Bot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())

    async def on_ready(self):
        await self.wait_until_ready()
        print(f"🏎️ Bot GT7 (Fast Code Format) gotowy! Zalogowano jako {self.user}")
        print("💡 Jeśli zaktualizowałeś kod, wpisz na czacie jako admin: !sync")


client = GT7Bot()
tree = app_commands.CommandTree(client)

# --- BAZA KAFELKÓW GT7 ---
S_SUN = [
    "S01 ☀️",
    "S02 ☀️",
    "S03 🌤️",
    "S04 🌤️",
    "S05 ☀️",
    "S06 ☀️",
    "S07 ☀️",
    "S08 🌤️",
    "S09 🌤️",
    "S10 🌤️",
    "S11 🌤️",
    "S12 🌤️",
    "S13 ☀️",
    "S14 🌤️",
    "S15 ☀️",
    "S16 ☀️",
    "S17 🌤️",
    "S18 🌤️",
]

C_CLOUD = ["C01 ☁️", "C02 ☁️", "C03 ☁️", "C04 ☁️", "C05 ☁️", "C06 ⛈️"]

R_RAIN = ["R01 🌧️", "R02 🌧️", "R03 🌧️", "R04 🌧️", "R05 🌧️", "R06 🌧️", "R07 ⛈️", "R08 ⛈️"]


# --- PODPOWIEDZI (AUTOCOMPLETE) ---
async def kod_autocomplete(
    interaction: discord.Interaction, current: str
) -> list[app_commands.Choice[str]]:
    # Lista najczęściej używanych kombinacji w lidze PGRT
    opcje = ["m9", "m5", "m3", "d9", "d5", "d3", "b9", "b5", "w9", "w5", "w3"]
    return [
        app_commands.Choice(name=opt.upper(), value=opt.lower())
        for opt in opcje
        if current.lower() in opt
    ]


# --- KOMENDA /POGODA ---
@tree.command(
    name="pogoda",
    description="Generuje pogodę za pomocą szybkiego kodu (np. m9, d5, w3)",
)
@app_commands.autocomplete(kod=kod_autocomplete)
async def pogoda(interaction: discord.Interaction, kod: str):
    # Oczyszczamy wpisany kod z białych znaków i zmieniamy na małe litery
    czysty_kod = kod.strip().lower()

    # Sprawdzamy czy kod ma poprawny format (np. litera + cyfra)
    if (
        len(czysty_kod) < 2
        or not czysty_kod[0].isalpha()
        or not czysty_kod[1:].isdigit()
    ):
        await interaction.response.send_message(
            "❌ Błędny format! Wpisz np. `m9` (Mixed 9 slotów), `d5` (Dry 5 slotów) itp.",
            ephemeral=True,
        )
        return

    prefiks_profilu = czysty_kod[0]
    sloty = int(czysty_kod[1:])

    # Walidacja liczby slotów zgodna z Waszymi założeniami (3-9)
    if sloty < 3 or sloty > 9:
        await interaction.response.send_message(
            "❌ Liczba slotów musi mieścić się w przedziale od 3 do 9! (np. `m6`)",
            ephemeral=True,
        )
        return

    pula_pogodowa = []
    nazwa_profilu = ""

    if prefiks_profilu == "d":
        pula_pogodowa = S_SUN.copy()
        nazwa_profilu = "D (DRY)"
    elif prefiks_profilu == "b":
        pula_pogodowa = S_SUN + C_CLOUD
        nazwa_profilu = "B (BALANCED)"
    elif prefiks_profilu == "m":
        pula_pogodowa = S_SUN + C_CLOUD + R_RAIN
        nazwa_profilu = "M (MIXED)"
    elif prefiks_profilu == "w":
        pula_pogodowa = [C_CLOUD[4], C_CLOUD[5]] + R_RAIN
        nazwa_profilu = "W (WET)"
    else:
        await interaction.response.send_message(
            "❌ Nieznany profil! Użyj: **D**, **B**, **M** lub **W**.", ephemeral=True
        )
        return

    # Losowanie bez powtórzeń w serii
    if len(pula_pogodowa) >= sloty:
        wylosowane_sloty = random.sample(pula_pogodowa, sloty)
    else:
        wylosowane_sloty = random.choices(pula_pogodowa, k=sloty)

    # Budowanie prostej i ultrawydajnej odpowiedzi tekstowej
    tresc_wiadomosci = [f"### 🌤️ WEATHER GENERATOR for GT7 • PRESET {nazwa_profilu}"]

    for i, stan in enumerate(wylosowane_sloty, 1):
        tresc_wiadomosci.append(f"**Slot {i}:** **{stan}**")

    tresc_wiadomosci.append(f"\n*Gran Turismo 7 Official Preset • Slots: {sloty}*")
    pelny_tekst = "\n".join(tresc_wiadomosci)

    # Błyskawiczny strzał do Discorda bez lagogennych deferów
    await interaction.response.send_message(pelny_tekst)


# --- BEZPIECZNA SYNCHRONIZACJA KOMEND ---
@client.event
async def on_message(message):
    if message.author.bot:
        return

    if (
        message.content.lower() == "!sync"
        and message.author.guild_permissions.administrator
    ):
        await tree.sync()
        await message.channel.send(
            "✅ Nowy system szybkiego wybierania (np. m9) został zsynchronizowany!"
        )


# --- URUCHOMIENIE ---
if not DISCORD_TOKEN:
    raise RuntimeError("Brakuje DISCORD_TOKEN w zmiennej srodowiskowej albo config.py.")

client.run(DISCORD_TOKEN)
