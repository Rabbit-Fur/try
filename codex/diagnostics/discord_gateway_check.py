"""Diagnostic tool for Discord gateway connectivity and scheduler events."""

from __future__ import annotations

import asyncio
import inspect
import logging
import os

import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler

log = logging.getLogger(__name__)

intents = discord.Intents.all()

bot = commands.Bot(command_prefix="!", intents=intents)

scheduler = AsyncIOScheduler()


@bot.event
async def on_ready() -> None:
    log.info("✅ Bot ist online: %s", bot.user)
    await test_gateway()
    await test_permissions()
    await analyze_check_upcoming_events()


async def test_gateway() -> None:
    try:
        gateway_url = await bot.http.static_login(bot.http.token)
        log.info("🌐 Discord Gateway-URL erreichbar: %s", gateway_url)
    except Exception as exc:  # noqa: BLE001
        log.error("❌ Gateway-Test fehlgeschlagen: %s", exc)


async def test_permissions() -> None:
    guilds = await bot.fetch_guilds(limit=5).flatten()
    for guild in guilds:
        try:
            perms = guild.me.guild_permissions
            if not perms.administrator:
                log.warning("⚠️ Keine Admin-Rechte in: %s", guild.name)
        except Exception as exc:  # noqa: BLE001
            log.error("❌ Fehler beim Rechte-Check: %s", exc)


async def analyze_check_upcoming_events() -> None:
    from bot.dm_scheduler import check_upcoming_events

    if not asyncio.iscoroutinefunction(check_upcoming_events):
        log.warning("❌ `check_upcoming_events` ist keine async-Funktion!")
        return

    source = inspect.getsource(check_upcoming_events)
    if "time.sleep" in source:
        log.warning("⏱️ `time.sleep()` gefunden – ersetze durch `await asyncio.sleep()`!")
    else:
        log.info("✅ Kein blockierender sleep gefunden.")

    if "for " in source or "while " in source:
        log.info("ℹ️ Schleifen gefunden – Stelle sicher, dass sie `await` korrekt nutzen.")


@scheduler.scheduled_job("interval", minutes=1)
async def example_check() -> None:
    await asyncio.sleep(1)
    log.info("⏰ Dummy-Event-Check ausgeführt.")


def run() -> None:
    scheduler.start()
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN not set")
    bot.run(token)


if __name__ == "__main__":
    run()
