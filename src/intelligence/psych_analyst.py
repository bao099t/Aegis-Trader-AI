import yfinance as yf
import pandas as pd
import time

class PsychAnalyst:
    def __init__(self):
        self.cache = {}
        self.CACHE_DURATION = 1800 # 30 mins

    def analyze(self, ticker, sentiment_score, technical_data):
        now = time.time()
        
        # 1. Gap Analysis
        gap_percent = 0
        gap_msg = "Price is stable relative to open."
        try:
            stock = yf.Ticker(ticker)
            # Get today's and yesterday's data
            hist = stock.history(period="2d")
            if len(hist) >= 2:
                prev_close = hist['Close'].iloc[-2]
                curr_price = hist['Close'].iloc[-1]
                gap_percent = ((curr_price / prev_close) - 1) * 100
                
                if abs(gap_percent) > 3.0:
                    gap_msg = f"⚠️ LARGE GAP: {gap_percent:+.1f}%. High risk of 'Gap Fill' (reversal)."
                elif abs(gap_percent) > 1.5:
                    gap_msg = f"Moderate Gap: {gap_percent:+.1f}%."
        except Exception as e:
            print(f"  [Psych] Gap Error: {e}")

        # 2. Saturation (Crowded Trade Detection)
        # Logic: High Sentiment + High RSI = Extreme Greed / Saturated
        is_saturated = False
        sat_msg = "Market participation is healthy."
        
        if technical_data:
            rsi = technical_data.get('rsi', 50)
            if sentiment_score > 0.7 and rsi > 75:
                is_saturated = True
                sat_msg = "🚨 OVERCROWDED: Sentiment & Tech are reaching peak euphoria. Trend exhaustion likely."
            elif sentiment_score < -0.7 and rsi < 25:
                is_saturated = True
                sat_msg = "🩸 PANIC BOTTOM: Sentiment & Tech are at peak fear. Potential contrarian long."

        # 3. Sentiment Divergence
        # Logic: Strong news but price doesn't reflect it
        div_msg = "Price confirms Sentiment."
        # Simple placeholder for intraday check: if gap is negative but sentiment is positive
        if sentiment_score > 0.5 and gap_percent < -0.5:
            div_msg = "❌ BEARISH DIVERGENCE: News is positive but price is falling. Sellers are absorbing the news."
        elif sentiment_score < -0.5 and gap_percent > 0.5:
            div_msg = "✅ BULLISH DIVERGENCE: News is bad but price is resilient. Potential accumulation."

        return {
            "gap_risk": {"percent": gap_percent, "msg": gap_msg},
            "saturation": {"is_saturated": is_saturated, "msg": sat_msg},
            "divergence": {"msg": div_msg},
            "ticker": ticker
        }

if __name__ == "__main__":
    pa = PsychAnalyst()
    # Dummy test
    print(pa.analyze("AAPL", 0.9, {"rsi": 80}))
