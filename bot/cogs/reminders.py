"""reminders_cog.py – Stündliche Erinnerungen + manuell per Slash-Command/Web."""

import logging
import os
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands, tasks

from config import Config, is_production
from fur_lang.i18n import t

log = logging.getLogger(__name__)
ENABLE_CHANNEL_REMINDERS = os.getenv("ENABLE_CHANNEL_REMINDERS", "false").lower() == "true"


class Reminders(commands.Cog):
    """
    Reminder-Cog für wiederkehrende Systemnachrichten (Events, Quests etc.).

    - Stündlicher Task (UTC)
    - Dynamische Sprachunterstützung via t()
    - /reminder_now für manuelles Auslösen durch Admins
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.channel_id = int(
            os.getenv("REMINDER_CHANNEL_ID", getattr(Config, "REMINDER_CHANNEL_ID", 0))
        )
        self.reminder_loop.start()

    def cog_unload(self):
        """Stoppt den Loop sauber beim Entladen."""
        self.reminder_loop.cancel()

    @tasks.loop(minutes=60)
    async def reminder_loop(self):
        """Sendet jede Stunde eine Erinnerungsnachricht an den Reminder-Channel."""
        if not ENABLE_CHANNEL_REMINDERS:
            return
        if not is_production():
            log.info("DM skipped in dev mode")
            return

        now = datetime.utcnow().strftime("%H:%M")
        channel = self.bot.get_channel(self.channel_id)

        if not channel:
            log.warning(f"⚠️ Reminder-Channel {self.channel_id} nicht gefunden.")
            return

        try:
            message = t("reminder_hourly", time=now, lang="de")  # 🔁 ggf. Lokalisierung dynamisch
            await channel.send(message)
            log.info(f"📤 Reminder gesendet an Channel {self.channel_id} (UTC {now})")
        except Exception as e:
            log.error(f"❌ Fehler beim Reminder-Versand: {e}", exc_info=True)

    @reminder_loop.before_loop
    async def before_reminder(self):
        """Wartet, bis Bot bereit ist (verhindert race conditions)."""
        await self.bot.wait_until_ready()

    #
    # ✅ Manuelles Auslösen per Slash-Command
    #

    @app_commands.command(
        name=app_commands.locale_str("cmd_reminder_now_name"),
        description=app_commands.locale_str("cmd_reminder_now_desc"),
    )
    async def reminder_now(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(t("no_permission"), ephemeral=True)
            return

        if not is_production():
            await interaction.response.send_message("DM skipped in dev mode", ephemeral=True)
            log.info("DM skipped in dev mode")
            return

        channel = self.bot.get_channel(self.channel_id)
        now = datetime.utcnow().strftime("%H:%M")

        if not channel:
            await interaction.response.send_message(t("reminder_channel_missing"), ephemeral=True)
            return

        try:
            message = t("reminder_hourly", time=now, lang="de")
            await channel.send(message)
            await interaction.response.send_message(t("reminder_sent"), ephemeral=True)
            log.info(f"📤 Manueller Reminder von {interaction.user.display_name}")
        except Exception as e:
            log.error(f"❌ Fehler beim manuellen Reminder-Versand: {e}", exc_info=True)
            await interaction.response.send_message(t("send_failed"), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Reminders(bot))
