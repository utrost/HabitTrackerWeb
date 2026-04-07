# Phase 2: Goals + Analytics — Implementation Task

## Context
This is a Flask + Vanilla JS habit tracker app. Single-file frontend (index.html), Flask backend (api.py).
Data lives in data.json. The app runs on Tailscale port 8078.

## Current State
- 7 habits configured (Beweglichkeit, Kraft, Klavier, Journaling, Gewicht, Schritte, Keine Süßigkeiten)
- CRUD for habits works
- Boolean + Number tracking works
- Streaks, weight chart, journal, 30-day dot grid, bottom nav — all done
- No entries yet (fresh start)

## Tasks to Implement

### 1. Goal Data Model (T-0813)
Add a `goals` section to data.json schema:
```json
{
  "goals": {
    "<slug>": {
      "label": "string",
      "icon": "emoji",
      "metric": "habit-slug or 'streak'",
      "target": number,
      "direction": "up" | "down",
      "start_value": number,
      "start_date": "YYYY-MM-DD",
      "contributing_habits": ["slug1", "slug2"]
    }
  }
}
```
Add default goals:
- "gewicht-82": target 82kg, direction down, start 93kg, contributing: beweglichkeit, kraft, suessigkeiten
- "klavier-routine": target 30 (streak days), direction up, contributing: kla

### 2. Goal Progress API (T-0814)
- GET `/api/goals` — returns all goals with current progress (% complete, current value, trend)
- PUT `/api/goal` — create/update goal
- DELETE `/api/goal/<slug>` — delete goal

### 3. Weekly Completion Rate (T-0815)
- In `/api/overview`, add `completion_rate` object:
  - `today`: % of habits done today
  - `week`: % of possible habit-days this week
  - `trend`: up/down/flat vs last week

### 4. Heatmap View (T-0816)
- New tab or section in frontend: GitHub-style heatmap
- X-axis: days (last 12 weeks), Y-axis: habits
- Color intensity = done (boolean) or % of target (numeric)
- Pure CSS/JS, no external libs

### 5. Weight Trend with Moving Average (T-0817)
- Improve existing weight chart
- Add 7-day moving average trendline
- Show delta from start and delta to goal
- Use canvas or SVG (no external chart libs)

### 6. Weekly Overview Dashboard (T-0818)
- Summary section showing:
  - Best habit this week (highest completion %)
  - Weakest habit (lowest completion %)
  - Overall completion rate
  - Current streaks
  - Weight progress vs goal

### 7. Public Dashboard Snapshot (T-0819)
- The public version at simiono.com/habits/ is read-only (no API access)
- Make index.html detect when no API is available and fall back to reading data.json directly
- Show a clean read-only dashboard (no input fields, no edit buttons)
- Add a "Last updated" timestamp

## Technical Constraints
- **No external dependencies** in frontend (no React, no Chart.js, no npm)
- Vanilla JS + CSS only. Canvas or inline SVG for charts.
- Flask backend, Python stdlib + flask only
- Mobile-first design (existing bottom-nav with 4 tabs)
- German UI labels
- All new endpoints must be documented in code comments

## File Structure
- `api.py` — Flask backend (modify)
- `index.html` — Frontend SPA (modify)
- `data.json` — Data file (will be modified by API at runtime)
- `tracking.py` — Tracking utilities (modify if needed)

## Testing
After implementation:
1. Start server: `python3 api.py`
2. Verify all new API endpoints return valid JSON
3. Verify frontend loads without errors
4. Verify heatmap renders (even with empty data)
5. Verify weight chart shows moving average
6. Verify read-only mode works (rename api.py temporarily, open index.html)

## Done Criteria
- All 7 features implemented and working
- No console errors in browser
- Mobile-friendly (test at 375px width)
- Code committed to git
