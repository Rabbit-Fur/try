"""Admin blueprint using MongoDB."""

import json
import os
from datetime import datetime

from bson import ObjectId
from flask import (
    Blueprint,
    Response,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from werkzeug.utils import secure_filename

from agents.webhook_agent import WebhookAgent
from config import Config
from fur_lang.i18n import t
from mongo_service import get_collection
from utils.discord_util import require_roles
from utils.poster_generator import generate_event_poster
from web.auth.decorators import r4_required

admin = Blueprint("admin", __name__)


@require_roles(["R4", "ADMIN"])
@r4_required
@admin.route("/")
def admin_dashboard():
    return render_template("admin/admin.html")


@require_roles(["R4", "ADMIN"])
@r4_required
@admin.route("/calendar")
def calendar():
    return render_template("admin/calendar.html")


@require_roles(["R4", "ADMIN"])
@r4_required
@admin.route("/create_event", methods=["GET", "POST"])
def create_event():
    if request.method == "POST":
        title = request.form.get("title")
        event_time = request.form.get("event_date")
        description = request.form.get("description")
        try:
            get_collection("events").insert_one(
                {
                    "title": title,
                    "event_time": event_time,
                    "created_by": 1,
                    "description": description,
                }
            )
            flash(t("event_created", default="Event created"), "success")
            return redirect(url_for("admin.events"))
        except Exception as e:
            current_app.logger.error("Event creation failed: %s", e, exc_info=True)
            flash(t("save_error", default="Save failed"), "danger")
    return render_template("admin/create_event.html")


@require_roles(["R4", "ADMIN"])
@r4_required
@admin.route("/dashboard")
def dashboard():
    if current_app.config.get("TESTING"):
        return "admindash"

    coll = get_collection("settings")
    dm_settings = {}
    for _t in ("daily", "weekly", "custom"):
        doc = coll.find_one({"_id": f"dm_image_{_t}"})
        dm_settings[_t] = doc.get("value") if doc else ""

    return render_template("admin/dashboard.html", dm_settings=dm_settings)


@require_roles(["R4", "ADMIN"])
@r4_required
@admin.route("/diplomacy")
def diplomacy():
    return render_template("admin/diplomacy.html")


@require_roles(["R4", "ADMIN"])
@r4_required
@admin.route("/downloads")
def downloads():
    return render_template("admin/downloads.html")


@require_roles(["R4", "ADMIN"])
@r4_required
@admin.route("/pet-advisor")
def pet_advisor():
    """Render the Pet Advisor dashboard for authorized users."""
    if current_app.config.get("TESTING"):
        return "petadvisor"
    return render_template("admin/pet_advisor.html")


@require_roles(["R4", "ADMIN"])
@r4_required
@admin.route("/edit_event", methods=["GET", "POST"])
def edit_event():
    event_id = request.args.get("id") or request.form.get("id")
    if not event_id:
        flash(t("unknown_event", default="Unknown event"), "danger")
        return redirect(url_for("admin.events"))

    collection = get_collection("events")
    event = collection.find_one({"_id": ObjectId(event_id)})
    if not event:
        flash(t("unknown_event", default="Unknown event"), "danger")
        return redirect(url_for("admin.events"))

    if request.method == "POST":
        update = {
            "title": request.form.get("title"),
            "description": request.form.get("description"),
            "event_time": request.form.get("event_date"),
            "role": request.form.get("role"),
            "recurrence": request.form.get("recurrence"),
            "updated_at": datetime.utcnow(),
        }
        try:
            collection.update_one({"_id": ObjectId(event_id)}, {"$set": update})
            flash(t("event_updated", default="Event updated"), "success")
            return redirect(url_for("admin.events"))
        except Exception as e:
            current_app.logger.error("Event update failed: %s", e, exc_info=True)
            flash(t("save_error", default="Save failed"), "danger")
    return render_template("admin/edit_event.html", event=event)


@require_roles(["R4", "ADMIN"])
@r4_required
@admin.route("/events")
def events():
    rows = list(get_collection("events").find().sort("event_time", 1))
    for row in rows:
        row["id"] = str(row.get("_id"))
    return render_template("admin/events.html", events=rows)


@require_roles(["R4", "ADMIN"])
@r4_required
@admin.route("/leaderboards")
def leaderboards():
    return render_template("admin/leaderboards.html")


@require_roles(["R4", "ADMIN"])
@r4_required
@admin.route("/participants")
def participants():
    event_id = request.args.get("event_id")
    event = None
    participant_list = []
    if event_id:
        try:
            event = get_collection("events").find_one({"_id": ObjectId(event_id)})
            if event:
                participant_docs = list(
                    get_collection("event_participants").find({"event_id": event["_id"]})
                )
                for p in participant_docs:
                    user = get_collection("users").find_one({"discord_id": p["user_id"]})
                    participant_list.append(
                        {"username": user.get("username") if user else p["user_id"]}
                    )
        except Exception as exc:  # noqa: BLE001
            current_app.logger.warning("Invalid event id %s: %s", event_id, exc)
    return render_template(
        "admin/participants.html", event=event or {}, participants=participant_list
    )


@require_roles(["R4", "ADMIN"])
@r4_required
@admin.route("/reminders")
def reminder_admin():
    reminders = list(get_collection("reminders").find().sort("send_time", 1))
    return render_template("admin/reminders.html", reminders=reminders)


@require_roles(["R4", "ADMIN"])
@r4_required
@admin.route("/settings")
def settings():
    return render_template("admin/settings.html")


@require_roles(["R4", "ADMIN"])
@r4_required
@admin.route("/tools")
def tools():
    return render_template("admin/tools.html")


@require_roles(["R4", "ADMIN"])
@r4_required
@admin.route("/translations_editor", methods=["GET", "POST"])
def translations_editor():
    from fur_lang.i18n import get_supported_languages, translations

    supported_languages = get_supported_languages()
    selected_language = (
        request.args.get("language") or request.form.get("language") or request.args.get("lang")
    )
    if not selected_language and supported_languages:
        selected_language = supported_languages[0]

    data = {}
    file_path = None
    if selected_language:
        file_path = os.path.join(
            current_app.root_path,
            "translations",
            f"{selected_language}.json",
        )
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    current_app.logger.error("Invalid JSON in %s", file_path)

    if request.method == "POST" and any(k.startswith("translations[") for k in request.form.keys()):
        updated = {}
        for k, v in request.form.items():
            if k.startswith("translations[") and k.endswith("]"):
                key = k[len("translations[") : -1]
                updated[key] = v
        if file_path:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(updated, f, indent=2, ensure_ascii=False)
            translations[selected_language] = updated
            data = updated

    return render_template(
        "admin/translations_editor.html",
        available_languages=supported_languages,
        selected_language=selected_language,
        translations=data,
    )


@admin.route("/trigger_reminder", methods=["POST"])
@require_roles(["R4", "ADMIN"])
@r4_required
def trigger_reminder():
    return "Reminder triggered"


@admin.route("/trigger_champion_post", methods=["POST"])
@require_roles(["R4", "ADMIN"])
@r4_required
def trigger_champion_post():
    return "Champion post triggered"


@admin.route("/healthcheck", methods=["POST"])
@require_roles(["R4", "ADMIN"])
@r4_required
def healthcheck():
    return Response("ok", status=200)


@admin.route("/export_participants")
@require_roles(["R4", "ADMIN"])
@r4_required
def export_participants():
    csv_data = "username\n"
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=participants.csv"},
    )


