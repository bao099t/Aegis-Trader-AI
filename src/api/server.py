from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
import os
import threading
import time

app = FastAPI(title="Aegis Sentinel API", version="1.0.0")

# Enable CORS for local dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = "data"
HEALTH_FILE = os.path.join(DATA_DIR, "system_health.json")
LOG_FILE = os.path.join(DATA_DIR, "logs", "app.log")
TRADES_FILE = os.path.join(DATA_DIR, "active_trades.json")

@app.get("/")
def read_root():
    return {"status": "online", "system": "Aegis Zenith Hybrid"}

@app.get("/status")
def get_status():
    if os.path.exists(HEALTH_FILE):
        try:
            with open(HEALTH_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            return {"status": "ERROR", "details": str(e)}
    return {"status": "WAITING_FOR_DATA"}

@app.get("/trades")
def get_trades():
    if os.path.exists(TRADES_FILE):
        try:
            with open(TRADES_FILE, "r") as f:
                return json.load(f)
        except:
            return []
    return []

@app.get("/logs")
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
    uvicorn.run(app, host="0.0.0.0", port=8000)
