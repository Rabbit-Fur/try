from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv

# .env laden
load_dotenv()

# MongoDB-Verbindung aus .env
mongo_url = os.getenv("MONGO_URL")
mongo_db_name = os.getenv("MONGO_DB", "furdb")

if not mongo_url:
    raise RuntimeError("MONGO_URL ist nicht gesetzt")

# Verbindung herstellen
client = MongoClient(mongo_url)
db = client[mongo_db_name]

# Kollektion prüfen / erstellen
collection_name = "daily_logs"
if collection_name not in db.list_collection_names():
    db.create_collection(collection_name)

# Beispiel-Eintrag
log_entry = {
    "date": datetime.now().strftime("%Y-%m-%d"),
    "type": "project_log",
    "entries": [
        {"category": "FUR SYSTEM", "content": "daily_logs wurde erfolgreich initialisiert."},
        {"category": "Codex", "content": "Export zu GitHub folgt im nächsten Schritt."},
    ],
    "created_by": "Mai Diep Anh Do",
}

# Eintrag speichern
db[collection_name].insert_one(log_entry)
print("✅ Log gespeichert in MongoDB → daily_logs")