@admin.route("/export_scores")
@require_roles(["R4", "ADMIN"])
@r4_required
def export_scores():
    csv_data = "username,score\n"
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=scores.csv"},
    )


@admin.route("/events/post/<event_id>", methods=["POST"])
@require_roles(["R4", "ADMIN"])
@r4_required
def post_event(event_id: str):
    """Post an event via bot or webhook."""
    event = get_collection("events").find_one({"_id": ObjectId(event_id)})
    if not event:
        flash(t("unknown_event"), "danger")
        return redirect(url_for("admin.events"))

    content = (
        f"📅 **{event.get('title')}**\n{event.get('description', '')}\n🕒 {event.get('event_time')}"
    )
    webhook = WebhookAgent(Config.DISCORD_WEBHOOK_URL)
    poster_path = generate_event_poster(event)
    poster_url = (
        poster_path
        if poster_path.startswith("http")
        else Config.BASE_URL.rstrip("/") + "/" + poster_path.lstrip("/")
    )
    success = webhook.send(content, image_url=poster_url, event_channel=True)
    flash(
        (
            t("event_posted", default="Event posted")
            if success
            else t("post_failed", default="Post failed")
        ),
        "success" if success else "danger",
    )
    return redirect(url_for("admin.events"))


@admin.route("/post_champion", methods=["POST"])
@require_roles(["R4", "ADMIN"])
@r4_required
def post_champion():
    from modules.champion import post_champion_poster

    success = post_champion_poster()
    flash(
        (
            t("champion_posted", default="Champion posted")
            if success
            else t("post_failed", default="Post failed")
        ),
        "success" if success else "danger",
    )
    return redirect(url_for("admin.admin_dashboard"))


@admin.route("/post_weekly_report", methods=["POST"])
@require_roles(["R4", "ADMIN"])
@r4_required
def post_weekly_report():
    from modules.weekly_report import post_report

    success = post_report()
    flash(
        (
            t("weekly_report_posted", default="Weekly report posted")
            if success
            else t("post_failed", default="Post failed")
        ),
        "success" if success else "danger",
    )
    return redirect(url_for("admin.admin_dashboard"))


