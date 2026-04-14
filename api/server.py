# ~/benchmaster/api/server.py

import os
import socket
import threading
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from api.routes import machines, jobs, results, thresholds
from api.mqtt_manager import mqtt_manager

app = FastAPI(title="BenchMaster API", version="1.0.0")

# Enable CORS for Dashboard access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- UDP Discovery Service ---
DISCOVERY_PORT = 55555
DISCOVERY_MSG_REQ = b"BENCHMASTER_DISCOVER_REQ"
DISCOVERY_MSG_RES_PREFIX = b"BENCHMASTER_DISCOVER_RES:"

def start_udp_discovery_service():
    def listen():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind(('', DISCOVERY_PORT))
        print(f"[*] UDP Discovery Service started on port {DISCOVERY_PORT}")
        while True:
            try:
                data, addr = s.recvfrom(1024)
                if data == DISCOVERY_MSG_REQ:
                    server_ip = addr[0]
                    response = DISCOVERY_MSG_RES_PREFIX + server_ip.encode()
                    s.sendto(response, addr)
                    print(f"[*] Responded to discovery request from {addr[0]}")
            except Exception as e:
                print(f"[!] UDP Discovery Error: {e}")

    thread = threading.Thread(target=listen, daemon=True)
    thread.start()

# Start the discovery service
start_udp_discovery_service()

# --- MQTT Lifecycle ---
@app.on_event("startup")
async def startup_event():
    mqtt_manager.start()

@app.on_event("shutdown")
async def shutdown_event():
    mqtt_manager.stop()

# --- Include Routers ---
app.include_router(machines.router, prefix="/machines", tags=["Machines"])
app.include_router(jobs.router, prefix="/jobs", tags=["Jobs"])
app.include_router(results.router, prefix="/results", tags=["Results"])
app.include_router(thresholds.router, prefix="/thresholds", tags=["Thresholds"])

# --- Dashboard Static Files ---
@app.get("/")
async def serve_dashboard():
    return FileResponse(os.path.join(os.path.dirname(__file__), '../dashboard/index.html'))

@app.get("/api/health")
async def health_check():
    return {"status": "online", "version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
