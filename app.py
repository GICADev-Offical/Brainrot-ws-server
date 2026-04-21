import asyncio
import websockets
import requests
import base64
from datetime import datetime

# === KONFIGURATION ===
PLACE_ID = "109983668079237"  # Steal a Brainrot
MIN_PLAYERS = 3
MAX_PLAYERS = 4
SECRET_KEY = 42
# =====================

connected_clients = set()
current_job_id = None

def obfuscate_job_id(job_id):
    if not job_id:
        return ""
    xored = "".join(chr(ord(c) ^ SECRET_KEY) for c in job_id)
    encoded = base64.b64encode(xored.encode()).decode()
    return encoded

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
                return best.get("id"), best_players
    except:
        pass
    return None, 0

async def handle(ws):
    connected_clients.add(ws)
    if current_job_id:
        await ws.send(obfuscate_job_id(current_job_id))
    try:
        await ws.wait_closed()
    finally:
        connected_clients.remove(ws)

async def update():
    global current_job_id
    while True:
        job_id, players = get_server()
        if job_id and job_id != current_job_id:
            current_job_id = job_id
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Job-ID: {job_id} ({players} Spieler)")
            if connected_clients:
                obf = obfuscate_job_id(job_id)
                await asyncio.gather(*[c.send(obf) for c in connected_clients])
        await asyncio.sleep(15)

async def main():
    async with websockets.serve(handle, "0.0.0.0", 8080):
        print("🌐 WebSocket läuft auf Port 8080")
        await update()

if __name__ == "__main__":
    asyncio.run(main())
