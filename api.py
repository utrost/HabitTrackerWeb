#!/usr/bin/env python3
"""
Stoic Uwe — Habit Tracker API Server
Flask-based REST API for interactive habit tracking.
Runs on Tailscale port 8078.
"""
import json
import subprocess
import sys
import os
import re as _re
from pathlib import Path
from datetime import datetime, timedelta, date
from flask import Flask, jsonify, request, send_from_directory

BASE = Path(__file__).parent
DATA_FILE = BASE / "data.json"
BACKUP_DIR = BASE / "backups"
BACKUP_DIR.mkdir(exist_ok=True)

app = Flask(__name__, static_folder=str(BASE))

# ──── helpers ─────────────────────────────────────────────────────────

def load():
    if DATA_FILE.exists():
        with open(DATA_FILE) as f:
            return json.load(f)
    d = _default_data()
    save(d)
    return d

def save(d):
    backup = BACKUP_DIR / f"data-{date.today()}.json"
    if not backup.exists():
        backup.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
    DATA_FILE.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")

def today():
    return date.today().isoformat()

def days_ago(n):
    return (date.today() - timedelta(days=n)).isoformat()

def _default_data():
    return {
        "habits": {},
        "goals": {},
        "journal": {},
        "meta": {"start_date": today(), "start_weight_kg": None, "target_weight_kg": None, "version": 2}
    }

def _slug(text, habits):
    s = _re.sub(r'[^\w\s-]', '', text.lower().strip())
    s = _re.sub(r'[\s_]+', '-', s)
    slug = s or f"habit-{int(datetime.now().timestamp())}"
    i = 1
    while slug in habits:
        i += 1
        slug = f"{s}-{i}"
    return slug

def _streak(entries):
    """Current streak: consecutive days ending today or yesterday."""
    if not entries:
        return 0
    keys = sorted(d for d in entries if len(d) == 10)
    if not keys:
        return 0
    t = date.today()
    # Walk backwards from the latest entry
    cur = 1
    for i in range(len(keys) - 1, 0, -1):
        try:
            d1 = datetime.strptime(keys[i], "%Y-%m-%d").date()
            d0 = datetime.strptime(keys[i-1], "%Y-%m-%d").date()
            if (d1 - d0).days == 1:
                cur += 1
            else:
                break
        except ValueError:
            break
    # Only count if the streak touches today or yesterday
    try:
        last = datetime.strptime(keys[-1], "%Y-%m-%d").date()
    except ValueError:
        return 0
    if (t - last).days > 1:
        return 0
    return cur

def _max_streak(entries):
    keys = sorted(d for d in entries if len(d) == 10)
    if len(keys) < 2:
        return len(keys)
    mx = 1
    cur = 1
    for i in range(1, len(keys)):
        try:
            d1 = datetime.strptime(keys[i-1], "%Y-%m-%d").date()
            d2 = datetime.strptime(keys[i], "%Y-%m-%d").date()
            if (d2 - d1).days == 1:
                cur += 1
                mx = max(mx, cur)
            else:
                cur = 1
        except ValueError:
            cur = 1
    return mx

def _deploy():
    return

# ──── gamification helpers ──────────────────────────────────────────

LEVELS = [
    (0,     1, "Anfänger"),
    (200,   2, "Beständig"),
    (500,   3, "Gewohnheitstier"),
    (1200,  4, "Diszipliniert"),
    (2500,  5, "Stoiker"),
    (5000,  6, "Meister der Routine"),
    (10000, 7, "Marcus Aurelius"),
]

ACHIEVEMENTS = [
    {"id": "first-day",    "name": "Erster Tag",       "icon": "🌱", "desc": "Erstes Habit getrackt"},
    {"id": "week-warrior", "name": "Wochenkrieger",     "icon": "⚔️", "desc": "7-Tage-Streak bei einem Habit"},
    {"id": "month-master", "name": "Monatsmeister",     "icon": "🏆", "desc": "30-Tage-Streak bei einem Habit"},
    {"id": "all-in",       "name": "All-In",            "icon": "💯", "desc": "Alle Habits an einem Tag erledigt"},
    {"id": "fifty-days",   "name": "50 Tage dabei",     "icon": "📅", "desc": "50 Tage mit mindestens 1 Eintrag"},
    {"id": "hundred-days", "name": "100 Tage dabei",    "icon": "🎖️", "desc": "100 Tage mit mindestens 1 Eintrag"},
    {"id": "weight-5",     "name": "5kg geschafft",     "icon": "🔥", "desc": "5 kg seit Start abgenommen"},
    {"id": "level-up-3",   "name": "Gewohnheitstier",   "icon": "🦁", "desc": "Level 3 erreicht"},
    {"id": "level-up-5",   "name": "Stoiker",           "icon": "🏛️", "desc": "Level 5 erreicht"},
    {"id": "level-up-7",   "name": "Marcus Aurelius",   "icon": "👑", "desc": "Level 7 erreicht"},
]


