from __future__ import annotations

import os
import argparse
from io import BytesIO
from urllib.parse import urlencode

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from discord.ext import tasks


try:
    import config
except Exception:
    config = None


DISCORD_TOKEN = os.getenv("DISCORD_TOKEN") or getattr(config, "DISCORD_TOKEN", "")
LOCAL_WEB_SERVICE_URL = "http://127.0.0.1:8000"
WEB_SERVICE_URL = ""
DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID") or getattr(config, "DISCORD_GUILD_ID", "")
KEEPALIVE_URL = os.getenv("KEEPALIVE_URL") or getattr(config, "KEEPALIVE_URL", "")
KEEPALIVE_ENABLED = os.getenv("KEEPALIVE_ENABLED", "1").strip().lower() in {"1", "true", "yes", "on"}
KEEPALIVE_INTERVAL_SECONDS = int(
    os.getenv("KEEPALIVE_INTERVAL_SECONDS") or getattr(config, "KEEPALIVE_INTERVAL_SECONDS", 600)
)

PROFILE_MAP = {
    "d": "dry",
    "b": "equal",
    "m": "mixed",
    "w": "wet",
}

PROFILE_LABELS = {
    "dry": "DRY",
    "equal": "BALANCED",
    "mixed": "MIXED",
    "wet": "WET",
}

DEFAULT_SLOT_COUNT = 9


def resolve_web_service_url() -> str:
    env_url = os.getenv("WEB_SERVICE_URL", "").strip()
    if env_url:
        return env_url.rstrip("/")

    use_local_service = os.getenv("GT7_USE_LOCAL_WEB_SERVICE", "").strip().lower()
    if use_local_service in {"1", "true", "yes", "on"}:
        return LOCAL_WEB_SERVICE_URL

    config_url = getattr(config, "WEB_SERVICE_URL", "") if config is not None else ""
    if config_url:
        return str(config_url).rstrip("/")

    return LOCAL_WEB_SERVICE_URL


def normalize_profile(profile: str) -> str:
    profile = profile.strip().lower()
    if profile in PROFILE_MAP.values():
        return profile
    if profile and profile[0] in PROFILE_MAP:
        return PROFILE_MAP[profile[0]]
    return "mixed"


def build_image_url(slot_count: int, profile: str, unique: bool, animate: bool = False) -> str:
    profile = normalize_profile(profile)
    return (
        f"{WEB_SERVICE_URL}/api/draw/image"
        f"?slot_count={slot_count}&profile={profile}&unique={'true' if unique else 'false'}&animate={'true' if animate else 'false'}"
    )


async def fetch_draw_png(image_url: str) -> bytes:
    async with aiohttp.ClientSession() as session:
        async with session.get(image_url) as response:
            if response.status != 200:
                text = await response.text()
                raise RuntimeError(f"HTTP {response.status}: {text[:300]}")
            return await response.read()


async def fetch_url_text(url: str) -> tuple[int, str]:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return response.status, await response.text()


class GT7Bot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    @tasks.loop(seconds=KEEPALIVE_INTERVAL_SECONDS)
    async def keepalive_task(self) -> None:
        if not KEEPALIVE_URL:
            return

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(KEEPALIVE_URL, headers={"Cache-Control": "no-cache"}) as response:
                    body = await response.text()
                    print(f"Keepalive ping -> HTTP {response.status}")
                    if body.strip():
                        print(body.strip())
        except Exception as exc:
            print(f"Keepalive ping failed: {exc}")

    @keepalive_task.before_loop
    async def before_keepalive_task(self) -> None:
        await self.wait_until_ready()

    async def setup_hook(self) -> None:
        if DISCORD_GUILD_ID:
            guild = discord.Object(id=int(DISCORD_GUILD_ID))
            try:
                synced = await self.tree.sync(guild=guild)
                print(f"Synced {len(synced)} slash commands to guild {DISCORD_GUILD_ID}")
            except discord.Forbidden:
                print(
                    f"Nie mam dostępu do guildy {DISCORD_GUILD_ID}. "
                    "Sprawdz, czy bot jest dodany do tego serwera i czy ID jest poprawne. "
                    "Pominieto sync guild i bot wystartuje dalej."
                )
                synced = await self.tree.sync()
                print(f"Synced {len(synced)} global slash commands")
        else:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} global slash commands")

        if KEEPALIVE_ENABLED and KEEPALIVE_URL:
            if not self.keepalive_task.is_running():
                self.keepalive_task.start()
                print(
                    f"Keepalive enabled: {KEEPALIVE_URL} "
                    f"every {KEEPALIVE_INTERVAL_SECONDS} seconds"
                )
        elif KEEPALIVE_ENABLED and not KEEPALIVE_URL:
            print("Keepalive enabled, but KEEPALIVE_URL is empty. Skipping keepalive task.")
        else:
            print("Keepalive disabled.")

    async def on_ready(self) -> None:
        print(f"GT7 bot ready as {self.user}")
        print("Prefix command: !pogoda m6")
        print("Slash command: /pogoda")

    async def close(self) -> None:
        if self.keepalive_task.is_running():
            self.keepalive_task.cancel()
        await super().close()


