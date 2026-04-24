import os
from flask import Flask, jsonify
import requests
import base64
from datetime import datetime

app = Flask(__name__)

# === KONFIGURATION ===
PLACE_ID = "109983668079237"
MIN_PLAYERS = 2
MAX_PLAYERS = 7
SECRET_KEY = 42
# =====================

current_job_id = None
current_players = 0
last_scan_time = "Nie"

def obfuscate_job_id(job_id):
    if not job_id:
        return ""
    xored = "".join(chr(ord(c) ^ SECRET_KEY) for c in job_id)
    encoded = base64.b64encode(xored.encode()).decode()
    return encoded

def get_server():
    global current_players, last_scan_time
    url = f"https://games.roblox.com/v1/games/{PLACE_ID}/servers/Public?limit=100"
    try:
        r = requests.get(url, timeout=10)
        last_scan_time = datetime.now().strftime("%H:%M:%S")
        if r.status_code == 200:
            data = r.json()
            best = None
            best_players = 0
            for s in data.get("data", []):
                p = s.get("playing", 0)
                if p in (MIN_PLAYERS, MAX_PLAYERS) and p > best_players:
                    best_players = p
                    best = s
            if best:
                current_players = best_players
                return best.get("id")
    except Exception as e:
        print(f"Fehler: {e}")
    return None

@app.route('/')
def home():
    return "Brainrot AutoJoiner läuft! Nutze /jobid oder /status"

@app.route('/jobid')
def get_job_id():
    global current_job_id
    job_id = get_server()
    if job_id:
        current_job_id = job_id
        return obfuscate_job_id(job_id)
    return "WAITING"

@app.route('/status')
def get_status():
    global current_job_id, current_players, last_scan_time
    return jsonify({
        "server": "Brainrot AutoJoiner",
        "status": "online",
        "current_job_id": current_job_id or "Keine",
        "players": current_players,
        "filter": f"{MIN_PLAYERS}-{MAX_PLAYERS} Spieler",
        "last_scan": last_scan_time
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
