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

def fetch_and_filter():
    nf = NewsFilter()
    analyst = MarketAnalyst()
    targeting = TargetingManager()
    results = []
    alerts = []
    
    print(f"Fetching and Filtering from {len(SOURCES)} sources + API...")
    
    # 1. Fetch from Yahoo API
    api = YahooAPI()
    api_results = api.fetch()
    print(f"  > Yahoo API: {len(api_results)} items")
    
    for item in api_results:
        # 1. Basic Filter (Is it important?)
        summary = item['title'] 
        analysis = nf.evaluate(item['title'], summary)
        
        # 2. Deep Analysis (If meaningful)
        market_analysis = analyst.analyze(item['title'], summary, analysis['sentiment'])
        
        # 2b. Source Credibility (Phase 23)
        source_bonus = 0
        for src, bonus in SOURCE_CREDIBILITY.items():
            if src.lower() in item.get('source', '').lower():
                source_bonus = bonus
                break
        
        if 'synthesis' in market_analysis:
            market_analysis['synthesis']['score'] += source_bonus
            if source_bonus > 0:
                market_analysis['reason'] += f" ✅ VERIFIED SOURCE: {item.get('source')} (+{source_bonus} conv)"
            elif source_bonus < 0:
                market_analysis['reason'] += f" 🛡️ LOW CREDIBILITY SOURCE: Proceed with caution ({source_bonus})"
        
        analysis['market_analysis'] = market_analysis
        
        # 3. Targeting & Priority Logic
        ticker = market_analysis.get('ticker')
        direction = market_analysis.get('direction', 'NEUTRAL')
        
        priority = targeting.check_priority(ticker)
        should_alert = targeting.should_alert(ticker, direction, priority)
        
        if priority == 'CRITICAL':
             analysis['is_watchlist'] = True
        else:
             analysis['is_watchlist'] = False

        item['analysis'] = analysis
            
        alerts.append(item) if should_alert else None
        results.append(item)

    # 2. Fetch from RSS (Skipping deep analysis for RSS for now to save API calls, or enable if needed)
    for source in SOURCES:
        try:
            feed = feedparser.parse(source['url'])
            print(f"  > {source['name']}: {len(feed.entries)} items")
            
            for entry in feed.entries:
                title = entry.title
                link = entry.link
                summary = getattr(entry, 'summary', '')
                
                # EVALUATE
                analysis = nf.evaluate(title, summary)
                
                item = {
                    "source": source['name'],
                    "title": title,
                    "link": link,
                    "published": str(parse_date(entry)),
                    "analysis": analysis
                }
                
                if analysis['is_important']:
                    alerts.append(item)
                
                results.append(item)
                    
        except Exception as e:
            print(f" Error fetching {source['name']}: {e}")

    # 3. Data Redundancy Check (Phase 26)
    if len(results) == 0:
        print("  [Prophet] ⚠️ Primary sources FAILED. Activating Redundant Data Stream...")
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