bot = GT7Bot()


@bot.tree.command(name="pogoda", description="Generuje obrazek wyniku losowania GT7")
@app_commands.describe(
    slot_count="Liczba slotow od 3 do 9",
    profile="Profil: dry, equal, mixed, wet",
    unique="Czy wyniki maja byc unikalne",
)
async def pogoda(
    interaction: discord.Interaction,
    slot_count: app_commands.Range[int, 3, 9] = DEFAULT_SLOT_COUNT,
    profile: str = "mixed",
    unique: bool = False,
) -> None:
    if not WEB_SERVICE_URL:
        await interaction.response.send_message(
            "Brakuje `WEB_SERVICE_URL` w config.py albo zmiennej srodowiskowej.",
            ephemeral=True,
        )
        return

    profile = normalize_profile(profile)
    image_url = build_image_url(slot_count, profile, unique, animate=False)

    await interaction.response.defer(thinking=True)

    try:
        payload = await fetch_draw_png(image_url)
    except Exception as exc:
        await interaction.followup.send(f"Nie udalo sie pobrac obrazu: {exc}", ephemeral=True)
        return

    file = discord.File(BytesIO(payload), filename="gt7-draw.png")
    embed = discord.Embed(
        title="WEATHER GENERATOR for GT7",
        description=f"Profile: {PROFILE_LABELS.get(profile, profile.upper())} | Slots: {slot_count} | Unique: {'yes' if unique else 'no'}",
        color=0x66D9EF,
    )
    embed.set_image(url="attachment://gt7-draw.png")

    await interaction.followup.send(embed=embed, file=file)


@bot.command(name="sync")
async def sync_prefix(ctx: commands.Context) -> None:
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("Brak uprawnien do synchronizacji.")
        return

    synced = await bot.tree.sync()
    await ctx.send(f"Synced {len(synced)} commands.")


@bot.command(name="status")
async def status_prefix(ctx: commands.Context) -> None:
    if not WEB_SERVICE_URL:
        await ctx.send("Brakuje WEB_SERVICE_URL.")
        return

    image_url = build_image_url(3, "mixed", False, animate=False)
    try:
        payload = await fetch_draw_png(image_url)
    except Exception as exc:
        await ctx.send(f"Web service error: {exc}")
        return

    file = discord.File(BytesIO(payload), filename="gt7-status.png")
    embed = discord.Embed(
        title="GT7 bot status",
        description="Lokalny test polaczenia z web service zakonczony sukcesem.",
        color=0x57F287,
    )
    embed.set_image(url="attachment://gt7-status.png")
    await ctx.send(embed=embed, file=file)


@bot.command(name="pogoda")
async def pogoda_prefix(ctx: commands.Context, code: str = "m9") -> None:
    if not WEB_SERVICE_URL:
        await ctx.send("Brakuje WEB_SERVICE_URL.")
        return

    code = code.strip().lower()
    if len(code) < 2 or code[0] not in PROFILE_MAP or not code[1:].isdigit():
        await ctx.send("Uzyj np. `!pogoda m6`.")
        return

    profile = PROFILE_MAP[code[0]]
    slot_count = int(code[1:])
    if slot_count < 3 or slot_count > 9:
        await ctx.send("Liczba slotow musi byc od 3 do 9.")
        return

    image_url = build_image_url(slot_count, profile, unique=False, animate=False)

    try:
        payload = await fetch_draw_png(image_url)
    except Exception as exc:
        await ctx.send(f"Nie udalo sie pobrac obrazu: {exc}")
        return

    file = discord.File(BytesIO(payload), filename="gt7-draw.png")
    embed = discord.Embed(
        title="WEATHER GENERATOR for GT7",
        description=f"Profile: {PROFILE_LABELS.get(profile, profile.upper())} | Slots: {slot_count}",
        color=0x66D9EF,
    )
    embed.set_image(url="attachment://gt7-draw.png")
    await ctx.send(embed=embed, file=file)


