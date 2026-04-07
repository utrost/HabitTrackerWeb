#!/usr/bin/env python3
"""
Uwe Habit Tracker — Flask API Server
Tailscale-only, writes directly to data.json.
Port: 8078
"""

import json
import os
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from flask import Flask, jsonify, request, send_file, abort

# ── Paths ──────────────────────────────────────────────────────────────
DATA_DIR = Path.home() / '.openclaw' / 'workspace' / 'stoic-uwe'
DATA_FILE = DATA_DIR / 'data.json'
BACKUP_DIR = Path.home() / '.openclaw' / 'workspace' / 'stoic-uwe' / 'backups'
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__, static_folder=str(DATA_DIR))

# ── Helpers ────────────────────────────────────────────────────────────

def load_data():
    if not DATA_FILE.exists():
        return default_data()
    return json.loads(DATA_FILE.read_text(encoding='utf-8'))

def save_data(data):
    # Backup with date
    backup_name = f"data-{date.today().isoformat()}.json"
    backup_path = BACKUP_DIR / backup_name
    if not backup_path.exists():
        backup_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    # Save main file
    DATA_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    # Deploy to simiono.com
    deploy_to_simiono()

def deploy_to_simiono():
    """Deploy habits to simiono.com/habits/ via FTP."""
    try:
        subprocess.run([
            'lftp', '-u', 'trosth_1,d8$XW#Lo;]QM', 'www458.your-server.de', '-e',
            f'mkdir -p /habits/; put {DATA_DIR}/tracking.html -o /habits/index.html; put {DATA_FILE} -o /habits/data.json; quit'
        ], capture_output=True, timeout=30)
    except Exception:
        pass

def default_data():
    return {
        "habits": {},
        "journal": {},
        "meta": {
            "start_date": date.today().isoformat(),
            "start_weight_kg": None,
            "target_weight_kg": None,
            "version": 2
        }
    }

def today_str():
    return date.today().isoformat()

def gen_slug(label):
    """Generate a slug from a label."""
    import re
    s = label.lower().strip()
    s = re.sub(r'[^\w\s-]', '', s)
    s = re.sub(r'[\s_]+', '-', s)
    # Make unique
    base = s
    data = load_data()
    counter = 1
    while s in data.get('habits', {}):
        counter += 1
        s = f"{base}-{counter}"
    return s

# ── Stats helpers ──────────────────────────────────────────────────────

def calc_streak(entries):
    """Calculate current streak (consecutive days with a value)."""
    if not entries:
        return 0
    dates = sorted(entries.keys(), reverse=True)
    today = date.today()
    streak = 0
    for i, ds in enumerate(dates):
        try:
            d = datetime.strptime(ds, '%Y-%m-%d').date()
        except ValueError:
            continue
        expected = today - timedelta(days=i)
        if d == expected:
            streak += 1
        else:
            break
    # Allow streak to start from yesterday if today hasn't been tracked yet
    if streak == 0 and dates:
        try:
            last = datetime.strptime(dates[0], '%Y-%m-%d').date()
            if last == today - timedelta(days=1):
                return 0
        except ValueError:
            pass
    return streak

def calc_max_streak(entries):
    """Calculate longest streak ever."""
    if not entries:
        return 0
    dates = sorted(k for k in entries.keys() if k[0:4].isdigit())
    if not dates:
        return 0
    max_streak = 1
    current = 1
    for i in range(1, len(dates)):
        try:
            d1 = datetime.strptime(dates[i-1], '%Y-%m-%d').date()
            d2 = datetime.strptime(dates[i], '%Y-%m-%d').date()
            if (d2 - d1).days == 1:
                current += 1
                max_streak = max(max_streak, current)
            else:
                current = 1
        except ValueError:
            current = 1
    return max_streak

def last_7_days():
    today = date.today()
    return [(today - timedelta(days=i)).isoformat() for i in range(6, -1, -1)]

# ── Routes ─────────────────────────────────────────────────────────────

@app.route('/')
@app.route('/index.html')
def serve_ui():
    html_file = DATA_DIR / 'tracking.html'
    if html_file.exists():
        return send_file(str(html_file))
    return '<h1>Habits</h1><p>Deploy tracking.html to stoic-uwe/</p>'

@app.route('/data.json')
def get_data():
    return jsonify(load_data())

@app.route('/api/status')
def api_status():
    data = load_data()
    habits = data.get('habits', {})
    today = today_str()
    today_count = sum(1 for h in habits.values() if today in h.get('entries', {}))
    return jsonify({
        'status': 'ok',
        'habits': len(habits),
        'today_tracked': today_count,
        'today_target': len(habits),
        'timestamp': datetime.now().isoformat(),
    })

@app.route('/api/habits', methods=['GET'])
def list_habits():
    data = load_data()
    today = today_str()
    result = []
    for slug, habit in data.get('habits', {}).items():
        entries = habit.get('entries', {})
        is_boolean = habit.get('type', 'number') == 'boolean'
        result.append({
            'slug': slug,
            'label': habit.get('label', slug),
            'icon': habit.get('icon', '📋'),
            'type': 'boolean' if is_boolean else 'number',
            'unit': habit.get('unit', ''),
            'inverted': habit.get('inverted', False),
            'chart': habit.get('chart', False),
            'entries': entries,
            'today': entries.get(today),
            'streak': calc_streak(entries),
            'max_streak': calc_max_streak(entries),
            'total_days': len(entries),
        })
    return jsonify(result)

