import os
from flask import Flask
import requests
import base64

app = Flask(__name__)

PLACE_ID = "109983668079237"
MIN_PLAYERS = 3
MAX_PLAYERS = 4
SECRET_KEY = 42

def get_server():
    url = f"https://games.roblox.com/v1/games/{PLACE_ID}/servers/Public?limit=100"
    try:
        r = requests.get(url, timeout=10)
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
                job_id = best.get("id")
                xored = "".join(chr(ord(c) ^ SECRET_KEY) for c in job_id)
                encoded = base64.b64encode(xored.encode()).decode()
                return encoded
    except:
        pass
    return "WAITING"

@app.route('/jobid')
def get_job_id():
    return get_server()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
