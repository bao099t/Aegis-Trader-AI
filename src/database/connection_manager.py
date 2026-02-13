import asyncio
from sqlalchemy.orm import Session
from src.database import db_setup

class ConnectionManager:
    """
    Singleton Database Manager with Async Locking.
    Prevents 'Database Locked' errors in concurrent environments.
    """
    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConnectionManager, cls).__new__(cls)
        return cls._instance

    @classmethod
    async def get_db(cls):
        """
        Async context manager for DB session.
        Usage:
            async with ConnectionManager.get_db() as db:
                ...
        """
        async with cls._lock:
            db = db_setup.SessionLocal()
            try:
                yield db
            finally:
                db.close()
