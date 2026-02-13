import feedparser
import datetime
from time import mktime
import sys
import os

# Add src to path to import intelligence
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))
from src.intelligence.filter import NewsFilter
from src.ingestion.yahoo_api import YahooAPI
from src.intelligence.market_analyst import MarketAnalyst
from src.intelligence.targeting import TargetingManager

# Configuration
SOURCES = [
    {
        "name": "CNBC Finance",
        "url": "https://www.cnbc.com/id/10000664/device/rss/rss.html",
        "tags": ["finance"]
    }
]

# Phase 26: Redundant Data Stream
BACKUP_SOURCES = [
    {
        "name": "MarketWatch",
        "url": "https://www.marketwatch.com/rss/marketupdate",
        "tags": ["market"]
    },
    {
        "name": "Yahoo RSS (Fallback)",
        "url": "https://finance.yahoo.com/news/rssindex",
        "tags": ["finance"]
    }
]

SOURCE_CREDIBILITY = {
    "Reuters": 20,
    "Bloomberg": 20,
    "Wall Street Journal": 20,
    "WSJ": 20,
    "CNBC": 10,
    "Yahoo Finance": 5,
    "Google News": 0,
    "Twitter": -10,
    "Unverified": -20
}

def parse_date(entry):
    """Attempt to parse published date to datetime object."""
    if hasattr(entry, 'published_parsed'):
        return datetime.datetime.fromtimestamp(mktime(entry.published_parsed))
    return datetime.datetime.now()

