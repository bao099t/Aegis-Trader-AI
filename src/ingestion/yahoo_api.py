import yfinance as yf
import datetime

class YahooAPI:
    def __init__(self):
        # Broad market tickers to watch for general news
        self.tickers = ["^GSPC", "^DJI", "^IXIC", "AAPL", "MSFT", "NVDA", "TSLA", "GOOGL"]
        
    def fetch(self):
        results = []
        seen_titles = set()
        
        print(f"  [YahooAPI] Fetching news for {len(self.tickers)} tickers...")
        
        for symbol in self.tickers:
            try:
                ticker = yf.Ticker(symbol)
                news = ticker.news
                
                for item in news:
                    title = item.get('title')
                    if title in seen_titles:
                        continue
                    seen_titles.add(title)
                    
                    # Normalize
                    normalized = {
                        "source": f"Yahoo API ({symbol})",
                        "title": title,
                        "link": item.get('link'),
                        "published": str(datetime.datetime.fromtimestamp(item.get('providerPublishTime', 0))),
                        "summary": ""
                        # Note: yfinance often doesn't give full summary, but link is key.
                    }
                    results.append(normalized)
            except Exception as e:
                # Silent fail for individual ticker
                pass
                
        # Sort by latest
        results.sort(key=lambda x: x['published'], reverse=True)
        return results[:20]

if __name__ == "__main__":
    api = YahooAPI()
    items = api.fetch()
    print(f"Fetched {len(items)} items from API.")
    for i in items:
        print(f"[{i['published']}] {i['title']}")
