from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
import os
import threading
import time

# Phase 60: API Security Hardening
API_KEY_NAME = "X-AEGIS-KEY"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

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
    allow_origins=["*"], # Keep open for local dashboard file
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = "data"
HEALTH_FILE = os.path.join(DATA_DIR, "system_health.json")
LOG_FILE = os.path.join(DATA_DIR, "logs", "app.log")
TRADES_FILE = os.path.join(DATA_DIR, "active_trades.json")

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
                content = f.readlines()
                return content[-lines:]
        except:
            return ["Log file not readable"]
    return ["Log file not found"]

if __name__ == "__main__":
    # Bind to localhost (127.0.0.1) for security.
    # To allow external access, use a reserve proxy (Nginx) or change host to 0.0.0.0 IF you add Auth.
    uvicorn.run(app, host="127.0.0.1", port=8000)
