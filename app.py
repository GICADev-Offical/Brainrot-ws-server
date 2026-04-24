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
MAX_RESULTS = 10
CACHE_SIZE = 50
# =====================

last_scan_time = "Nie"
sent_jobs = set()
all_found_servers = []
last_full_scan = 0
SCAN_COOLDOWN = 10  # Sekunden zwischen Vollscans

def obfuscate_job_id(job_id):
    if not job_id:
        return ""
    xored = "".join(chr(ord(c) ^ SECRET_KEY) for c in job_id)
    return base64.b64encode(xored.encode()).decode()

def fetch_all_servers():
    """Holt ALLE Server von der Roblox-API (mehrere Seiten)"""
    global last_scan_time
    
    api_url = f"https://games.roblox.com/v1/games/{PLACE_ID}/servers/Public?limit=100"
    all_servers = []
    
    try:
        for page in range(5):  # Bis zu 5 Seiten = 500 Server
            r = requests.get(api_url, timeout=8)
            if r.status_code == 200:
                data = r.json()
                servers = data.get("data", [])
                all_servers.extend(servers)
                
                next_cursor = data.get("nextPageCursor")
                if not next_cursor:
                    break
                api_url = f"https://games.roblox.com/v1/games/{PLACE_ID}/servers/Public?limit=100&cursor={next_cursor}"
            else:
                break
        
        last_scan_time = datetime.now().strftime("%H:%M:%S")
        print(f"📡 {len(all_servers)} Server gefunden")
        
    except Exception as e:
        print(f"❌ API-Fehler: {e}")
    
    return all_servers

def filter_matching_servers(servers):
    """Filtert Server nach MIN_PLAYERS-MAX_PLAYERS und ignoriert bereits gesendete"""
    matching = []
    
    # Zufällig mischen für Abwechslung
    random.shuffle(servers)
    
    for s in servers:
        job_id = s.get("id")
        p = s.get("playing", 0)
        max_p = s.get("maxPlayers", 8)
        
        # Nur passende Server die NICHT im Cache sind
        if MIN_PLAYERS <= p <= MAX_PLAYERS and job_id not in sent_jobs:
            matching.append({
                "job_id": job_id,
                "players": p,
                "maxPlayers": max_p,
                "obfuscated": obfuscate_job_id(job_id)
            })
            
            # Zum Cache hinzufügen
            sent_jobs.add(job_id)
            
            # Genug Ergebnisse?
            if len(matching) >= MAX_RESULTS:
                break
    
    # Cache begrenzen
    if len(sent_jobs) > CACHE_SIZE:
        # Alte Einträge entfernen (älteste Hälfte löschen)
        to_remove = list(sent_jobs)[:len(sent_jobs)//2]
        for old in to_remove:
            sent_jobs.discard(old)
        print(f"🗑️ Cache bereinigt: {len(sent_jobs)} Einträge")
    
    return matching

def get_servers_smart():
    """Smarte Funktion: Nutzt Cache wenn möglich, sonst neuer Scan"""
    global all_found_servers, last_full_scan
    
    now = datetime.now().timestamp()
    
    # Wenn Cache leer oder Cooldown vorbei → Neuer Vollscan
    if len(all_found_servers) == 0 or (now - last_full_scan) > SCAN_COOLDOWN:
        all_found_servers = fetch_all_servers()
        last_full_scan = now
        # Cache leeren für frische Ergebnisse
        sent_jobs.clear()
        print("🔄 Neuer Vollscan durchgeführt")
    
    # Server filtern
    result = filter_matching_servers(all_found_servers)
    
    # Falls keine passenden gefunden, Cache leeren und neu suchen
    if len(result) == 0 and len(sent_jobs) > 0:
        sent_jobs.clear()
        result = filter_matching_servers(all_found_servers)
    
    return result

# === ROUTES ===

@app.route('/')
def home():
    return "✅ Brainrot AutoJoiner läuft! /jobid /jobs /status"

@app.route('/jobid')
def get_job_id():
    """Eine einzelne Job-ID (schnell!)"""
    servers = get_servers_smart()
    if servers:
        return servers[0]["obfuscated"]
    return "WAITING"

@app.route('/jobs')
def get_all_jobs():
    """Mehrere Job-IDs auf einmal (bis zu 10)"""
    servers = get_servers_smart()
    if servers:
        job_ids = [s["obfuscated"] for s in servers]
        return jsonify({
            "count": len(job_ids),
            "job_ids": job_ids,
            "details": [{"players": s["players"], "max": s["maxPlayers"]} for s in servers]
        })
    return jsonify({
        "count": 0,
        "job_ids": [],
        "message": "Keine passenden Server gefunden"
    })

@app.route('/status')
def get_status():
    servers = get_servers_smart()
    return jsonify({
        "status": "online",
        "found_servers": len(servers),
        "filter": f"{MIN_PLAYERS}-{MAX_PLAYERS} Spieler",
        "last_scan": last_scan_time,
        "cache_size": len(sent_jobs),
        "total_servers_api": len(all_found_servers)
    })

@app.route('/reset')
def reset_cache():
    """Cache manuell zurücksetzen"""
    global sent_jobs, all_found_servers
    sent_jobs.clear()
    all_found_servers = []
    return "✅ Cache geleert! Nächster Scan bringt frische Server."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
