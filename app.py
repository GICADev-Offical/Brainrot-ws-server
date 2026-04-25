import os
import asyncio
import json
from datetime import datetime
import requests
from flask import Flask, jsonify, request
import threading

app = Flask(__name__)

PLACE_ID = "109983668079237"
MIN_PLAYERS = 3
MAX_PLAYERS = 7

current_job_id = None
current_players = 0
bot_finds = []

def get_server():
    global current_players
    url = f"https://games.roblox.com/v1/games/{PLACE_ID}/servers/Public?limit=100"
    try:
        r = requests.get(url, timeout=10)
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

# WebSocket Handler (Simple)
async def ws_handler(websocket, path):
    async for message in websocket:
        try:
            data = json.loads(message)
            if data.get("type") == "botreport":
                data['reported_at'] = datetime.now().strftime("%H:%M:%S")
                bot_finds.insert(0, data)
                if len(bot_finds) > 20:
                    bot_finds.pop()
                await websocket.send(json.dumps({"status": "ok"}))
        except:
            pass

def start_ws_server():
    import websockets
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    server = websockets.serve(ws_handler, "0.0.0.0", 8080)
    loop.run_until_complete(server)
    loop.run_forever()

# Starte WebSocket in eigenem Thread
threading.Thread(target=start_ws_server, daemon=True).start()

@app.route('/')
def home():
    return "✅ FallenHub läuft!"

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
    return jsonify({"status": "online", "bot_finds": len(bot_finds)})

@app.route('/botreport', methods=['POST'])
def bot_report():
    data = request.json
    if data:
        data['reported_at'] = datetime.now().strftime("%H:%M:%S")
        bot_finds.insert(0, data)
        if len(bot_finds) > 20:
            bot_finds.pop()
        return jsonify({"status": "ok"})
    return jsonify({"status": "error"}), 400

@app.route('/botfinds')
def get_bot_finds():
    return jsonify(bot_finds)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