def _calculate_xp(data):
    """Recalculate total XP from all entries — idempotent."""
    habits = data.get("habits", {})
    journal = data.get("journal", {})
    xp = 0

    # Collect all dates that have any entry
    all_dates = set()
    for slug, h in habits.items():
        for d in h.get("entries", {}):
            if len(d) == 10:
                all_dates.add(d)
    for d in journal:
        if len(d) == 10:
            all_dates.add(d)

    for ds in sorted(all_dates):
        day_xp = 0
        tracked_count = 0
        total_habits = len(habits)

        for slug, h in habits.items():
            entries = h.get("entries", {})
            val = entries.get(ds)
            if val is None:
                continue
            tracked_count += 1
            htype = h.get("type", "number")
            if htype == "boolean":
                day_xp += 10
            else:
                day_xp += 5  # any numeric value
                # Target check: for numeric habits, reaching daily target
                # Use unit-based heuristics (any non-zero value counts as target met)
                day_xp += 10  # +15 total for numeric with value

        # Journaling bonus
        if ds in journal:
            day_xp += 20

        # All habits done bonus
        if total_habits > 0 and tracked_count >= total_habits:
            day_xp += 50

        xp += day_xp

    # Streak bonuses — check each habit's max streak milestones
    for slug, h in habits.items():
        entries = h.get("entries", {})
        keys = sorted(d for d in entries if len(d) == 10)
        if len(keys) < 2:
            continue
        # Find all streaks to award milestone bonuses
        cur_streak = 1
        awarded_7 = False
        awarded_30 = False
        for i in range(1, len(keys)):
            try:
                d1 = datetime.strptime(keys[i-1], "%Y-%m-%d").date()
                d2 = datetime.strptime(keys[i], "%Y-%m-%d").date()
                if (d2 - d1).days == 1:
                    cur_streak += 1
                    if cur_streak >= 7 and not awarded_7:
                        xp += 100
                        awarded_7 = True
                    if cur_streak >= 30 and not awarded_30:
                        xp += 500
                        awarded_30 = True
                else:
                    cur_streak = 1
                    awarded_7 = False
                    awarded_30 = False
            except ValueError:
                cur_streak = 1

    return xp


def _get_level(xp):
    """Return (level_number, title, xp_for_this_level, xp_for_next_level)."""
    lvl_num, title, lvl_xp = LEVELS[0]
    next_xp = LEVELS[1][0] if len(LEVELS) > 1 else None
    for i, (threshold, num, t) in enumerate(LEVELS):
        if xp >= threshold:
            lvl_num = num
            title = t
            lvl_xp = threshold
            next_xp = LEVELS[i + 1][0] if i + 1 < len(LEVELS) else None
    return lvl_num, title, lvl_xp, next_xp