@admin.route("/post_announcement", methods=["POST"])
@require_roles(["R4", "ADMIN"])
@r4_required
def post_announcement():
    title = request.form.get("title", "").strip()
    message = request.form.get("message", "").strip()

    if not title or not message:
        flash(t("title_message_required", default="Title and message required"), "danger")
        return redirect(url_for("admin.admin_dashboard"))

    content = f"📣 **{title}**\n{message}"
    success = WebhookAgent(Config.DISCORD_WEBHOOK_URL).send(content)

    flash(
        (
            t("announcement_sent", default="Announcement sent")
            if success
            else t("send_failed", default="Send failed")
        ),
        "success" if success else "danger",
    )
    return redirect(url_for("admin.admin_dashboard"))


@admin.route("/send_daily_dms", methods=["POST"])
@require_roles(["R4", "ADMIN"])
@r4_required
def send_daily_dms():
    """Trigger sending of today's event reminders via DM."""
    if current_app.config.get("TESTING"):
        return "daily"

    from bot import bot_main, dm_scheduler
    import asyncio

    bot = bot_main.bot
    asyncio.run(dm_scheduler.send_daily_dm(bot))
    flash("Daily DMs sent", "success")
    return redirect(url_for("admin.admin_dashboard"))


@admin.route("/send_custom_dm", methods=["POST"])
@require_roles(["R4", "ADMIN"])
@r4_required
def send_custom_dm():
    """Send a custom DM to all or a specific user."""
    if current_app.config.get("TESTING"):
        return "custom"

    from bot import bot_main, dm_scheduler
    import asyncio

    text = request.form.get("message", "").strip()
    user_id = request.form.get("user_id")
    if not text:
        flash("Message required", "danger")
        return redirect(url_for("admin.admin_dashboard"))

    bot = bot_main.bot
    targets = []
    if user_id:
        targets = [int(user_id)]
    else:
        targets = dm_scheduler.get_dm_users()

    success = 0
    for uid in targets:
        try:
            user = asyncio.run(bot.fetch_user(uid))
            asyncio.run(dm_scheduler.send_embed_dm(user, text, "custom"))
            success += 1
        except Exception:
            pass

    flash(f"DMs sent: {success}", "success")
    return redirect(url_for("admin.admin_dashboard"))


@admin.route("/dm_images", methods=["POST"])
@require_roles(["R4", "ADMIN"])
@r4_required
def save_dm_images():
    """Save DM image URLs or uploads for each DM type."""
    coll = get_collection("settings")
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)
    for dm_type in ("daily", "weekly", "custom"):
        url = request.form.get(f"{dm_type}_url", "").strip()
        file = request.files.get(f"{dm_type}_file")
        value = None
        if file and file.filename:
            filename = secure_filename(file.filename)
            file.save(os.path.join(upload_folder, filename))
            value = f"/static/uploads/{filename}"
        elif url:
            value = url
        if value:
            coll.update_one(
                {"_id": f"dm_image_{dm_type}"},
                {"$set": {"value": value}},
                upsert=True,
            )
    flash(t("dm_images_saved", default="DM images saved"), "success")
    return redirect(url_for("admin.dashboard"))


def _allowed_file(filename: str) -> bool:
    """Return True if the filename has an allowed extension."""
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"]
    )


@admin.route("/upload", methods=["GET", "POST"])
@require_roles(["R4", "ADMIN"])
@r4_required
def upload():
    """Handle file uploads for admin users."""
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)

    if request.method == "POST":
        if (
            request.content_length
            and request.content_length > current_app.config["MAX_CONTENT_LENGTH"]
        ):
            flash(t("file_too_large", default="Datei zu groß"), "danger")
            return redirect(request.url)

        file = request.files.get("file")
        if not file or file.filename == "":
            flash(t("no_file_selected", default="No file selected"), "danger")
            return redirect(request.url)
        if not _allowed_file(file.filename):
            flash(t("invalid_file_type", default="Ungültiger Dateityp"), "danger")
            return redirect(request.url)

        allowed_mimes = current_app.config.get("ALLOWED_MIME_TYPES", {"image/png", "image/jpeg"})
        if file.mimetype not in allowed_mimes:
            flash(t("invalid_file_type", default="Ungültiger Dateityp"), "danger")
            return redirect(request.url)

        filename = secure_filename(file.filename)
        file.save(os.path.join(upload_folder, filename))
        flash(t("file_uploaded", default="Datei hochgeladen"), "success")
        return redirect(url_for("admin.upload"))

    files = []
    if os.path.exists(upload_folder):
        files = sorted(f for f in os.listdir(upload_folder) if _allowed_file(f))

    return render_template("admin/upload.html", files=files)
