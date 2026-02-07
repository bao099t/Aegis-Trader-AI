import yfinance as yf
from .entity_extractor import EntityExtractor
from .technical_analyst import TechnicalAnalyst
from .macro_analyst import MacroAnalyst
from .institutional_analyst import InstitutionalAnalyst
from .psych_analyst import PsychAnalyst
from src.core.guardian import Guardian
import time
import datetime

class MarketAnalyst:
    def __init__(self):
        self.extractor = EntityExtractor()
        self.tech = TechnicalAnalyst()
        self.macro = MacroAnalyst()
        self.inst = InstitutionalAnalyst()
        self.psych = PsychAnalyst()
        self.guardian = Guardian()
        # Simple cache: {ticker: {data: {}, timestamp: 0}}
        self.cache = {} 
        self.CACHE_DURATION = 3600 * 24 # 24 hours
        from src.database import db_setup, models # Deferred import to avoid circular dependency
        self.db_setup = db_setup
        self.models = models

    def _check_sector_concentration(self, sector):
        """Counts active alerts in the same sector from the last 24 hours."""
        db = self.db_setup.SessionLocal()
        try:
            now = datetime.datetime.utcnow()
            day_ago = now - datetime.timedelta(hours=24)
            count = db.query(self.models.Alert).filter(
                self.models.Alert.published_at > day_ago,
                self.models.Alert.summary.like(f"%Sector: {sector}%") | # Heuristic if we didn't store sector explicitly
                self.models.Alert.reason.like(f"%{sector}%")
            ).count()
            return count
        except:
            return 0
        finally:
            db.close()

    def get_fundamentals(self, ticker):
        """
        Fetches key stats from yfinance with caching.
        """
        now = time.time()
        if ticker in self.cache:
            if now - self.cache[ticker]['timestamp'] < self.CACHE_DURATION:
                return self.cache[ticker]['data']
        
        try:
            print(f"  [Analyst] Fetching fundamentals for {ticker}...")
            stock = yf.Ticker(ticker)
            info = stock.info
            
            data = {
                "sector": info.get("sector", "Unknown"),
                "industry": info.get("industry", "Unknown"),
                "pe_ratio": info.get("forwardPE", info.get("trailingPE", "N/A")),
                "market_cap": info.get("marketCap", 0),
                "52w_high": info.get("fiftyTwoWeekHigh", 0),
                "52w_low": info.get("fiftyTwoWeekLow", 0),
                "current_price": info.get("currentPrice", 0),
                "short_ratio": info.get("shortRatio", 0)
            }
            
            # Format Market Cap
            mc = data['market_cap']
            if mc > 1_000_000_000_000:
                data['market_cap_fmt'] = f"${mc/1_000_000_000_000:.2f}T"
            elif mc > 1_000_000_000:
                data['market_cap_fmt'] = f"${mc/1_000_000_000:.2f}B"
            else:
                data['market_cap_fmt'] = f"${mc/1_000_000:.2f}M"
                
            self.cache[ticker] = {'data': data, 'timestamp': now}
            return data
        except Exception as e:
            print(f"  [Analyst] Error fetching fundamentals: {e}")
            return None

    def get_atr(self, ticker):
        """Calculates Average True Range (ATR) for dynamic stops."""
        try:
            stock = yf.Ticker(ticker)
            # Fetch last 30 days to calculate a clean 14-day ATR
            hist = stock.history(period="1mo")
            if len(hist) < 15: return None
            
            high_low = hist['High'] - hist['Low']
            high_cp = (hist['High'] - hist['Close'].shift()).abs()
            low_cp = (hist['Low'] - hist['Close'].shift()).abs()
            
            tr = high_low.combine(high_cp, max).combine(low_cp, max)
            atr = tr.rolling(window=14).mean().iloc[-1]
            return atr
        except:
            return None

    def analyze(self, news_title, news_summary="", sentiment_score=0.0):
        full_text = f"{news_title} {news_summary}"
        ticker = self.extractor.extract(full_text)
        
        result = {
            "has_analysis": False,
            "ticker": ticker,
            "direction": "NEUTRAL",
            "signal": None,
            "context": None,
            "reason": ""
        }
        
        if not ticker:
            return result
            
        # 1. Get Context (Fundamentals)
        fund = self.get_fundamentals(ticker)
        result['context'] = fund
        result['has_analysis'] = True
        
        # 2. Get Technicals
        tech = self.tech.analyze(ticker)
        result['technical'] = tech
        
        # 3. Get Macro Context
        macro = self.macro.analyze()
        result['macro'] = macro
        
        # 4. Get Institutional Analysis
        inst = self.inst.analyze(ticker)
        result['institutional'] = inst
        
        # 5. NLP Analysis Integration (Phase 4 Upgrade)
        u_text = full_text.lower()
        
        # KEYWORD OVERRIDES (Strongest Signals)
        # BULLISH SIGNALS
        if any(x in u_text for x in ["earnings beat", "revenue grow", "record quarter", "upgrade", "buy rating", "partnership", "wins contract", "fda approval"]):
            result['direction'] = "BULLISH"
            result['signal'] = "Positive Catalyst"
            
        # BEARISH SIGNALS
        elif any(x in u_text for x in ["misses estimates", "lowers guidance", "lawsuit", "investigation", "subpoena", "recall", "downgrade", "sell rating", "hack", "breach"]):
            result['direction'] = "BEARISH"
            result['signal'] = "Negative Catalyst"
            
        # ACQUISITION LOGIC
        elif "acquire" in u_text or "buy" in u_text:
             result['direction'] = "VOLATILE"
             result['signal'] = "M&A Activity"

        # NLP SENTIMENT FALLBACK (If no keywords matched)
        elif abs(sentiment_score) > 0.2: # Threshold for AI confidence
            if sentiment_score > 0.2:
                result['direction'] = "BULLISH"
                result['signal'] = f"AI Sentiment (Score: {sentiment_score:.2f})"
                result['reason'] = f"AI News Analysis detects positive tone ({sentiment_score:.2f}). "
            else:
                result['direction'] = "BEARISH"
                result['signal'] = f"AI Sentiment (Score: {sentiment_score:.2f})"
                result['reason'] = f"AI News Analysis detects negative tone ({sentiment_score:.2f}). "
                
        # 3. Generate Reason (Keyword based)
        if result['signal'] == "Positive Catalyst":
            result['reason'] = "Strong keyword catalyst detected. "
        elif result['signal'] == "Negative Catalyst":
            result['reason'] = "Negative keyword catalyst detected. "
            
        # 6. Psychology & Behavioral (Pass technical data too)
        psych = self.psych.analyze(ticker, sentiment_score, tech)
        result['psychology'] = psych

        # Contextual Insight & Convergence
        # Fundamentals
        if fund:
             pe = fund['pe_ratio']
             if pe != "N/A" and isinstance(pe, (int, float)):
                 if pe > 50 and result['direction'] == "BEARISH":
                     result['reason'] += "Stock is expensive (High P/E), risk of sharp correction. "
                 elif pe < 15 and result['direction'] == "BULLISH":
                     result['reason'] += "Stock is cheap (Low P/E), potential value play. "
        
        # Technicals
        if tech:
             # Warning: Good News + Overbought
             if result['direction'] == "BULLISH" and tech['rsi_state'] == "OVERBOUGHT":
                 result['reason'] += "⚠️ CAUTION: Stock is Overbought (RSI > 70). Sell pressure likely despite news. "
                 
             # Warning: Bad News + Oversold
             if result['direction'] == "BEARISH" and tech['rsi_state'] == "OVERSOLD":
                   result['reason'] += "⚠️ NOTE: Stock is Oversold (RSI < 30). Price may bounce. "
                   
             # Confirmation: Good News + Uptrend
             if result['direction'] == "BULLISH" and tech['trend'] == "UPTREND":
                 result['reason'] += "🚀 CONVERGENCE: News aligns with Uptrend. Strong Signal. "

             # Regime Awareness (Phase 26)
             if tech['regime'] == "CHOPPY / SIDEWAY":
                 result['reason'] += "🌪️ MARKET REGIME: Choppy/Sideway conditions detected. Higher probability of failed breakouts. "

        # Macro (Risk Management)
        if macro and macro['risk_status'] == "RISK-OFF":
             # Downgrade Bullish signals in Bear Market/High Volatility
             if result['direction'] == "BULLISH":
                 result['reason'] += "🌪️ WARNING: Market is Risk-Off (High VIX/Bear). Success rate lower. "
                 
        # Institutional Validation (Brutal Audit)
        if inst:
            # Volume Check
            if inst['volume']['score'] == "LOW":
                result['reason'] += "⚠️ TRAP: Low volume move. Smart money not participating. "
            
            # Sector Check
            if result['direction'] == "BULLISH" and inst['sector']['status'] == "BEARISH":
                result['reason'] += "🛑 SECTOR LAG: Stock trying to rally while sector is sinking. Avoid. "
                
            # RS Check
            if result['direction'] == "BULLISH" and inst['relative_strength']['score'] == "LAGGARD":
                result['reason'] += "🐢 WEAK ALPHA: Stock is underperforming SPY. Better opportunities elsewhere. "
                
        # Psychological Validation (Contrarian Audit)
        if psych:
            if psych['saturation']['is_saturated']:
                result['reason'] += f"🛑 {psych['saturation']['msg']} "
            
            if "BEARISH DIVERGENCE" in psych['divergence']['msg'] and result['direction'] == "BULLISH":
                result['reason'] += "🧨 DIVERGENCE TRAP: Positive sentiment but price action is bearish. Smart money selling. "
            
            if "LARGE GAP" in psych['gap_risk']['msg']:
                 result['reason'] += "🌋 GAP OVEREXTENDED: Prices jumped too far. Wait for gap fill. "

        # --- SIGNAL SYNTHESIS (Phase 18/19/21) ---
        score, verdict, size, sl = self.calculate_synthesis(result)
        result['synthesis'] = {
            "score": score,
            "verdict": verdict,
            "suggested_size": f"{size:.1f}%",
            "stop_loss": sl
        }

        # --- SECTOR CORRELATION GUARD (Phase 22: Addressing Brutal Audit #6) ---
        if fund:
            sector = fund.get('sector')
            if sector:
                concentration = self._check_sector_concentration(sector)
                if concentration >= 3:
                    result['reason'] += f"📉 CONCENTRATION RISK: You already have {concentration} active signals in the {sector} sector. Diversify! "
                    result['synthesis']['score'] -= 10
                    result['synthesis']['verdict'] = "⚠️ SECTOR CLUSTER: High correlation risk."

        # --- CROSS-VALIDATION (Phase 21: Addressing Brutal Audit #2) ---
        # Detect Deception: News is Bullish but Trend is clearly Bearish
        result['is_verified'] = True
        if result['direction'] == "BULLISH" and tech and tech['trend'] == "DOWNTREND":
             # Price action is fighting the news - high probability of a Trap
             result['is_verified'] = False
             result['reason'] += "🧨 DECEPTION ALERT: Sentiment is Bullish but Price Trend is Bearish. Likely a Bull Trap. "
             # Note: Score adjustment is now handled via Weighted Synthesis logic

        return result

    def calculate_synthesis(self, analysis):
        """
        Synthesizes all layers into a final score (0-100) using Weighted Logic (Phase 27).
        """
        # Weights for different layers
        WEIGHTS = {
            "SENTIMENT": 0.40,   # Core catalyst drive
            "TECHNICALS": 0.25,  # Trend & Price action confirmation
            "MACRO": 0.15,       # Market background
            "INST_PSYCH": 0.20   # Smart money & Crowd behavior
        }
        
        # 1. Base Sentiment Score (0-100 equivalent)
        sent_component = 50
        if analysis['direction'] == "BULLISH": sent_component = 85
        elif analysis['direction'] == "BEARISH": sent_component = 15
        
        # 2. Technical Component
        tech_component = 50
        tech = analysis.get('technical')
        if tech:
            if analysis['direction'] == "BULLISH" and tech['trend'] == "UPTREND": tech_component += 20
            if analysis['direction'] == "BEARISH" and tech['trend'] == "DOWNTREND": tech_component -= 20
            # Regime adjustment in Tech
            if tech.get('regime') == "CHOPPY / SIDEWAY": tech_component = 40 # Neutralize bias in noise
        
        # 3. Macro Component
        macro_component = 50
        macro = analysis.get('macro')
        if macro:
            if macro['risk_status'] == "RISK-ON": macro_component = 70
            else: macro_component = 30
            
        # 4. Institutional & Psych Component
        ip_component = 50
        inst = analysis.get('institutional')
        psych = analysis.get('psychology')
        if inst:
            if inst['volume']['score'] == "HIGH": ip_component += 10
            if inst['relative_strength']['score'] == "LEADER": ip_component += 10
        if psych and "DIVERGENCE" in psych['divergence']['msg']:
            ip_component -= 20 # Sharp penalty for divergence
            
        # CALCULATE WEIGHTED SCORE
        score = (
            (sent_component * WEIGHTS["SENTIMENT"]) +
            (tech_component * WEIGHTS["TECHNICALS"]) +
            (macro_component * WEIGHTS["MACRO"]) +
            (ip_component * WEIGHTS["INST_PSYCH"])
        )
        
        score = max(0, min(100, score)) # Clamp
        
        # Final Verdict Sentence
        verdict = "Neutral market observation."
        if score > 85: verdict = "🏆 ELITE SETUP: All layers align. High conviction move."
        elif score > 70: verdict = "🚀 POSITIVE: Strong momentum but check technical levels."
        elif score > 55: verdict = "📈 MILD BULLISH: Low conviction or minor catalyst."
        elif score < 15: verdict = "💀 CRITICAL TRAP: Sentiment is fake. Institutional/Psych indicators are bearish."
        elif score < 30: verdict = "📉 BEARISH: Heavy sell pressure or negative fundamental shift."
        elif score < 45: verdict = "⚠️ CAUTION: Negative lean. Market conditions are unfavorable."

        # Position Sizing Logic (Phase 32: Competitive Calibration)
        # Strategy: Request 30% allocation and let Guardian Hard-Cap it at 15%.
        # This maximizes 'Alpha' on high confidence trades while retaining the safety net.
        suggested_size = (score / 100) * 30.0 
        
        # Regime Discount (Phase 26)
        if tech and tech.get('regime') == "CHOPPY / SIDEWAY":
            suggested_size *= 0.5 # Cut size in half for safety
        
        # GUARDIAN CHECK (Phase 28)
        # Final veto power over the trade
        is_safe, refusal_reason, safe_size = self.guardian.check_safety(analysis.get('ticker'), analysis['direction'], suggested_size)
        
        # Phase 29: Phoenix Protocol Support
        # If Probation, we treat it as SAFE but mark it as VIRTUAL only.
        is_virtual = False
        if not is_safe and "PROBATION" in refusal_reason:
            is_virtual = True
            is_safe = True # We let it pass, but downstream (main.py) will treat it as virtual
            # We keep the size as is (or capped) for simulation
            result['synthesis']['status'] = "PROBATION (VIRTUAL)"
        elif not is_safe:
            # Real Block
            score = 0
            verdict = refusal_reason
            suggested_size = 0
            result['synthesis']['status'] = "BLOCKED"
        else:
            # Safe and Live
            suggested_size = safe_size
            result['synthesis']['status'] = "LIVE"
            
        result['is_virtual'] = is_virtual # Pass this flag to main.py

        
        # Stop-Loss Logic (Phase 21/23: Dynamic ATR Stops)
        sl_price = None
        fund = analysis.get('context')
        if fund and fund['current_price']:
            entry = fund['current_price']
            ticker = analysis.get('ticker')
            
            # Phase 23: ATR based stop-loss
            atr = self.get_atr(ticker) if ticker else None
            
            if atr:
                # Use 2x ATR as a professional standard for stops
                if analysis['direction'] == "BULLISH":
                    sl_price = entry - (2 * atr)
                elif analysis['direction'] == "BEARISH":
                    sl_price = entry + (2 * atr)
                
                # Safeguard: Never more than 10% loss
                max_stop = entry * 0.90 if analysis['direction'] == "BULLISH" else entry * 1.10
                if analysis['direction'] == "BULLISH" and sl_price is not None:
                    sl_price = max(sl_price, max_stop)
                elif analysis['direction'] == "BEARISH" and sl_price is not None:
                    sl_price = min(sl_price, max_stop)
            else:
                # Fallback to static 3% if ATR fails
                if analysis['direction'] == "BULLISH":
                    sl_price = entry * 0.97
                elif analysis['direction'] == "BEARISH":
                    sl_price = entry * 1.03
                
        return score, verdict, suggested_size, sl_price

if __name__ == "__main__":
    ma = MarketAnalyst()
    print(ma.analyze("Tesla recalls 2 million cars"))
    print(ma.analyze("Apple reports record earnings beat"))
