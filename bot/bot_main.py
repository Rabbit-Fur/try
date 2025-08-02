"""bot_main.py – Startpunkt für den Discord-Bot im FUR-System.

Unterstützt echten Discord.py-Bot oder Stub/Webhook-Modus je nach ENV.
"""

import asyncio
import logging
import os

import aiohttp

from config import Config

from .dm_scheduler import schedule_dm_tasks, scheduler
from .translator import MyTranslator

# 🧠 Umschalten zwischen echtem Bot & Stub-Modus (z. B. für Web-Dashboard)
USE_DISCORD_BOT = os.getenv("ENABLE_DISCORD_BOT", "false").lower() == "true"

if USE_DISCORD_BOT:
    import discord
    from discord.ext import commands
else:
    import discord_util as discord
    from discord_util import Client as BotStub

    class commands:  # type: ignore
        Bot = BotStub


# 🔧 Logging
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ✅ Intents konfigurieren
intents = discord.Intents.all()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = None  # Globales Bot-Objekt für externe Nutzung


async def create_bot() -> commands.Bot:
    """Initialisiert eine Bot-Instanz (echter Discord-Bot oder Stub)."""
    connector = aiohttp.TCPConnector(resolver=aiohttp.AsyncResolver())

    if USE_DISCORD_BOT:
        new_bot = commands.Bot(command_prefix="!", intents=intents, connector=connector)
        await new_bot.tree.set_translator(MyTranslator())

        @new_bot.event
        async def on_ready():
            log.info("✅ Eingeloggt als %s (ID: %s)", new_bot.user, new_bot.user.id)
            if not scheduler.running:
                schedule_dm_tasks(new_bot)

    else:
        new_bot = BotStub()
        log.info("🧪 Bot-Stub aktiv (kein Gateway, nur Simulation)")
        if hasattr(new_bot, "tree"):
            await new_bot.tree.set_translator(MyTranslator())

    return new_bot


async def load_extensions(bot_instance: commands.Bot):
    """Lädt alle aktiven Bot-Cogs."""
    extensions = [
        "bot.cogs.error_handler",
        "bot.cogs.reminder_autopilot",
        "bot.cogs.reminder_optout",
        "bot.cogs.dm_broadcast_cog",
        "bot.cogs.base_commands",
        "bot.cogs.leaderboard",
        "bot.cogs.newsletter_optout",
        "bot.cogs.newsletter_autopilot",
        "bot.cogs.newsletter",
        "bot.cogs.reminders",
        "bot.cogs.reminder_cog",
        "bot.cogs.intro_cog",
        "bot.cogs.reaction_signup",
        "bot.cogs.calendar_cog",
        # "bot.cogs.reminder_sender_cog",  # falls später aktiv
    ]

    for ext in extensions:
        try:
            await bot_instance.load_extension(ext)
            log.info("🔗 Cog geladen: %s", ext)
        except Exception as e:
            log.error("❌ Fehler beim Laden von %s: %s", ext, e)


async def run_bot(max_retries: int = 3) -> None:
    """Startet den Discord-Bot mit Retry-Mechanismus."""
    global bot
    bot = await create_bot()

    if USE_DISCORD_BOT:
        await load_extensions(bot)

        for attempt in range(1, max_retries + 1):
            try:
                await bot.start(Config.DISCORD_TOKEN)
                return
            except aiohttp.ClientConnectorError as e:
                log.warning("🌐 DNS-Verbindungsfehler (%s/%s): %s", attempt, max_retries, e)
                if attempt == max_retries:
                    log.critical("❌ Discord-Gateway dauerhaft unerreichbar.", exc_info=True)
                    raise
                await asyncio.sleep(5)
            except Exception as e:
                log.critical("❌ Discord-Bot-Start fehlgeschlagen: %s", e, exc_info=True)
                raise
    else:
        # Stub-Bot ohne echte Verbindung (z. B. im Web-Modus)
        bot.run("FAKE_TOKEN")


def is_ready() -> bool:
    """Prüft, ob der Bot bereit ist.

    Gibt ``True`` zurück, wenn das Bot-Objekt initialisiert und einsatzbereit ist.
    """
    return bot is not None and getattr(bot, "is_ready", lambda: False)()


def main() -> None:
    """Synchroner Startpunkt für manuelles Ausführen."""
    try:
        log.info("🚀 Discord-Bot wird gestartet...")
        asyncio.run(run_bot())
    except Exception as e:
        log.critical("❌ Bot konnte nicht gestartet werden: %s", e, exc_info=True)


def run_bot_sync() -> None:
    """Alias für den Bot-Start aus anderen Kontexten."""
    main()
