

Willkommen im Kernsystem von **FUR (Federated Utility Rabbit)** – einem modularen Discord-, Kalender- und Ereignis-Managementsystem mit GPT-gestütztem Multi-Agent-Netzwerk, MongoDB, Google-API-Integration und vollautomatisierten Abläufen.

> Dieses Repository folgt dem Codex-Protokoll QUM-1.0 und ist vollständig kompatibel mit Codex-Aktionen, Commit-Governance und Agenten-Routing.

---

## 🚀 Quickstart

# 1. Repository klonen

git clone https://github.com/Rabbit-Fur/try.git
cd try

# 2. Umgebung konfigurieren

cp .env.example .env
# 3. Pre-commit installieren

pre-commit install

# 4. Starten (lokal)

poetry run python main_app.py

🧱 Struktur

.
├── agents/                # Alle Codex-konformen Agenten
├── bot/                   # Discord-Bot + Cogs
├── blueprints/           # Flask-API (OAuth, User, Events)
├── db/                   # MongoDB-Logik, Zugriffsschicht
├── tests/                # pytest-Tests
├── .copilot/             # Codex-Regeln, Commit- und Branchrichtlinien
├── argend.md             # Agent-Beschreibung (optional pro Modul)
└── AGENTS.md             # Übersicht aller registrierten Agenten
⚙️ Konfiguration

Erstelle .env basierend auf .env.example:

env
DISCORD_TOKEN=...
GOOGLE_CLIENT_SECRET=...
MONGO_URI=mongodb+srv://...
OPENAI_API_KEY=...
GITHUB_TOKEN=...
PROMETHEUS_ENDPOINT=http://localhost:9090
DEBUG=true

`GITHUB_TOKEN` wird für Zugriffe auf die GitHub API benötigt.
`PROMETHEUS_ENDPOINT` legt fest, wo Prometheus die Metriken abrufen kann.
Weitere Details zu allen Variablen finden sich in [docs/env_vars.md](docs/env_vars.md).

📡 Features

✅ Zwei-Wege-Kalendersync (Google ↔ MongoDB)

✅ Vollständig modularisiertes Agentensystem

✅ Discord-Bot mit intelligenten Cogs (/cal, /now, /add)

🧠 Kontextspeicher für Multi-User-Prompting

📁 Logging + Event-Trail über log_agent

🌐 Externe Webhook-Verarbeitung (z. B. GitHub, Stripe)

📦 Agenten (Auszug)

Agent	Zweck

reminder_agent	Erinnerungen via Kalender / Discord
auth_agent	Auth mit Discord, Google OAuth
scheduler_agent	Zeitbasierte Planung & Trigger
poster_agent	Bildgenerierung über image_api
tagging_agent	Automatische Kategorisierung

→ Vollständige Liste: AGENTS.md

📜 Codex-Protokoll (QUM-1.0)

Jeder Agent benötigt eine eigene argend.md

Commit Messages folgen dem Schema COD:agent-name → kurzbeschreibung

Commit-Lint, Branch- und PR-Regeln werden über .copilot/config.json gesteuert

Jeder Branch beginnt mit feature/, fix/, agent/, release/

🧪 Tests

pytest tests/

Testabdeckung für Agenten, API-Flows, Discord-Kommandos

Linting: ruff, mypy, black

Pre-Commit Hooks aktiviert (.pre-commit-config.yaml)
Vor dem ersten Commit: `pre-commit install`

📄 Dokumentation

Agentendefinitionen: AGENTS.md

API-Flows: docs/oauth.md

MongoDB Setup: docs/mongo.md

🔐 Sicherheit

Alle Secrets sind über .env geschützt

Token Refresh-Flows sind implementiert

Codex blockiert Deployment ohne .env.example + Commit-Lint

## Google Calendar → Eventbild → Discord Workflow

- Liest Events automatisiert aus Google Calendar
- Erstellt für jedes Event ein ansprechendes Eventbild (FUR-Style)
- Postet Event + Bild als Embed ins Discord (mit `!postevent`)
- Vollständig modular, robust und testbar umgesetzt
- Für Setup siehe `requirements.txt` und API-Doku im Ordner `docs/`

📬 Kontakt

Maintainer: Marcel Schlanzke

Discord: see_u_m

🛠️ Kompatibilität

Komponente	Version
Python	3.11.x
MongoDB Atlas	≥ 5.0
Discord.py	2.x
Google API	v3
OpenAI API	GPT-4 Turbo

📜 Lizenz
MIT – siehe LICENSE


