# Phase 3: Gamification — Implementation Task

## Context
Habit Tracker Web App. Flask backend (api.py), Vanilla JS frontend (index.html).
Data in data.json. See CONCEPT.md for the full XP/Level/Achievement design.

## Current State
- Phase 1+2 complete: habits CRUD, goals, analytics, heatmap, dashboard all working
- data.json has: habits, goals, journal, meta sections
- Frontend has: Today tab, History, Heatmap, Weight, Journal, Dashboard tabs

## Tasks to Implement

### 1. XP-Engine (T-0820)
Add XP calculation to the backend. Rules:
- Boolean habit completed: +10 XP
- Numeric habit with any value: +5 XP
- Numeric habit reaching daily target: +15 XP
- Journaling done: +20 XP
- All habits done in a day: +50 XP bonus
- 7-day streak on any habit: +100 XP
- 30-day streak: +500 XP

Store XP in data.json under `gamification.xp` (cumulative total).
XP should be recalculated from entries (not stored incrementally) to stay consistent.
Add helper function `_calculate_xp(data) -> int`.

### 2. Level System (T-0821)
7 levels based on XP thresholds:
| Level | XP | Title |
|---|---|---|
| 1 | 0 | Anfänger |
| 2 | 200 | Beständig |
| 3 | 500 | Gewohnheitstier |
| 4 | 1200 | Diszipliniert |
| 5 | 2500 | Stoiker |
| 6 | 5000 | Meister der Routine |
| 7 | 10000 | Marcus Aurelius |

Add `/api/gamification` GET endpoint returning: xp, level, title, xp_to_next_level, progress_pct.
Store `gamification` section in data.json.

### 3. Achievement System (T-0822)
Define achievements as badges. Check conditions on each API call to `/api/gamification`.
Achievements (store earned ones with date in `gamification.achievements`):

| ID | Name | Icon | Condition |
|---|---|---|---|
| first-day | Erster Tag | 🌱 | First habit tracked |
| week-warrior | Wochenkrieger | ⚔️ | 7-day streak any habit |
| month-master | Monatsmeister | 🏆 | 30-day streak any habit |
| all-in | All-In | 💯 | All habits done in one day |
| fifty-days | 50 Tage dabei | 📅 | 50 days since start with at least 1 entry |
| hundred-days | 100 Tage dabei | 🎖️ | 100 days since start with at least 1 entry |
| weight-5 | 5kg geschafft | 🔥 | Lost 5kg from start weight |
| level-up-3 | Gewohnheitstier | 🦁 | Reached level 3 |
| level-up-5 | Stoiker | 🏛️ | Reached level 5 |
| level-up-7 | Marcus Aurelius | 👑 | Reached level 7 |

### 4. XP/Level UI Display (T-0823)
- Show current level + title in the header area
- XP progress bar toward next level
- Small XP counter
- Update on page load

### 5. Level-Up Notification (T-0824)
- When user reaches a new level, show a celebratory overlay/modal
- Display: new level number, title, and a motivating message
- Auto-dismiss after 5 seconds or on tap
- Store `gamification.last_seen_level` to detect new level-ups
- CSS animation (scale up + fade in)

### 6. Achievement Gallery (T-0825)
- New section/tab showing all achievements
- Earned achievements: colored with date earned
- Unearned: greyed out with "???" or condition hint
- Use a grid layout with icons

## Technical Constraints
- No external dependencies (no npm, no libs)
- Vanilla JS + CSS only
- Mobile-first
- German UI labels
- XP must be recalculated from data (not stored incrementally) — idempotent

## Testing
After implementation:
1. `python3 -c "import api"` must work
2. `/api/gamification` must return valid JSON with xp, level, title, achievements
3. Frontend must show XP bar and level without console errors
4. Achievement gallery must render (even with no achievements earned)

## Done Criteria
- All 6 features working
- No console errors
- Git commit with descriptive message
