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
    return {
        "habits": hlist,
        "total": len(hlist),
        "today_done": today_done,
        "today_total": len(hlist),
        "current_weight": weights[-1][1] if weights else None,
        "weight_trend": round(weights[-1][1] - weights[-2][1], 2) if len(weights) >= 2 else None,
        "start_weight": meta.get("start_weight_kg"),
        "target_weight": meta.get("target_weight_kg"),
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
