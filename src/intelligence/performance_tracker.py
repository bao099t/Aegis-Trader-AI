import yfinance as yf
from src.database import db_setup, models
import datetime
import time

class PerformanceTracker:
    def __init__(self, db_session):
        self.db = db_session
        self.SLIPPAGE_PER_SIDE = 0.0015 # 0.15% trượt giá mỗi chiều (vào/ra)
        self.COMMISSION = 0.001        # 0.1% phí sàn

    def update_pnl(self):
        """
        Finds alerts that need performance tracking and updates their PnL.
        """
        # Find alerts older than 1 hour (for simulation/testing, normally 24h)
        # and which don't have exit_price_24h yet.
        now = datetime.datetime.utcnow()
        one_hour_ago = now - datetime.timedelta(hours=1)
        
        pending = self.db.query(models.Alert).filter(
            models.Alert.entry_price != None,
            models.Alert.exit_price_24h == None,
            models.Alert.published_at < one_hour_ago
        ).all()
        
        if not pending:
            return 0

        print(f"  [Tracker] Updating PnL for {len(pending)} alerts...")
        count = 0
        for alert in pending:
            try:
                # Use Ticker from DB
                ticker = alert.ticker
                if not ticker: continue
                
                stock = yf.Ticker(ticker)
                
                # Check for Stop-Loss (Phase 21)
                if alert.stop_loss_price:
                    # Fetch history since publication
                    hist = stock.history(start=alert.published_at.strftime('%Y-%m-%d'))
                    if not hist.empty:
                        low_val = hist['Low'].min()
                        high_val = hist['High'].max()
                        
                        is_bullish = alert.reason and "Good news" in alert.reason
                        
                        # If Bullish and Low hit SL
                        if is_bullish and low_val <= alert.stop_loss_price:
                            alert.is_stopped_out = True
                            alert.exit_price_24h = alert.stop_loss_price
                            alert.pnl_percent = -3.0 # Fixed loss for SL hit (matching our 3% SL)
                            count += 1
                            continue
                        
                        # If Bearish and High hit SL
                        if not is_bullish and high_val >= alert.stop_loss_price:
                            alert.is_stopped_out = True
                            alert.exit_price_24h = alert.stop_loss_price
                            alert.pnl_percent = -3.0
                            count += 1
                            continue

                # Normal 24h Exit
                current_price = stock.info.get('currentPrice')
                if not current_price: continue
                
                alert.exit_price_24h = current_price
                
                # Calculate PnL %
                # If Signal was Positive -> (Exit - Entry) / Entry
                # If Signal was Negative -> (Entry - Exit) / Entry
                pnl = ((current_price - alert.entry_price) / alert.entry_price) * 100
                
                # Simple logic: If we predicted BEARISH, we profit if it goes DOWN
                if alert.reason and ("Bad news" in alert.reason or "Negative Catalyst" in alert.reason):
                    pnl = -pnl
                
                # Phase 24: Apply Real-world Haircut (Slippage + Fees)
                # Total cost = 0.15% (entry) + 0.15% (exit) + 0.1% (fee) = 0.4% approx
                total_cost_pct = (self.SLIPPAGE_PER_SIDE * 2 + self.COMMISSION) * 100
                net_pnl = pnl - total_cost_pct
                
                alert.pnl_percent = round(net_pnl, 2)
                count += 1
                
            except Exception as e:
                print(f"  [Tracker] Error updating {alert.id}: {e}")
        
        self.db.commit()
        return count

    def _extract_ticker(self, alert):
        # We know we extract tickers in MarketAnalyst, but we didn't save it to the DB yet.
        # Let's use a simple regex or check the title.
        # Heuristic: First word of the title is often the ticker if it's all caps.
        words = alert.title.split()
        if words[0].isupper() and len(words[0]) <= 5:
            return words[0]
        return None

    def get_stats(self):
        """Returns overall performance stats."""
        total_tracked = self.db.query(models.Alert).filter(models.Alert.pnl_percent != None).count()
        if total_tracked == 0:
            return {"win_rate": 0, "avg_pnl": 0, "total": 0}
            
        wins = self.db.query(models.Alert).filter(models.Alert.pnl_percent > 0).count()
        avg_pnl_data = self.db.query(models.Alert).filter(models.Alert.pnl_percent != None).order_by(models.Alert.published_at.asc()).all()
        pnls = [a.pnl_percent for a in avg_pnl_data]
        
        avg_pnl_val = sum(pnls) / len(pnls)
        
        # Calculate Max Drawdown (Phase 24)
        # We simulate an equity curve starting at 100
        equity = 100
        curve = [100]
        for p in pnls:
            equity *= (1 + p/100)
            curve.append(equity)
        
        peak = 0
        max_dd = 0
        for val in curve:
            if val > peak:
                peak = val
            dd = (peak - val) / peak * 100 if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd

        return {
            "win_rate": round((wins / total_tracked) * 100, 2),
            "avg_pnl": round(avg_pnl_val, 2),
            "total_tracked": total_tracked,
            "max_drawdown": round(max_dd, 2)
        }

    def get_drawdown_state(self):
        """
        Returns full drawdown metrics for Guardian Circuit Breakers.
        """
        avg_pnl_data = self.db.query(models.Alert).filter(models.Alert.pnl_percent != None).order_by(models.Alert.published_at.asc()).all()
        pnls = [a.pnl_percent for a in avg_pnl_data]
        
        if not pnls:
            return {"max_drawdown": 0, "current_drawdown": 0}

        equity = 100
        peak = 100
        current_dd = 0
        max_dd = 0
        
        for p in pnls:
            equity *= (1 + p/100)
            if equity > peak:
                peak = equity
            
            dd = (peak - equity) / peak * 100 if peak > 0 else 0
            if dd > max_dd: max_dd = dd
            current_dd = dd # The last calculated DD is the current one
            
        return {
            "max_drawdown": round(max_dd, 2),
            "current_drawdown": round(current_dd, 2)
        }

    def get_recent_performance(self, n=5):
        """
        Returns last N closed trades for Streak Analysis.
        """
        recent = self.db.query(models.Alert)\
            .filter(models.Alert.pnl_percent != None)\
            .order_by(models.Alert.published_at.desc())\
            .limit(n)\
            .all()
        
        return [a.pnl_percent for a in recent]

if __name__ == "__main__":
    db = db_setup.SessionLocal()
    tracker = PerformanceTracker(db)
    print(tracker.get_stats())
    db.close()
