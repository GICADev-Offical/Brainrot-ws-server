import os
from flask import Flask, jsonify, request
import requests
from datetime import datetime

app = Flask(__name__)

PLACE_ID = "109983668079237"
MIN_PLAYERS = 3
MAX_PLAYERS = 7

current_job_id = None
current_players = 0
last_scan_time = "Nie"

# Speicher für Bot-Funde
bot_finds = []

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
                if MIN_PLAYERS <= p <= MAX_PLAYERS and p > best_players:
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
    return "✅ FallenHub AutoJoiner läuft!"

@app.route('/jobid')
def get_job_id():
    global current_job_id
    job_id = get_server()
    if job_id:
        current_job_id = job_id
        return job_id
    return "WAITING"

@app.route('/status')
def get_status():
    return jsonify({
        "status": "online",
        "job_id": current_job_id or "Keine",
        "players": current_players,
        "filter": f"{MIN_PLAYERS}-{MAX_PLAYERS} Spieler",
        "bot_finds": len(bot_finds)
    })

# NEU: Bot meldet Fund
@app.route('/botreport', methods=['POST'])
def bot_report():
    data = request.json
    if data and 'jobId' in data:
        data['reported_at'] = datetime.now().strftime("%H:%M:%S")
        bot_finds.insert(0, data)
        if len(bot_finds) > 20:
            bot_finds.pop()
        return jsonify({"status": "ok"})
    return jsonify({"status": "error"}), 400

# NEU: Funde abrufen
@app.route('/botfinds')
def get_bot_finds():
    return jsonify(bot_finds)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