def fetch_and_filter(active_tickers=None):
    nf = NewsFilter()
    analyst = MarketAnalyst()
    targeting = TargetingManager()
    results = []
    alerts = []
    
    # Phase 4: Zenith Turbo - Parallel Ingestion
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    print(f"Fetching and Filtering from {len(SOURCES)} sources + API (Parallel Mode)...")
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_source = {}
        
        # 1. Submit Yahoo API Task
        def fetch_yahoo_api():
            api = YahooAPI()
            return api.fetch()
        
        future_api = executor.submit(fetch_yahoo_api)
        future_to_source[future_api] = "YahooAPI"
        
        # 2. Submit RSS Feed Tasks
        def fetch_rss(source_conf):
            try:
                feed = feedparser.parse(source_conf['url'])
                return source_conf, feed.entries
            except Exception as e:
                print(f"Error fetching {source_conf['name']}: {e}")
                return source_conf, []
                
        for source in SOURCES:
            future = executor.submit(fetch_rss, source)
            future_to_source[future] = source['name']
            
        # 3. Process Results as they arrive
        for future in as_completed(future_to_source):
            src_name = future_to_source[future]
            try:
                if src_name == "YahooAPI":
                    api_results = future.result()
                    print(f"  > Yahoo API: {len(api_results)} items")
                    for item in api_results:
                         # 1. Basic Filter
                         summary = item['title'] 
                         analysis = nf.evaluate(item['title'], summary)
                         
                         # 2. Deep Analysis
                         market_analysis = analyst.analyze(item['title'], summary, analysis['sentiment'])
                         
                         # 2b. Source Credibility
                         source_bonus = 0
                         for s, bonus in SOURCE_CREDIBILITY.items():
                             if s.lower() in item.get('source', '').lower():
                                 source_bonus = bonus
                                 break
                         
                         if 'synthesis' in market_analysis:
                             market_analysis['synthesis']['score'] += source_bonus
                             if source_bonus > 0:
                                 market_analysis['reason'] += f" ✅ VERIFIED SOURCE: {item.get('source')} (+{source_bonus})"
                             elif source_bonus < 0:
                                 market_analysis['reason'] += f" 🛡️ LOW CREDIBILITY: ({source_bonus})"
                         
                         analysis['market_analysis'] = market_analysis
                         
                         # 3. Targeting
                         ticker = market_analysis.get('ticker')
                         priority = targeting.check_priority(ticker, active_tickers)
                         should_alert = targeting.should_alert(ticker, market_analysis.get('direction'), priority)
                         
                         analysis['is_watchlist'] = (priority == 'CRITICAL')
                         item['analysis'] = analysis
                         
                         if should_alert: alerts.append(item)
                         results.append(item)
                         
                else:
                    # RSS Result
                    source_conf, entries = future.result()
                    print(f"  > {src_name}: {len(entries)} items")
                    
                    for entry in entries:
                        title = entry.title
                        link = entry.link
                        summary = getattr(entry, 'summary', '')
                        
                        analysis = nf.evaluate(title, summary)
                        item = {
                            "source": source_conf['name'],
                            "title": title,
                            "link": link,
                            "published": str(parse_date(entry)),
                            "analysis": analysis
                        }
                        
                        if analysis['is_important']: alerts.append(item)
                        results.append(item)
                        
            except Exception as e:
                print(f"  Error processing {src_name}: {e}")

    # 3. Data Redundancy Check (Phase 26) & Fallback (Phase 54)
    if len(results) == 0:
        print("  [Prophet] ⚠️ Primary sources FAILED. Activating Redundant Data Stream...")
        
        # Fallback A: Backup RSS
        for source in BACKUP_SOURCES:
            try:
                feed = feedparser.parse(source['url'])
                print(f"  > Backup {source['name']}: {len(feed.entries)} items")
                for entry in feed.entries:
                    analysis = nf.evaluate(entry.title, getattr(entry, 'summary', ''))
                    item = {
                        "source": source['name'],
                        "title": entry.title,
                        "link": entry.link,
                        "published": str(parse_date(entry)),
                        "analysis": analysis
                    }
                    if analysis['is_important']: alerts.append(item)
                    results.append(item)
            except:
                continue
                
        # Fallback B: Yahoo Finance API (Robust)
        if len(results) == 0 and active_tickers:
            print(f"  [Prophet] 🆘 ALL RSS DOWN. Engaging Emergency API Scan for {len(active_tickers)} assets...")
            import yfinance as yf
            
            for ticker in active_tickers[:5]: # Check top 5 active to save time
                try:
                     t = yf.Ticker(ticker)
                     news = t.news
                     for n in news:
                         title = n.get('title', '')
                         if not title: continue
                         
                         analysis = nf.evaluate(title, title) # Summary is title
                         item = {
                             "source": f"YahooAPI({ticker})",
                             "title": title,
                             "link": n.get('link', ''),
                             "published": datetime.datetime.fromtimestamp(n.get('providerPublishTime', time.time())).strftime("%Y-%m-%d %H:%M:%S"),
                             "analysis": analysis
                         }
                         results.append(item)
                         if analysis['is_important']: alerts.append(item)
                except Exception as e:
                    print(f"  [Prophet] API Error on {ticker}: {e}")

    # Phase 59: Blind Mode Protocol
    if len(results) == 0:
        print("\n" + "="*60)
        print("🚨 CRITICAL WARNING: BLIND MODE ACTIVATED 🚨")
        print("All News Sources (RSS + API) are unreachable.")
        print("System will reduce polling frequency to prevent IP Ban.")
        print("Recommendations:")
        print("1. Check Internet Connection.")
        print("2. Verify Yahoo Finance API access.")
        print("="*60 + "\n")
        
    # Sort alerts by published date
    alerts.sort(key=lambda x: x['published'], reverse=True)
    return alerts, results

if __name__ == "__main__":
    alerts, all_news = fetch_and_filter()
    
    print(f"\nProcessed {len(all_news)} news items.")
    print(f"Found {len(alerts)} POTENTIAL ALERTS.")
    
    print("\n=== ALERT CANDIDATES ===")
    for item in alerts:
        print(f"[{item['published']}] {item['source']}")
        print(f"TITLE:   {item['title']}")
        print(f"REASON:  {item['analysis']['reason']}")
        print(f"SCORE:   {item['analysis']['sentiment']}")
        print(f"LINK:    {item['link']}")
        print("-" * 60)