async def dry_run() -> None:
    print("Dry-run: sprawdzam konfiguracje bez logowania do Discorda.")

    if not DISCORD_TOKEN:
        raise RuntimeError("Brakuje DISCORD_TOKEN w config.py albo zmiennej srodowiskowej.")

    if not WEB_SERVICE_URL:
        raise RuntimeError("Brakuje WEB_SERVICE_URL w config.py albo zmiennej srodowiskowej.")

    print(f"DISCORD_TOKEN: ustawiony ({len(DISCORD_TOKEN)} znakow)")
    print(f"WEB_SERVICE_URL: {WEB_SERVICE_URL}")

    if DISCORD_GUILD_ID:
        print(f"DISCORD_GUILD_ID: {DISCORD_GUILD_ID}")
    else:
        print("DISCORD_GUILD_ID: brak, uzyje sync globalnego")

    image_url = build_image_url(3, "mixed", False, animate=False)
    print(f"Przykladowy URL obrazu: {image_url}")
    print("Dry-run zakonczony pomyslnie.")


async def check_web_service() -> None:
    print("Web-check: sprawdzam lokalny web service bez Discorda.")

    if not WEB_SERVICE_URL:
        raise RuntimeError("Brakuje WEB_SERVICE_URL w config.py albo zmiennej srodowiskowej.")

    health_url = f"{WEB_SERVICE_URL}/health"
    health_status, health_body = await fetch_url_text(health_url)
    print(f"GET {health_url} -> HTTP {health_status}")
    print(f"Health body: {health_body[:200]}")

    query = urlencode(
        {
            "slot_count": 3,
            "profile": "mixed",
            "unique": "false",
            "animate": "false",
        }
    )
    image_url = f"{WEB_SERVICE_URL}/api/draw/image?{query}"
    payload = await fetch_draw_png(image_url)
    print(f"GET {image_url} -> image bytes: {len(payload)}")
    print("Web-check zakonczony pomyslnie.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--local",
        action="store_true",
        help="Use local Flask service at http://127.0.0.1:8000",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate configuration without connecting to Discord.",
    )
    parser.add_argument(
        "--check-web",
        action="store_true",
        help="Check the Flask web service endpoint without connecting to Discord.",
    )
    args = parser.parse_args()

    if args.local:
        os.environ["GT7_USE_LOCAL_WEB_SERVICE"] = "true"

    WEB_SERVICE_URL = resolve_web_service_url()
    if not WEB_SERVICE_URL:
        raise RuntimeError("Brakuje WEB_SERVICE_URL w config.py albo zmiennej srodowiskowej.")

    if args.check_web:
        print("Using web check mode; Discord connection will be skipped.")
        print(f"Using web service: {WEB_SERVICE_URL}")
        import asyncio

        asyncio.run(check_web_service())
        raise SystemExit(0)

    if args.dry_run:
        print("Using dry-run mode; Discord connection will be skipped.")
        print(f"Using web service: {WEB_SERVICE_URL}")
        if DISCORD_GUILD_ID:
            print(f"Using guild sync for {DISCORD_GUILD_ID}")
        else:
            print("Using global sync; slash commands may appear with delay.")
        import asyncio

        asyncio.run(dry_run())
        raise SystemExit(0)

    if not DISCORD_TOKEN:
        raise RuntimeError("Brakuje DISCORD_TOKEN w config.py albo zmiennej srodowiskowej.")

    if DISCORD_GUILD_ID:
        print(f"Using guild sync for {DISCORD_GUILD_ID}")
    else:
        print("Using global sync; slash commands may appear with delay.")
    print(f"Using web service: {WEB_SERVICE_URL}")
    print("Tip: use `python bot_vs.py --local` to test against localhost.")

    bot.run(DISCORD_TOKEN)
