from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
import os
import threading
import time
from collections import deque

import time
from fastapi import Request, Response, Body
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel

class ControlCommand(BaseModel):
    action: str # PANIC_SELL, PAUSE, RESUME, SHUTDOWN
    secret: str # Extra layer of safety (optional)

# Phase 60: API Security Hardening
API_KEY_NAME = "X-AEGIS-KEY"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

class RateLimiter(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 60, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.clients = {} # IP -> [timestamps]

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        now = time.time()
        
        # Clean old requests
        if client_ip not in self.clients:
            self.clients[client_ip] = []
        self.clients[client_ip] = [t for t in self.clients[client_ip] if now - t < self.window_seconds]
        
        # Check limit
        if len(self.clients[client_ip]) >= self.max_requests:
            return Response("Rate limit exceeded", status_code=429)
            
        self.clients[client_ip].append(now)
        response = await call_next(request)
        return response

def get_api_key(api_key_header: str = Security(api_key_header)):
    # In production, fetch this from .env or Secrets Manager
    # Default fallback for local dev if not set: "aegis_local_dev"
    correct_key = os.getenv("AEGIS_API_KEY", "aegis_local_dev")
    
    if api_key_header == correct_key:
        return api_key_header
    else:
        raise HTTPException(
            status_code=403,
            detail="Could not validate credentials"
        )

app = FastAPI(title="Aegis Sentinel API", version="1.1.0 (Secured)")

# Create a dependency list that covers all routes if needed, 
# or just decorate specific routes. 
# For Sentinel, we likely want to secure sensitive endpoints but maybe keep / status open?
# User asked to "fix it", implying secure everything.

# Enable CORS for local dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"], # Restricted to local dashboard
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Rate Limiter (60 req/min/IP)
app.add_middleware(RateLimiter, max_requests=60, window_seconds=60)

DATA_DIR = "data"
HEALTH_FILE = os.path.join(DATA_DIR, "system_health.json")
LOG_FILE = os.path.join(DATA_DIR, "logs", "app.log")
LOG_FILE = os.path.join(DATA_DIR, "logs", "app.log")
TRADES_FILE = os.path.join(DATA_DIR, "active_trades.json")
CONTROL_FILE = os.path.join(DATA_DIR, "control_signal.json")

# --- CONTROL ENDPOINTS (Phase 8) ---
@app.post("/control", dependencies=[Depends(get_api_key)])
def send_command(cmd: ControlCommand):
    """
    Sends a high-priority signal to the Trading Bot via IPC (File).
    """
    valid_actions = ["PANIC_SELL", "PAUSE", "RESUME", "SHUTDOWN"]
    if cmd.action not in valid_actions:
        raise HTTPException(status_code=400, detail="Invalid Action")
        
    # Write Signal to File
    signal = {
        "action": cmd.action,
        "timestamp": time.time(),
        "source": "API_DASHBOARD"
    }
    
    with open(CONTROL_FILE, "w") as f:
        json.dump(signal, f)
        
    return {"status": "SIGNAL_SENT", "action": cmd.action}


@app.get("/", dependencies=[Depends(get_api_key)])
def read_root():
    return {"status": "online", "system": "Aegis Zenith Hybrid", "security": "Active"}

@app.get("/status", dependencies=[Depends(get_api_key)])
def get_status():
    if os.path.exists(HEALTH_FILE):
        try:
            with open(HEALTH_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            return {"status": "ERROR", "details": str(e)}
    return {"status": "WAITING_FOR_DATA"}

@app.get("/trades", dependencies=[Depends(get_api_key)])
def get_trades():
    if os.path.exists(TRADES_FILE):
        try:
            with open(TRADES_FILE, "r") as f:
                return json.load(f)
        except:
            return []
    return []

@app.get("/logs", dependencies=[Depends(get_api_key)])
def get_logs(lines: int = 50):
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r", encoding='utf-8') as f:
                # Efficiently read only the last N lines using deque
                return list(deque(f, maxlen=lines))
        except Exception as e:
            return [f"Log file error: {str(e)}"]
    return ["Log file not found"]

if __name__ == "__main__":
    # Bind to localhost (127.0.0.1) for security.
    # To allow external access, use a reserve proxy (Nginx) or change host to 0.0.0.0 IF you add Auth.
    uvicorn.run(app, host="127.0.0.1", port=8000)