def _check_achievements(data, xp, level):
    """Check all achievement conditions, return list of earned ones."""
    habits = data.get("habits", {})
    journal = data.get("journal", {})
    meta = data.get("meta", {})
    earned = data.get("gamification", {}).get("achievements", {})
    today_str = today()

    def award(aid):
        if aid not in earned:
            earned[aid] = today_str

    # first-day: any habit tracked
    for h in habits.values():
        if h.get("entries"):
            award("first-day")
            break

    # week-warrior / month-master: streak milestones
    for h in habits.values():
        ms = _max_streak(h.get("entries", {}))
        if ms >= 7:
            award("week-warrior")
        if ms >= 30:
            award("month-master")

    # all-in: all habits done in one day
    all_dates = set()
    for h in habits.values():
        for d in h.get("entries", {}):
            if len(d) == 10:
                all_dates.add(d)
    total_habits = len(habits)
    if total_habits > 0:
        for ds in all_dates:
            done = sum(1 for h in habits.values() if h.get("entries", {}).get(ds) is not None)
            if done >= total_habits:
                award("all-in")
                break

    # fifty-days / hundred-days: days with at least 1 entry
    entry_dates = set()
    for h in habits.values():
        for d in h.get("entries", {}):
            if len(d) == 10:
                entry_dates.add(d)
    for d in journal:
        if len(d) == 10:
            entry_dates.add(d)
    if len(entry_dates) >= 50:
        award("fifty-days")
    if len(entry_dates) >= 100:
        award("hundred-days")

    # weight-5: lost 5kg from start
    sw = meta.get("start_weight_kg")
    gw = habits.get("gewicht", {}).get("entries", {})
    if sw and gw:
        weights = sorted((k, v) for k, v in gw.items() if isinstance(v, (int, float)))
        if weights:
            current = weights[-1][1]
            if sw - current >= 5:
                award("weight-5")

    # level-based
    if level >= 3:
        award("level-up-3")
    if level >= 5:
        award("level-up-5")
    if level >= 7:
        award("level-up-7")

    return earned

# ──── serve app ───────────────────────────────────────────────────────

@app.route("/")
@app.route("/index.html")
def index():
    return send_from_directory(str(BASE), "index.html")

@app.route("/data.json")
def serve_data():
    return jsonify(load())

# ──── API: overview ──────────────────────────────────────────────────

def _get_overview():
    d = load()
    habits = d.get("habits", {})
    t = today()
    hlist = []
    for slug, h in habits.items():
        entries = h.get("entries", {})
        t_val = entries.get(t)
        hlist.append({
            "slug": slug,
            "label": h.get("label", slug),
            "icon": h.get("icon", "📋"),
            "type": h.get("type", "number"),
            "unit": h.get("unit", ""),
            "today": t_val if t_val is not None else None,
            "streak": _streak(entries),
            "max_streak": _max_streak(entries),
            "total_entries": len(entries),
        })
    gew = habits.get("gewicht", {})
    w_entries = gew.get("entries", {})
    weights = sorted((k, v) for k, v in w_entries.items() if isinstance(v, (int, float)))
    meta = d.get("meta", {})
    today_done = sum(1 for h in hlist if h["today"] is not None)
    total_habits = len(habits)

    # Task 3 (T-0815): Weekly completion rate
    week_done = 0
    week_possible = 0
    for i in range(7):
        ds = days_ago(i)
        for slug_h, hh in habits.items():
            week_possible += 1
            if hh.get("entries", {}).get(ds) is not None:
                week_done += 1
    week_rate = round(week_done / week_possible * 100) if week_possible > 0 else 0
    # Previous week for trend comparison
    last_done = 0
    last_possible = 0
    for i in range(7, 14):
        ds = days_ago(i)
        for slug_h, hh in habits.items():
            last_possible += 1
            if hh.get("entries", {}).get(ds) is not None:
                last_done += 1
    last_rate = round(last_done / last_possible * 100) if last_possible > 0 else 0
    trend = "up" if week_rate > last_rate else ("down" if week_rate < last_rate else "flat")
    today_rate = round(today_done / total_habits * 100) if total_habits > 0 else 0

    return {
        "habits": hlist,
        "total": len(hlist),
        "today_done": today_done,
        "today_total": len(hlist),
        "current_weight": weights[-1][1] if weights else None,
        "weight_trend": round(weights[-1][1] - weights[-2][1], 2) if len(weights) >= 2 else None,
        "start_weight": meta.get("start_weight_kg"),
        "target_weight": meta.get("target_weight_kg"),
        "completion_rate": {
            "today": today_rate,
            "week": week_rate,
            "trend": trend,
        },
    }

@app.route("/api/overview")
def overview():
    return jsonify(_get_overview())

@app.route("/api/habits")
def list_habits():
    d = load()
    habits = d.get("habits", {})
    t = today()
    hlist = []
    for slug, h in habits.items():
        entries = h.get("entries", {})
        t_val = entries.get(t)
        hlist.append({
            "slug": slug,
            "label": h.get("label", slug),
            "icon": h.get("icon", "📋"),
            "type": h.get("type", "number"),
            "unit": h.get("unit", ""),
            "inverted": h.get("inverted", False),
            "chart": h.get("chart", False),
            "today": t_val,
            "entries": entries,
            "streak": _streak(entries),
            "max_streak": _max_streak(entries),
            "total_entries": len(entries),
        })
    return jsonify(hlist)

