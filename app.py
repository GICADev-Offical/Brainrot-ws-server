import os
from flask import Flask, jsonify
import requests
from datetime import datetime

app = Flask(__name__)

PLACE_ID = "109983668079237"
MIN_PLAYERS = 3
MAX_PLAYERS = 8

current_job_id = None
current_players = 0
last_scan_time = "Nie"

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
    except:
        pass
    return None

@app.route('/')
def home():
    return "Brainrot AutoJoiner laeuft!"

@app.route('/jobid')
def get_job_id():
    global current_job_id
    job_id = get_server()
    if job_id:
        current_job_id = job_id
        return job_id  # KLARTEXT!
    return "WAITING"

@app.route('/status')
def get_status():
    return jsonify({
        "status": "online",
        "job_id": current_job_id or "Keine",
        "players": current_players,
        "filter": f"{MIN_PLAYERS}-{MAX_PLAYERS} Spieler"
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
