import requests
import os
import feedparser
import time
from datetime import datetime

# --- CONFIGURATION ---
INSTAPAPER_USER = os.environ.get("INSTAPAPER_USER")
INSTAPAPER_PASS = os.environ.get("INSTAPAPER_PASS")

def add_url_to_instapaper(url):
    """Sends individual links to Instapaper. Returns True if successful."""
    if not INSTAPAPER_USER or not INSTAPAPER_PASS:
        return False
    api_url = "https://www.instapaper.com/api/add"
    # unique tag for individual articles
    unique_url = f"{url}?sync={int(time.time())}"
    try:
        r = requests.post(api_url, auth=(INSTAPAPER_USER, INSTAPAPER_PASS), data={'url': unique_url}, timeout=15)
        return r.status_code == 200
    except:
        return False

def get_weather_afd():
    """Scrapes raw NOAA text."""
    url = "https://forecast.weather.gov/product.php?site=iwx&issuedby=iwx&product=afd&format=ci&version=1&glossary=1"
    try:
        r = requests.get(url, timeout=20, headers={'User-Agent': 'Mozilla/5.0'})
        r.encoding = 'utf-8'
        if '<pre class="glossaryProduct">' in r.text:
            start = r.text.find('<pre class="glossaryProduct">') + 29
            end = r.text.find('</pre>', start)
            return r.text[start:end].replace('&nbsp;', ' ').replace('&amp;', '&')
        return "Weather discussion tag not found."
    except Exception as e:
        return f"Weather connection error: {e}"

def main():
    # 1. NEWS SYNC & ARCHIVE
    archive_items = []
    feeds = {
        "Guardian": "https://www.theguardian.com/news/series/the-long-read/rss",
        "NYT": "https://rss.nytimes.com/services/xml/rss/nyt/TheMorning.xml"
    }
    
    print("Syncing News...")
    for name, feed_url in feeds.items():
        try:
            resp = requests.get(feed_url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
            feed = feedparser.parse(resp.content)
            print(f"  {name}: Found {len(feed.entries)} articles total.")
            
            limit = 10 if name == "Guardian" else 2
            count = 0
            for entry in feed.entries:
                if count >= limit: break
                # More precise filter: only excludes if 'sport' or 'podcast' is in the URL path
                link_lower = entry.link.lower()
                is_excluded = any(x in link_lower for x in ['/sport/', '/football/', '/podcast/', '/audio/'])
                
                if not is_excluded:
                    if add_url_to_instapaper(entry.link):
                        archive_items.append(f'<li><a href="{entry.link}">{entry.title}</a> ({name})</li>')
                        count += 1
                        print(f"    Sent: {entry.title}")
                        time.sleep(2) # Breath between articles
        except Exception as e:
            print(f"  Error with {name}: {e}")

    # 2. BUILDING THE PAGE
    weather_raw = get_weather_afd()
    current_dt = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    archive_list = "".join(archive_items) if archive_items else "<li>No articles synced this run.</li>"

    html_content = f"""
    <div class="masthead">liroh daily</div>
    <p class="timestamp"><strong>Updated:</strong> {current_dt}</p>
    <hr>
    <h2>🌩️ Weather Discussion</h2>
    <div class="weather-block">{weather_raw}</div>
    <hr>
    <h2>📰 Today's Archive</h2>
    <ul>{archive_list}</ul>
    <hr>
    <h2>🤖 Reddit Highlights</h2>
    <div class="reddit-block">Awaiting API...</div>
    """

    html_wrapper = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><link rel="stylesheet" href="style.css"><title>liroh daily</title></head><body>{html_content}</body></html>"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_wrapper)
    print("Success: index.html created.")

if __name__ == "__main__":
    main()