from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean
from .db_setup import Base
import datetime

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, index=True)
    title = Column(String, index=True)
    link = Column(String, unique=True, index=True)
    published_at = Column(DateTime, default=datetime.datetime.utcnow)
    summary = Column(Text, nullable=True)
    
    # Analysis
    sentiment_score = Column(Float)
    ticker = Column(String, index=True, nullable=True)
    keyword = Column(String, nullable=True)
    reason = Column(String, nullable=True)
    
    # Meta
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    is_sent = Column(Boolean, default=False)
    
    # Performance Tracking (Phase 19)
    signal_score = Column(Float, nullable=True)
    entry_price = Column(Float, nullable=True)
    exit_price_24h = Column(Float, nullable=True)
    pnl_percent = Column(Float, nullable=True)
    
    # Risk Management (Phase 21)
    stop_loss_price = Column(Float, nullable=True)
    is_stopped_out = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=True) # Flag for 'Sentiment vs Reality' check
    
    # Phoenix Protocol (Phase 29)
    is_virtual = Column(Boolean, default=False) # If True, ignored by PnL but used for Resurrection
