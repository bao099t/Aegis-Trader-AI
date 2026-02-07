import re
import yfinance as yf
import time

class EntityExtractor:
    def __init__(self):
        # MVP: Top 50 most popular US stocks + Crypto
        self.TICKER_MAP = {
            "APPLE": "AAPL", "IPHONE": "AAPL", "MACBOOK": "AAPL",
            "MICROSOFT": "MSFT", "WINDOWS": "MSFT", "AZURE": "MSFT",
            "GOOGLE": "GOOGL", "ALPHABET": "GOOGL", "YOUTUBE": "GOOGL",
            "AMAZON": "AMZN", "AWS": "AMZN",
            "TESLA": "TSLA", "ELON MUSK": "TSLA",
            "META": "META", "FACEBOOK": "META", "INSTAGRAM": "META",
            "NVIDIA": "NVDA", "GPU": "NVDA",
            "NETFLIX": "NFLX",
            "AMD": "AMD",
            "INTEL": "INTC",
            "BOEING": "BA",
            "DISNEY": "DIS",
            "COINBASE": "COIN",
            "BITCOIN": "BTC-USD", "BTC": "BTC-USD",
            "ETHEREUM": "ETH-USD", "ETH": "ETH-USD",
            "GOLDMAN SACHS": "GS",
            "JPMORGAN": "JPM",
            "WALMART": "WMT",
            "TARGET": "TGT",
            "COSTCO": "COST",
            "PEP": "PEP",
            "COKE": "KO", "COCA-COLA": "KO",
            "PFIZER": "PFE",
            "MODERNA": "MRNA",
            "PALANTIR": "PLTR",
            "GAMESTOP": "GME",
            "AMC": "AMC",
            "ROBINHOOD": "HOOD",
            "UBER": "UBER", 
            "LYFT": "LYFT",
            "AIRBNB": "ABNB",
            "ORACLE": "ORCL",
            "SALESFORCE": "CRM",
            "ADOBE": "ADBE"
        }
        self.validation_cache = {} # ticker: (is_valid, timestamp)
        
    def extract(self, text):
        """
        Returns a Ticker symbol (e.g. 'AAPL') if found, otherwise None.
        """
        upper_text = text.upper()
        ticker_to_verify = None
        
        # 1. Look for explicit tickers like (AAPL) or $AAPL
        # Regex: \b[A-Z]{2,5}\b inside parens or after $
        explicit = re.search(r'\(\s*([A-Z]{2,5})\s*\)|\$([A-Z]{2,5})', upper_text)
        if explicit:
            ticker_to_verify = explicit.group(1) or explicit.group(2)
        else:
            for key, ticker in self.TICKER_MAP.items():
                # Check for whole word match
                pattern = r'\b' + re.escape(key) + r'\b'
                if re.search(pattern, upper_text):
                    ticker_to_verify = ticker
                    break
        
        if not ticker_to_verify:
            return None
            
        # 3. VERIFICATION LAYER (Phase 27)
        return ticker_to_verify if self._is_valid_ticker(ticker_to_verify) else None

    def _is_valid_ticker(self, ticker):
        """Verifies ticker exists in real market data to prevent logic holes."""
        now = time.time()
        if ticker in self.validation_cache:
            is_valid, ts = self.validation_cache[ticker]
            if now - ts < 86400: # 24h cache
                return is_valid
        
        try:
            # Quick check: Fetch currentPrice
            stock = yf.Ticker(ticker)
            # Use fast_info if available or simple check
            if stock.info.get('regularMarketPrice') or stock.info.get('currentPrice'):
                self.validation_cache[ticker] = (True, now)
                return True
        except:
            pass
            
        self.validation_cache[ticker] = (False, now)
        return False

if __name__ == "__main__":
    ee = EntityExtractor()
    print(ee.extract("Apple releases new phone")) # AAPL
    print(ee.extract("Tesla recalls cars")) # TSLA
    print(ee.extract("Market ignores inflation")) # None
