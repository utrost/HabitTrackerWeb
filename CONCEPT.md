# Habit Tracker Web — Konzept

## Philosophie

Drei Säulen, die sich gegenseitig verstärken:

### 1. Atomic Habits (James Clear)
- **Identitätsbasiert:** Nicht "ich will abnehmen", sondern "ich bin jemand, der sich bewegt"
- **1% besser:** Kleine tägliche Verbesserungen. Konsistenz > Intensität
- **Habit Stacking:** Neue Gewohnheiten an bestehende ankoppeln
- **Tracking = Beweis:** Jeder Eintrag ist ein Beweis für deine neue Identität

### 2. Stoizismus (Marcus Aurelius / Ryan Holiday)
- **Morgen-Reflexion:** "Was steht heute an? Was kann ich kontrollieren?"
- **Abend-Reflexion:** "Was lief gut? Was kann ich morgen besser machen?"
- **Dichotomie der Kontrolle:** Nur eigene Handlungen tracken, nicht Ergebnisse
- **Memento Mori:** Endlichkeit als Motivation — jeder Tag zählt
- **Tugenden:** Weisheit, Mut, Gerechtigkeit, Mäßigung als Kompass

### 3. Gamification (dezent, nicht Dopamin-Hack)
- **XP-System:** Jede getrackte Gewohnheit gibt XP
- **Level:** XP-Schwellen definieren Stufen (nicht inflationär)
- **Streaks:** Konsekutive Tage pro Habit + Gesamtstreak
- **Achievements:** Einmalige Meilensteine (erste Woche, 30 Tage, 100 Tage)
- **Kein Bestrafen:** Kein Streak-Verlust durch einen verpassten Tag — Streaks pausieren, starten neu

---

## Datenmodell-Erweiterung

### Ziele (Goals)
Habits dienen Zielen. Jedes Ziel hat messbare Kriterien:

```json
{
  "goals": {
    "gewicht-82": {
      "label": "Zielgewicht 82 kg",
      "icon": "🎯",
      "metric": "gewicht",
      "target": 82,
      "direction": "down",
      "start_value": 93,
      "start_date": "2026-04-07",
      "contributing_habits": ["beweglichkeit", "kraft", "keine-suessigkeiten"]
    },
    "klavier-routine": {
      "label": "Tägliche Klavier-Routine",
      "icon": "🎹",
      "metric": "streak",
      "target": 30,
      "direction": "up",
      "contributing_habits": ["kla"]
    }
  }
}
```

### XP + Level
```json
{
  "gamification": {
    "xp": 0,
    "level": 1,
    "achievements": [],
    "xp_rules": {
      "boolean_habit": 10,
      "numeric_habit_min": 5,
      "numeric_habit_target": 15,
      "journaling": 20,
      "all_habits_done": 50,
      "streak_7": 100,
      "streak_30": 500
    },
    "levels": [
      {"level": 1, "xp": 0, "title": "Anfänger"},
      {"level": 2, "xp": 200, "title": "Beständig"},
      {"level": 3, "xp": 500, "title": "Gewohnheitstier"},
      {"level": 4, "xp": 1200, "title": "Diszipliniert"},
      {"level": 5, "xp": 2500, "title": "Stoiker"},
      {"level": 6, "xp": 5000, "title": "Meister der Routine"},
      {"level": 7, "xp": 10000, "title": "Marcus Aurelius"}
    ]
  }
}
```

### Stoische Reflexion
```json
{
  "reflections": {
    "YYYY-MM-DD": {
      "morning": "Heute will ich...",
      "evening": "Heute habe ich...",
      "virtue": "temperance"
    }
  }
}
```

---

## Erinnerungen (Reminder-Konzept)

| Trigger | Zeit | Nachricht |
|---|---|---|
| Morgen-Impuls | 08:00 | Stoisches Zitat + "Was steht heute an?" |
| Mittags-Check | 13:00 | Kurzer Status: "3/7 Habits erledigt. 💪 Kraft und 🧘 Beweglichkeit fehlen noch." |
| Abend-Reminder | 21:00 | Fehlende Habits + Aufforderung zum Journaling |
| Streak-Warnung | 20:00 | Nur wenn Streak >7 und heute nichts getrackt |

**Regeln:**
- Nur an Tagen senden, an denen nicht schon getrackt wurde
- Nie aufdringlich — eine Nachricht pro Slot, keine Wiederholung
- Morgen-Impuls immer (motivierend), Rest nur bei Bedarf
- Wochenende: Zeiten anpassen (09:00 statt 08:00)

---

## Auswertung / Analytics

### Tägliche Sicht
- Welche Habits erledigt / offen
- XP-Gewinn heute
- Streak-Status pro Habit

### Wöchentliche Sicht
- Completion Rate (% der möglichen Habits)
- Gewichtsverlauf (7-Tage-Trend)
- Beste/schwächste Habits
- Gesamtstreak

### Monatliche Sicht
- Heatmap (GitHub-Style: Tage × Habits)
- Gewichtskurve mit Trendlinie
- Goal-Progress (% zum Ziel)
- XP-Verlauf + Level-Fortschritt

### Milestone-Berichte
- Wintermute liefert auf Anfrage oder bei Meilensteinen Zusammenfassungen
- Automatische Wochen-Reviews (Sonntag) via Telegram

---

## Architektur-Entscheidungen

| Entscheidung | Wahl | Begründung |
|---|---|---|
| Persistenz | JSON → SQLite (Phase 3) | JSON reicht für Start, SQLite bei >3 Monaten Daten |
| Frontend | Vanilla JS SPA | Keine Build-Tools, keine Dependencies, schnell |
| API | Flask (Python) | Einfach, Wintermute kennt es, schnelle Iteration |
| Hosting interaktiv | Tailscale:8078 | Sicher, nur Uwes Geräte |
| Hosting public | simiono.com/habits/ | Read-only Dashboard, FTP-Deploy |
| Repo | github.com/utrost/HabitTrackerWeb | AGPL-3.0 |
| Erinnerungen | Wintermute Cron → Telegram | Kein eigener Reminder-Service nötig |

---

## Phasen

### Phase 1: Foundation (aktuell) ✅ teilweise
- API + Frontend Grundgerüst
- 7 Start-Habits konfiguriert
- CRUD für Habits
- Streak-Berechnung
- Mobile-optimiertes UI

### Phase 2: Goals + Analytics
- Ziel-Datenmodell einführen
- Wöchentliche Heatmap
- Gewichtstrend-Chart verbessern
- Completion Rate Dashboard
- Public Dashboard (simiono.com)

### Phase 3: Gamification
- XP-System implementieren
- Level + Titel
- Achievement-System (Badges)
- Level-Up Animationen im UI

### Phase 4: Stoische Elemente
- Morgen/Abend-Reflexion UI
- Stoische Zitate-Datenbank
- Tugend-Tracking (welche Tugend stand heute im Fokus?)
- Wöchentlicher Reflexions-Bericht

### Phase 5: Reminder + Automation
- Cron-basierte Telegram-Reminders
- Intelligente Erinnerungen (nur wenn nötig)
- Wochen-Review automatisch
- Streak-Schutz-Warnungen

### Phase 6: Polish + Sustainability
- SQLite-Migration (wenn nötig)
- PWA + Offline-Fähigkeit
- Daten-Export (CSV, JSON)
- Langzeit-Statistiken (3/6/12 Monate)
