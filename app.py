import os
import random
from flask import Flask, jsonify
import requests
import base64
from datetime import datetime

app = Flask(__name__)

# === KONFIGURATION ===
PLACE_ID = "109983668079237"
MIN_PLAYERS = 3  # Wieder 3-4 für bessere Pets!
MAX_PLAYERS = 4
SECRET_KEY = 42
MAX_RESULTS = 30  # Mehr Ergebnisse
SCAN_COOLDOWN = 12
# =====================

cached_jobs = []
cached_index = 0
last_scan_time = "Nie"
last_full_scan = 0

debug_info = {
    "api_status": "unbekannt",
    "total_servers_api": 0,
    "matching_servers": 0,
    "pages_scanned": 0
}

def obfuscate_job_id(job_id):
    if not job_id:
        return ""
    xored = "".join(chr(ord(c) ^ SECRET_KEY) for c in job_id)
    return base64.b64encode(xored.encode()).decode()

def fetch_servers_page(url):
    """Holt eine Seite der API"""
    try:
        r = requests.get(url, timeout=8, headers={
            "User-Agent": "Roblox/WinInet",
            "Accept": "application/json"
        })
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None

def fetch_all_servers():
    """Holt Server mit VERSCHIEDENEN Sortierungen für bessere Abdeckung"""
    global last_scan_time, debug_info
    
    all_servers = []
    pages_scanned = 0
    
    # 🔄 Verschiedene Sortierungen durchprobieren
    sort_options = [
        "2",   # Nach Spielerzahl absteigend (volle zuerst)
        "1",   # Nach Spielerzahl aufsteigend (leere zuerst)
        "Asc", # Alphabetisch (andere Reihenfolge)
        "Desc" # Alphabetisch absteigend
    ]
    
    for sort in sort_options:
        base_url = f"https://games.roblox.com/v1/games/{PLACE_ID}/servers/Public?limit=100&sortOrder={sort}"
        
        # Pro Sortierung bis zu 3 Seiten holen
        current_url = base_url
        for page in range(3):
            data = fetch_servers_page(current_url)
            
            if data:
                servers = data.get("data", [])
                all_servers.extend(servers)
                pages_scanned += 1
                
                next_cursor = data.get("nextPageCursor")
                if not next_cursor:
                    break
                current_url = f"{base_url}&cursor={next_cursor}"
            else:
                break
    
    debug_info["total_servers_api"] = len(all_servers)
    debug_info["pages_scanned"] = pages_scanned
    last_scan_time = datetime.now().strftime("%H:%M:%S")
    
    print(f"📡 {len(all_servers)} Server von {pages_scanned} Seiten eingesammelt")
    
    # 🔀 ALLES gründlich mischen
    random.shuffle(all_servers)
    random.shuffle(all_servers)  # Zweimal für extra Zufälligkeit
    
    # 🎯 Passende Server finden
    matching = []
    seen_ids = set()  # Verhindert Duplikate
    
    for s in all_servers:
        p = s.get("playing", 0)
        max_p = s.get("maxPlayers", 8)
        job_id = s.get("id")
        
        # Nur Server mit 3-4 Spielern, nicht voll, keine Duplikate
        if MIN_PLAYERS <= p <= MAX_PLAYERS and p < max_p and job_id and job_id not in seen_ids:
            seen_ids.add(job_id)
            matching.append(job_id)
            
            if len(matching) >= MAX_RESULTS:
                break
    
    debug_info["matching_servers"] = len(matching)
    print(f"🎯 {len(matching)} passende Server (3-4 Spieler)")
    
    return matching

def refresh_cache_if_needed():
    global cached_jobs, cached_index, last_full_scan
    
    now = datetime.now().timestamp()
    
    if len(cached_jobs) == 0 or (now - last_full_scan) > SCAN_COOLDOWN:
        print("🔄 Neuer Scan...")
        raw_jobs = fetch_all_servers()
        
        if raw_jobs and len(raw_jobs) > 0:
            cached_jobs = [obfuscate_job_id(j) for j in raw_jobs]
            cached_index = 0
            last_full_scan = now
            print(f"✅ {len(cached_jobs)} Jobs im Cache")
            return True
        else:
            print("❌ Keine passenden Server!")
            return False
    
    return True

def get_next_job():
    global cached_index
    
    refresh_cache_if_needed()
    
    if len(cached_jobs) == 0:
        return "WAITING"
    
    job = cached_jobs[cached_index]
    cached_index += 1
    
    if cached_index >= len(cached_jobs):
        cached_index = 0
    
    return job

# === ROUTES ===

@app.route('/')
def home():
    return "✅ Brainrot AutoJoiner laeuft!"

@app.route('/jobid')
def get_job_id():
    return get_next_job()

@app.route('/jobs')
def get_all_jobs():
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
        "last_scan": last_scan_time,
        "debug": debug_info
    })

@app.route('/debug')
def get_debug():
    refresh_cache_if_needed()
    return jsonify({
        "cached_jobs_count": len(cached_jobs),
        "debug": debug_info
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
