import secrets
from urllib.parse import urlencode

import requests
from bson import ObjectId
from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from fur_lang.i18n import get_supported_languages
from mongo_service import db
from web.auth.decorators import r3_required

public = Blueprint("public", __name__)


@public.route("/")
def landing():
    return render_template("public/landing.html")


@public.route("/set_language")
def set_language():
    lang = request.args.get("lang")
    if lang in get_supported_languages():
        session["lang"] = lang
    return redirect(request.referrer or url_for("public.landing"))


@public.route("/login")
def login():
    user = session.get("user")
    if user:
        role = user.get("role_level")
        if role in ["ADMIN", "R4"]:
            return redirect(url_for("admin.dashboard"))
        elif role == "R3":
            return redirect(url_for("member.dashboard"))
    return render_template("public/login.html")


@public.route("/logout")
def logout():
    session.clear()
    flash("Du wurdest erfolgreich ausgeloggt.", "info")
    return redirect(url_for("public.login"))


@public.route("/login/discord")
def discord_login():
    client_id = current_app.config["DISCORD_CLIENT_ID"]
    redirect_uri = current_app.config["DISCORD_REDIRECT_URI"]

    state = secrets.token_urlsafe(16)
    session["discord_oauth_state"] = state

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "identify guilds guilds.members.read",
        "state": state,
    }

    url = f"https://discord.com/oauth2/authorize?{urlencode(params)}"
    return redirect(url)


@public.route("/callback")
def discord_callback():
    code = request.args.get("code")
    state = request.args.get("state")

    if not code:
        return "Fehlender Code", 400
    if not state or state != session.pop("discord_oauth_state", None):
        return "Ungültiger OAuth-State", 400

    token_res = requests.post(
        "https://discord.com/api/oauth2/token",
        data={
            "client_id": current_app.config["DISCORD_CLIENT_ID"],
            "client_secret": current_app.config["DISCORD_CLIENT_SECRET"],
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": current_app.config["DISCORD_REDIRECT_URI"],
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )

    if token_res.status_code != 200:
        current_app.logger.error("OAuth Token Error %s: %s", token_res.status_code, token_res.text)
        flash("Discord Login fehlgeschlagen", "danger")
        return redirect(url_for("public.login"))

    access_token = token_res.json().get("access_token")

    user_res = requests.get(
        "https://discord.com/api/users/@me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    user_data = user_res.json()

    guild_res = requests.get(
        f"https://discord.com/api/users/@me/guilds/{current_app.config['DISCORD_GUILD_ID']}/member",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if guild_res.status_code != 200:
        return "Nicht-Mitglied im FUR Discord-Server", 403

    guild_member = guild_res.json()
    user_roles = set(str(role) for role in guild_member.get("roles", []))

    r3_roles = set(map(str, current_app.config.get("R3_ROLE_IDS", set())))
    r4_roles = set(map(str, current_app.config.get("R4_ROLE_IDS", set())))
    admin_roles = set(map(str, current_app.config.get("ADMIN_ROLE_IDS", set())))

    if user_roles & admin_roles:
        role_level = "ADMIN"
    elif user_roles & r4_roles:
        role_level = "R4"
    elif user_roles & r3_roles:
        role_level = "R3"
    else:
        current_app.logger.warning("❌ Keine gültige Discord-Rolle erkannt.")
        return "Keine gültige Rolle für den Zugriff", 403

    session["discord_roles"] = [role_level]
    session["user"] = {
        "id": user_data["id"],
        "username": user_data["username"],
        "avatar": user_data["avatar"],
        "email": user_data.get("email"),
        "role_level": role_level,
    }
    session.permanent = True

    db["users"].update_one(
        {"discord_id": user_data["id"]},
        {
            "$set": {
                "username": user_data["username"],
                "avatar": user_data["avatar"],
                "email": user_data.get("email"),
                "role_level": role_level,
            }
        },
        upsert=True,
    )

    flash("Erfolgreich mit Discord eingeloggt", "success")

    if role_level in ["ADMIN", "R4"]:
        return redirect(url_for("admin.dashboard"))
    else:
        return redirect(url_for("member.dashboard"))


@public.route("/lore")
def lore():
    return render_template("public/lore.html")


@public.route("/calendar")
def calendar():
    return render_template("public/calendar.html")


@public.route("/events")
def events():
    rows = list(db["events"].find().sort("event_date", 1))
    return render_template("public/events_list.html", events=rows)


@public.route("/events/<event_id>")
def view_event(event_id):
    event = db["events"].find_one({"_id": ObjectId(event_id)})
    if not event:
        abort(404)
    return render_template("public/view_event.html", event=event)


@public.route("/events/<event_id>/join", methods=["POST"])
@r3_required
def join_event(event_id):
    if "user" not in session:
        flash("Du musst eingeloggt sein.", "warning")
        return redirect(url_for("public.login"))

    flash("Du bist dem Event erfolgreich beigetreten!", "success")
    return redirect(url_for("public.view_event", event_id=event_id))


@public.route("/hall_of_fame")
def hall_of_fame():
    rows = list(db["hall_of_fame"].find().sort("_id", -1).limit(10))
    return render_template("public/hall_of_fame.html", hof=rows)


@public.route("/leaderboard")
def leaderboard():
    rows = list(db["leaderboard"].find().sort("score", -1).limit(100))
    leaderboard_list = []
    for i, row in enumerate(rows, start=1):
        leaderboard_list.append({"rank": i, "username": row["username"], "score": row["score"]})
    return render_template("public/public_leaderboard.html", leaderboard=leaderboard_list)


@public.route("/dashboard")
def dashboard():
    return render_template("public/dashboard.html")
