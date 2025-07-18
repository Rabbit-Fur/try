"""MongoDB-based reminder cog with global slash commands."""

import logging
from datetime import datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands, tasks

from config import Config
from fur_lang.i18n import t
from mongo_service import get_collection
from utils.event_helpers import get_events_for, parse_event_time


def is_opted_out(user_id: int) -> bool:
    """Return True if the user opted out of reminders."""
    uid = str(user_id)
    if get_collection("reminder_optout").find_one({"discord_id": uid}):
        return True
    settings = get_collection("user_settings").find_one(
        {"discord_id": uid, "reminder_optout": True}
    )
    return bool(settings)


log = logging.getLogger(__name__)


class ReminderCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.check_reminders.start()

    def cog_unload(self) -> None:
        self.check_reminders.cancel()

    def get_user_language(self, user_id: int) -> str:
        user = get_collection("users").find_one({"discord_id": str(user_id)})
        return user.get("lang", "de") if user else "de"

    #
    # 🔄 Hintergrund-Reminder-Task (alle 5 Minuten)
    #

    @tasks.loop(minutes=5.0)
    async def check_reminders(self) -> None:
        now = datetime.utcnow()
        window_start = now + timedelta(minutes=60)
        window_end = now + timedelta(minutes=61)

        try:
            today_events = get_events_for(now)
            events = [
                ev
                for ev in today_events
                if (
                    (ev_time := parse_event_time(ev.get("event_time")))
                    and window_start <= ev_time <= window_end
                )
            ]
            for event in events:
                participants = get_collection("event_participants").find({"event_id": event["_id"]})
                for p in participants:
                    user_id = int(p["user_id"])
                    if get_collection("reminders_sent").find_one(
                        {"event_id": event["_id"], "user_id": user_id}
                    ):
                        continue

                    if is_opted_out(user_id):
                        continue
                    lang = self.get_user_language(user_id)
                    try:
                        user = self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)
                        if not user:
                            log.warning(f"User ID {user_id} not found.")
                            continue
                        msg = t("reminder_event_60min", title=event["title"], lang=lang)
                        mention = (
                            f"<@&{Config.REMINDER_ROLE_ID}> "
                            if getattr(Config, "REMINDER_ROLE_ID", 0)
                            else ""
                        )
                        await user.send(f"{mention}{msg}" if mention else msg)
                        get_collection("reminders_sent").insert_one(
                            {"event_id": event["_id"], "user_id": user_id, "sent_at": now}
                        )
                        log.info(f"📤 60-Minuten-Reminder an {user_id} gesendet.")
                    except discord.Forbidden:
                        log.warning(f"🚫 DMs deaktiviert bei User {user_id}")
                    except Exception as e:
                        log.error(f"❌ Fehler beim Senden an {user_id}: {e}")
        except Exception as e:
            log.error(f"❌ Fehler beim Reminder-Check: {e}", exc_info=True)

    @check_reminders.before_loop
    async def before_check_reminders(self) -> None:
        await self.bot.wait_until_ready()

    #
    # ✅ Slash-Commands (global)
    #

    @app_commands.command(
        name=app_commands.locale_str("cmd_remind_name"),
        description=app_commands.locale_str("cmd_remind_desc"),
    )
    @app_commands.describe(minutes=app_commands.locale_str("cmd_remind_param_minutes_desc"))
    async def remind(self, interaction: discord.Interaction, minutes: int):
        if minutes < 1 or minutes > 1440:
            await interaction.response.send_message(t("reminder_time_invalid"), ephemeral=True)
            return

        user_id = interaction.user.id
        remind_at = datetime.utcnow() + timedelta(minutes=minutes)

        get_collection("user_reminders").insert_one(
            {"user_id": str(user_id), "remind_at": remind_at, "created_at": datetime.utcnow()}
        )

        await interaction.response.send_message(
            t("reminder_saved", minutes=minutes), ephemeral=True
        )

    @app_commands.command(
        name=app_commands.locale_str("cmd_remind_list_name"),
        description=app_commands.locale_str("cmd_remind_list_desc"),
    )
    async def remind_list(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        reminders = list(get_collection("user_reminders").find({"user_id": user_id}))
        if not reminders:
            await interaction.response.send_message(t("no_reminders"), ephemeral=True)
            return

        msg = "\n".join(
            (
                f"• <t:{int(r['remind_at'].timestamp())}:R> – "
                f"gesetzt am <t:{int(r['created_at'].timestamp())}:f>"
            )
            for r in reminders
        )
        await interaction.response.send_message(t("reminder_list", msg=msg), ephemeral=True)

    @app_commands.command(
        name=app_commands.locale_str("cmd_remind_cancel_name"),
        description=app_commands.locale_str("cmd_remind_cancel_desc"),
    )
    async def remind_cancel(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        result = get_collection("user_reminders").delete_many({"user_id": user_id})
        await interaction.response.send_message(
            t("reminders_deleted", count=result.deleted_count), ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(ReminderCog(bot))
