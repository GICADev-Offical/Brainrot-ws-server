import os
import random
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
MAX_RESULTS = 20  # ⬅️ Bis zu 20 Job-IDs speichern!
SCAN_COOLDOWN = 15  # Sekunden zwischen Vollscans
# =====================

# Cache
cached_jobs = []       # Liste mit obfuskierten Job-IDs
cached_index = 0       # Welche ID als nächstes ausgeben
last_scan_time = "Nie"
last_full_scan = 0
current_players = 0

def obfuscate_job_id(job_id):
    if not job_id:
        return ""
    xored = "".join(chr(ord(c) ^ SECRET_KEY) for c in job_id)
    return base64.b64encode(xored.encode()).decode()

def fetch_all_servers():
    """Holt ALLE Server (mehrere Seiten) und filtert passende"""
    global last_scan_time, current_players
    
    api_url = f"https://games.roblox.com/v1/games/{PLACE_ID}/servers/Public?limit=100"
    all_servers = []
    
    try:
        for _ in range(5):  # Bis zu 5 Seiten = 500 Server
            r = requests.get(api_url, timeout=8)
            if r.status_code == 200:
                data = r.json()
                all_servers.extend(data.get("data", []))
                next_cursor = data.get("nextPageCursor")
                if not next_cursor:
                    break
                api_url = f"https://games.roblox.com/v1/games/{PLACE_ID}/servers/Public?limit=100&cursor={next_cursor}"
        
        last_scan_time = datetime.now().strftime("%H:%M:%S")
        
        # Passende Server filtern
        matching = []
        for s in all_servers:
            p = s.get("playing", 0)
            job_id = s.get("id")
            if MIN_PLAYERS <= p <= MAX_PLAYERS and job_id:
                matching.append(job_id)
        
        # Zufällig mischen
        random.shuffle(matching)
        
        # Auf MAX_RESULTS begrenzen
        result = matching[:MAX_RESULTS]
        
        if len(result) > 0:
            current_players = len(result)
            print(f"✅ {len(result)} Server gefunden und gecached")
        
        return result
        
    except Exception as e:
        print(f"❌ API-Fehler: {e}")
        return []

def refresh_cache_if_needed():
    """Aktualisiert den Cache wenn leer oder Cooldown vorbei"""
    global cached_jobs, cached_index, last_full_scan
    
    now = datetime.now().timestamp()
    
    if len(cached_jobs) == 0 or (now - last_full_scan) > SCAN_COOLDOWN:
        raw_jobs = fetch_all_servers()
        if raw_jobs:
            # Obfuskieren und speichern
            cached_jobs = [obfuscate_job_id(j) for j in raw_jobs]
            cached_index = 0
            last_full_scan = now
            print(f"🔄 Cache aktualisiert: {len(cached_jobs)} Jobs")

def get_next_job():
    """Gibt die nächste Job-ID aus dem Cache zurück"""
    global cached_index
    
    refresh_cache_if_needed()
    
    if len(cached_jobs) == 0:
        return "WAITING"
    
    # Nächste ID holen
    job = cached_jobs[cached_index]
    
    # Index erhöhen für nächstes Mal
    cached_index += 1
    
    # Wenn alle durch, von vorne anfangen
    if cached_index >= len(cached_jobs):
        cached_index = 0
        print("🔄 Alle Jobs ausgegeben, starte von vorne")
    
    return job

# === ROUTES ===

@app.route('/')
def home():
    return "✅ Brainrot AutoJoiner läuft!"

@app.route('/jobid')
def get_job_id():
    """Gibt EINE Job-ID zurück (immer die nächste aus dem Cache)"""
    return get_next_job()

@app.route('/jobs')
def get_all_jobs():
    """Gibt ALLE gecachten Job-IDs auf einmal zurück"""
    refresh_cache_if_needed()
    return jsonify({
        "count": len(cached_jobs),
        "job_ids": cached_jobs
    })

@app.route('/status')
def get_status():
    refresh_cache_if_needed()
    return jsonify({
        "status": "online",
        "cached_jobs": len(cached_jobs),
        "current_index": cached_index,
        "filter": f"{MIN_PLAYERS}-{MAX_PLAYERS} Spieler",
        "last_scan": last_scan_time
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