# ──── API: habits CRUD ───────────────────────────────────────────────

@app.route("/api/habit", methods=["POST"])
def add_habit():
    body = request.json or {}
    label = (body.get("label") or "").strip()
    if not label:
        return jsonify({"error": "label required"}), 400
    d = load()
    slug = _slug(label, d.get("habits", {}))
    d.setdefault("habits", {})[slug] = {
        "label": label,
        "icon": body.get("icon", "⬜"),
        "unit": body.get("unit", ""),
        "type": body.get("type", "number"),
        "entries": {},
    }
    h = d["habits"][slug]
    if body.get("inverted"):
        h["inverted"] = True
    if body.get("chart"):
        h["chart"] = True
    save(d)
    return jsonify({"ok": True, "slug": slug})

@app.route("/api/habit/<slug>", methods=["PUT"])
def edit_habit(slug):
    body = request.json or {}
    d = load()
    if slug not in d.get("habits", {}):
        return jsonify({"error": "not found"}), 404
    h = d["habits"][slug]
    for key in ("label", "icon", "unit", "type"):
        if key in body:
            h[key] = body[key]
    if "inverted" in body:
        h["inverted"] = body["inverted"]
    if "chart" in body:
        h["chart"] = body["chart"]
    save(d)
    return jsonify({"ok": True})

@app.route("/api/habit/<slug>", methods=["DELETE"])
def delete_habit(slug):
    d = load()
    if slug in d.get("habits", {}):
        del d["habits"][slug]
        save(d)
    return jsonify({"ok": True})

# ──── API: tracking ──────────────────────────────────────────────────

@app.route("/api/track", methods=["PUT"])
def track():
    body = request.json or {}
    slug = body.get("slug")
    if not slug:
        return jsonify({"error": "slug required"}), 400
    d = load()
    if slug not in d.get("habits", {}):
        return jsonify({"error": "habit not found"}), 404
    h = d["habits"][slug]
    entries = h.setdefault("entries", {})
    is_bool = h.get("type") == "boolean"
    track_date = body.get("date", today())
    
    if is_bool:
        if entries.get(track_date) is not None:
            del entries[track_date]
            saved = None
        else:
            entries[track_date] = True
            saved = True
    else:
        val = body.get("value")
        if val is None:
            return jsonify({"error": "value required"}), 400
        try:
            val = float(val)
        except (ValueError, TypeError):
            return jsonify({"error": "invalid value"}), 400
        entries[track_date] = val
        saved = val
    
    save(d)
    return jsonify({"ok": True, "value": saved, "streak": _streak(entries)})

@app.route("/api/weight", methods=["PUT"])
def track_weight():
    body = request.json or {}
    w = body.get("weight")
    if w is None:
        return jsonify({"error": "weight required"}), 400
    try:
        w = float(w)
    except (ValueError, TypeError):
        return jsonify({"error": "invalid weight"}), 400
    d = load()
    d.setdefault("habits", {}).setdefault("gewicht", {"label": "Gewicht", "icon": "⚖️", "unit": "kg", "chart": True, "entries": {}})
    d["habits"]["gewicht"]["entries"][today()] = w
    if not d.get("meta", {}).get("start_weight_kg"):
        d.setdefault("meta", {})["start_weight_kg"] = w
    if body.get("target"):
        d["meta"]["target_weight_kg"] = body["target"]
    save(d)
    return jsonify({"ok": True, "weight": w})

# ──── API: goals (T-0814) ───────────────────────────────────────────
# GET /api/goals — returns all goals with current progress
# PUT /api/goal — create or update a goal
# DELETE /api/goal/<slug> — remove a goal

