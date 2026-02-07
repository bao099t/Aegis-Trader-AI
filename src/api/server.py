from fastapi import FastAPI, Depends, Body
from src.intelligence.performance_tracker import PerformanceTracker
from src.infrastructure.monitor import InfrastructureMonitor
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from src.database import models, db_setup
import datetime
import os

# Create Tables
models.Base.metadata.create_all(bind=db_setup.engine)

app = FastAPI(title="Stock Alert API")

# Mount Static
app.mount("/static", StaticFiles(directory="src/static"), name="static")

@app.get("/")
def read_root():
    return FileResponse('src/static/index.html')

@app.get("/alerts")
def get_alerts(limit: int = 50, db: Session = Depends(db_setup.get_db)):
    alerts = db.query(models.Alert).order_by(models.Alert.published_at.desc()).limit(limit).all()
    return alerts

@app.get("/stats")
def get_stats(db: Session = Depends(db_setup.get_db)):
    total = db.query(models.Alert).count()
    sent = db.query(models.Alert).filter(models.Alert.is_sent == True).count()
    
    tracker = PerformanceTracker(db)
    perf = tracker.get_stats()
    
    return {
        "total_alerts": total, 
        "alerts_sent": sent,
        "win_rate": perf.get('win_rate', 0),
        "avg_pnl": perf.get('avg_pnl', 0),
        "total_tracked": perf.get('total_tracked', 0)
    }

@app.get("/watchlist")
def get_watchlist():
    if not os.path.exists("watchlist.txt"):
        return []
    with open("watchlist.txt", "r") as f:
        return [line.strip() for line in f.readlines() if line.strip()]

@app.post("/watchlist")
def add_to_watchlist(ticker: str = Body(..., embed=True)):
    ticker = ticker.upper().strip()
    if not ticker: return {"status": "error"}
    
    current = get_watchlist()
    if ticker not in current:
        with open("watchlist.txt", "a") as f:
            f.write(f"\n{ticker}")
    return {"status": "success", "watchlist": get_watchlist()}

@app.get("/macro")
def get_macro_status():
    # Simple heartbeat/macro check
    from src.intelligence.macro_analyst import MacroAnalyst
    ma = MacroAnalyst()
    return ma.analyze()

@app.get("/health")
def get_system_health():
    mon = InfrastructureMonitor()
    return mon.get_status()

@app.get("/orders")
def get_orders():
    from src.delivery.broker_api import BrokerAPI
    broker = BrokerAPI()
    return broker.get_active_orders()

@app.post("/kill-switch")
def trigger_kill_switch(status: bool = Body(..., embed=True)):
    lock_file = "data/kill_switch.lock"
    if status:
        with open(lock_file, "w") as f:
            f.write("STOP")
        return {"status": "ARMED", "msg": "SYSTEM DISARMED - ALL TRADING STOPPED"}
    else:
        if os.path.exists(lock_file):
            os.remove(lock_file)
        return {"status": "DISARMED", "msg": "SYSTEM RE-ARMED - READY FOR EXECUTION"}

@app.get("/kill-switch")
def get_kill_status():
    return {"is_killed": os.path.exists("data/kill_switch.lock")}
