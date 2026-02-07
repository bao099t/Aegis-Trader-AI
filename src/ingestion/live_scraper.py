import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import datetime
import random
import time

class LiveScraper:
    def __init__(self):
        self.ua = UserAgent()
        # Yahoo Finance "Latest News" Stream
        self.url = "https://finance.yahoo.com/topic/stock-market-news/"
        
    def get_headers(self):
        return {
            "User-Agent": self.ua.random,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": "https://finance.yahoo.com/"
        }

    def fetch(self):
        print(f"  [Scraper] Hitting {self.url}...")
        try:
            # Random sleep to behave like human (0.5 - 1.5s)
            time.sleep(random.uniform(0.5, 1.5))
            
            resp = requests.get(self.url, headers=self.get_headers(), timeout=10)
            if resp.status_code != 200:
                print(f"  [Scraper] Failed. Status: {resp.status_code}")
                return []

            soup = BeautifulSoup(resp.text, 'html.parser')
            results = []

            # Yahoo's structure often puts news in a specific stream
            # We look for common patterns in their "Stream" layout
            # Note: This is brittle and might break if Yahoo changes classes. 
            # We look for h3 tags which usually contain the titles.
            
            articles = soup.find_all('h3')
            
            for art in articles:
                # Yahoo usually wraps the link in an 'a' tag inside 'h3'
                link_tag = art.find('a')
                if not link_tag:
                    continue
                
                title = link_tag.get_text()
                link = link_tag.get('href', '')
                
                if not link.startswith('http'):
                    link = 'https://finance.yahoo.com' + link
                
                # Check exclusion (ads, generic non-news)
                if 'finance.yahoo.com' not in link and 'yhoo.it' not in link:
                    continue

                item = {
                    "source": "Yahoo (Live)",
                    "title": title,
                    "link": link,
                    "published": str(datetime.datetime.now()), # Live stream implies "Now"
                    "summary": "" # Scrapers often miss summary on index pages
                }
                results.append(item)
            
            # Deduplicate locally or limit
            return results[:10]

        except Exception as e:
            print(f"  [Scraper] Error: {e}")
            return []

if __name__ == "__main__":
    ls = LiveScraper()
    news = ls.fetch()
    print(f"Fetched {len(news)} items.")
    for n in news:
        print(f"- {n['title']}")
