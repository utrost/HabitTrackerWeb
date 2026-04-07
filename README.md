# Habit Tracker Web

Web-basierte Anwendung zum Tracken täglicher Gewohnheiten. Teil des "Stoic Uwe"-Projekts.

**Drei Säulen:** Stoizismus · Atomic Habits · Gamification

## Quick Start

```bash
# API-Server starten (Tailscale Port 8078)
python3 api.py

# Oder via systemd
systemctl --user start habits-api
```

## Architektur

- **Frontend:** Vanilla JS SPA, Mobile-optimiert (Bottom-Nav)
- **Backend:** Flask REST API (Python), Port 8078
- **Daten:** `data.json` (JSON, SQLite geplant)
- **Deploy:** Tailscale (interaktiv) + simiono.com/habits/ (read-only)

## API-Endpunkte

| Endpoint | Methode | Funktion |
|---|---|---|
| `/api/overview` | GET | Summary |
| `/api/habits` | GET | Alle Habits mit Entries/Streaks |
| `/api/habit` | POST | Neues Habit |
| `/api/habit/<slug>` | PUT/DELETE | Habit bearbeiten/löschen |
| `/api/track` | PUT | Wert tracken |
| `/api/weight` | PUT | Gewicht eintragen |
| `/api/journal` | GET/POST | Journal-Einträge |

## Konzept

Siehe [CONCEPT.md](CONCEPT.md) für das vollständige Konzept inkl. Gamification, stoische Elemente und Reminder-System.

## Lizenz

AGPL-3.0
