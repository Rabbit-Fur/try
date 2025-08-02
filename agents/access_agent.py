# agents/access_agent.py

import os
from datetime import datetime


class AccessAgent:
    def __init__(self, db):
        self.db = db
        # .env-basierte Rollenzuordnung (CSV → Liste[str])
        self.admin_roles = set(os.getenv("ADMIN_ROLE_IDS", "").split(","))
        self.r4_roles = set(os.getenv("R4_ROLE_IDS", "").split(","))
        self.r3_roles = set(os.getenv("R3_ROLE_IDS", "").split(","))

    def get_user_role_level(self, discord_roles: list[str]) -> str:
        """Bestimme die höchste Rollenstufe anhand der Discord-Rollenliste.

        Gibt die Rolle mit dem höchsten Berechtigungsniveau zurück.
        """
        if set(discord_roles) & self.admin_roles:
            return "admin"
        elif set(discord_roles) & self.r4_roles:
            return "R4"
        elif set(discord_roles) & self.r3_roles:
            return "R3"
        return "guest"

    def log_access(self, discord_id: str, action: str, result: str):
        """Speichert einen Audit-Log über den Rollencheck.

        Persistiert Discord-ID, Aktion, Ergebnis und Zeitpunkt in der Datenbank.
        """
        self.db["access_logs"].insert_one(
            {
                "discord_id": discord_id,
                "action": action,
                "result": result,
                "timestamp": datetime.utcnow(),
            }
        )

    def has_access(self, discord_id: str, discord_roles: list[str], required_level: str) -> bool:
        role_level = self.get_user_role_level(discord_roles)
        level_map = {"guest": 0, "R3": 1, "R4": 2, "admin": 3}
        result = level_map.get(role_level, 0) >= level_map.get(required_level, 0)
        self.log_access(
            discord_id,
            f"require:{required_level}",
            "✅ allow" if result else "❌ deny",
        )
        return result

    def is_admin(self, discord_roles: list[str]) -> bool:
        return bool(set(discord_roles) & self.admin_roles)