@app.route("/api/goals")
def get_goals():
    d = load()
    goals = d.get("goals", {})
    habits = d.get("habits", {})
    result = {}
    for slug, g in goals.items():
        metric = g.get("metric", "")
        target = g.get("target", 0)
        direction = g.get("direction", "up")
        start_value = g.get("start_value", 0)
        contributing = g.get("contributing_habits", [])
        # Current value depends on metric type
        if metric == "streak":
            current = 0
            for ch in contributing:
                h = habits.get(ch, {})
                current = max(current, _streak(h.get("entries", {})))
        else:
            # Habit-slug metric (e.g. "gewicht")
            h = habits.get(metric, {})
            w_entries = h.get("entries", {})
            vals = sorted((k, v) for k, v in w_entries.items() if isinstance(v, (int, float)))
            current = vals[-1][1] if vals else start_value
        # Progress %
        if direction == "down":
            total_range = start_value - target
            done = start_value - current
        else:
            total_range = target - start_value
            done = current - start_value
        pct = round(done / total_range * 100) if total_range != 0 else 0
        pct = max(0, min(100, pct))
        trend = "positive" if done > 0 else "flat"
        result[slug] = {
            **g,
            "current_value": current,
            "progress_pct": pct,
            "trend": trend,
            "remaining": round(abs(current - target), 1),
        }
    return jsonify(result)

@app.route("/api/goal", methods=["PUT"])
def put_goal():
    body = request.json or {}
    slug = (body.get("slug") or "").strip()
    if not slug:
        return jsonify({"error": "slug required"}), 400
    d = load()
    d.setdefault("goals", {})[slug] = {
        "label": body.get("label", slug),
        "icon": body.get("icon", "🎯"),
        "metric": body.get("metric", ""),
        "target": body.get("target", 0),
        "direction": body.get("direction", "up"),
        "start_value": body.get("start_value", 0),
        "start_date": body.get("start_date", today()),
        "contributing_habits": body.get("contributing_habits", []),
    }
    save(d)
    return jsonify({"ok": True, "slug": slug})

@app.route("/api/goal/<slug>", methods=["DELETE"])
def delete_goal(slug):
    d = load()
    if slug in d.get("goals", {}):
        del d["goals"][slug]
        save(d)
    return jsonify({"ok": True})

# ──── API: journal ──────────────────────────────────────────────────

# ──── API: gamification (T-0820/0821/0822) ────────────────────────

@app.route("/api/gamification")
def gamification():
    d = load()
    xp = _calculate_xp(d)
    level, title, lvl_xp, next_xp = _get_level(xp)
    achievements = _check_achievements(d, xp, level)

    # Update gamification section in data.json
    g = d.setdefault("gamification", {})
    g["xp"] = xp
    g["level"] = level
    g["title"] = title
    g["achievements"] = achievements
    save(d)

    if next_xp is not None:
        xp_to_next = next_xp - xp
        progress_pct = round((xp - lvl_xp) / (next_xp - lvl_xp) * 100) if next_xp > lvl_xp else 100
    else:
        xp_to_next = 0
        progress_pct = 100

    # Build achievement list with earned status
    ach_list = []
    for a in ACHIEVEMENTS:
        earned_date = achievements.get(a["id"])
        ach_list.append({
            **a,
            "earned": earned_date is not None,
            "earned_date": earned_date,
        })

    return jsonify({
        "xp": xp,
        "level": level,
        "title": title,
        "xp_to_next_level": max(0, xp_to_next),
        "progress_pct": max(0, min(100, progress_pct)),
        "level_xp": lvl_xp,
        "next_level_xp": next_xp,
        "last_seen_level": g.get("last_seen_level", 1),
        "achievements": ach_list,
    })

@app.route("/api/gamification/seen", methods=["PUT"])
def gamification_seen():
    """Mark the current level as seen (dismiss level-up notification)."""
    d = load()
    g = d.setdefault("gamification", {})
    g["last_seen_level"] = g.get("level", 1)
    save(d)
    return jsonify({"ok": True})

# ──── API: journal ──────────────────────────────────────────────────

@app.route("/api/journal", methods=["POST"])
def journal_add():
    body = request.json or {}
    text = (body.get("text") or "").strip()
    if not text:
        return jsonify({"error": "text required"}), 400
    d = load()
    d.setdefault("journal", {})[body.get("date", today())] = text
    save(d)
    return jsonify({"ok": True})

@app.route("/api/journal", methods=["GET"])
def journal_list():
    d = load()
    items = sorted(d.get("journal", {}).items(), reverse=True)[:14]
    return jsonify(items)

# ──── main ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        r = subprocess.run(["tailscale", "ip", "-4"], capture_output=True, text=True, timeout=5)
        ip = r.stdout.strip() or "0.0.0.0"
    except Exception:
        ip = "0.0.0.0"
    port = int(os.environ.get("HABITS_PORT", "8078"))
    print(f"Habits: http://{ip}:{port}")
    app.run(host=ip, port=port, debug=False, threaded=True)