@app.route('/api/habits', methods=['POST'])
def add_habit():
    data = request.get_json() or {}
    label = data.get('label', '').strip()
    if not label:
        return jsonify({'error': 'label required'}), 400
    
    habit_type = data.get('type', 'number')  # 'number' or 'boolean'
    icon = data.get('icon', '📋')
    unit = data.get('unit', '')
    inverted = data.get('inverted', False)

    slug = gen_slug(label)
    data_store = load_data()
    data_store['habits'][slug] = {
        'label': label,
        'type': habit_type,
        'icon': icon,
        'entries': {},
    }
    if habit_type == 'number':
        data_store['habits'][slug]['unit'] = unit
    if inverted:
        data_store['habits'][slug]['inverted'] = True
    
    save_data(data_store)
    return jsonify({'ok': True, 'slug': slug, 'label': label})

@app.route('/api/habits/<slug>', methods=['DELETE'])
def delete_habit(slug):
    data = load_data()
    if slug not in data.get('habits', {}):
        return jsonify({'error': f'Habit {slug} not found'}), 404
    del data['habits'][slug]
    save_data(data)
    return jsonify({'ok': True, 'slug': slug})

@app.route('/api/track/<slug>', methods=['POST'])
def track(slug):
    """Track a value for a habit."""
    data = request.get_json() or {}
    value = data.get('value')
    track_date = data.get('date', today_str())
    
    if value is None and 'value' in data:
        value = data['value']
    # boolean toggle
    if value is None:
        value = True

    store = load_data()
    if slug not in store.get('habits', {}):
        return jsonify({'error': f'Habit {slug} not found'}), 404

    habit = store['habits'][slug]
    is_boolean = habit.get('type', 'number') == 'boolean'

    if is_boolean:
        # Toggle: if already tracked for date, remove it (toggle off)
        if track_date in habit.get('entries', {}):
            del habit['entries'][track_date]
            saved_value = None
        else:
            habit['entries'][track_date] = True
            saved_value = True
    else:
        # Numeric value
        try:
            value = float(value)
        except (ValueError, TypeError):
            return jsonify({'error': 'Numeric value required'}), 400
        if 'entries' not in habit:
            habit['entries'] = {}
        habit['entries'][track_date] = value
        saved_value = value

    save_data(store)
    habit_obj = store['habits'].get(slug, {})
    return jsonify({
        'ok': True,
        'slug': slug,
        'value': saved_value,
        'date': track_date,
        'streak': calc_streak(habit_obj.get('entries', {})),
    })

@app.route('/api/journal', methods=['GET'])
def get_journal():
    data = load_data()
    journal = data.get('journal', {})
    # Return last 14 entries
    entries = sorted(journal.items(), key=lambda x: x[0], reverse=True)[:14]
    return jsonify(entries)

@app.route('/api/journal', methods=['POST'])
def add_journal():
    data = request.get_json() or {}
    text = data.get('text', '').strip()
    jdate = data.get('date', today_str())
    if not text:
        return jsonify({'error': 'text required'}), 400

    store = load_data()
    store['journal'][jdate] = text
    save_data(store)
    return jsonify({'ok': True, 'date': jdate})

@app.route('/api/overview', methods=['GET'])
def overview():
    """Get a quick overview for the UI."""
    data = load_data()
    habits = data.get('habits', {})
    today = today_str()
    seven = last_7_days()
    
    overview = {
        'total_habits': len(habits),
        'today_tracked': 0,
        'today_total': len(habits),
        'week_summary': [],
        'meta': data.get('meta', {}),
    }
    
    for slug, habit in habits.items():
        entries = habit.get('entries', {})
        is_boolean = habit.get('type', 'number') == 'boolean'
        
        if today in entries:
            overview['today_tracked'] += 1
        
        # Week data
        week_data = []
        for d in seven:
            val = entries.get(d)
            week_data.append({
                'date': d,
                'tracked': val is not None,
                'value': val,
            })
        
        overview['week_summary'].append({
            'slug': slug,
            'label': habit.get('label', slug),
            'icon': habit.get('icon', '📋'),
            'type': 'boolean' if is_boolean else 'number',
            'unit': habit.get('unit', ''),
            'streak': calc_streak(entries),
            'week': week_data,
        })
    
    return jsonify(overview)

# ── Main ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    # Get Tailscale IP
    try:
        result = subprocess.run(['tailscale', 'ip', '-4'], capture_output=True, text=True, timeout=5)
        ip = result.stdout.strip() or '100.86.120.118'
    except Exception:
        ip = '100.86.120.118'
    
    port = int(os.environ.get('HABITS_PORT', '8078'))
    print(f"Habit Tracker: http://{ip}:{port}")
    app.run(host=ip, port=port, debug=False, threaded=True)
