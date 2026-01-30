import requests
import os
import feedparser
import time
from datetime import datetime

# --- CONFIGURATION ---
INSTAPAPER_USER = os.environ.get("INSTAPAPER_USER")
INSTAPAPER_PASS = os.environ.get("INSTAPAPER_PASS")

def add_url_to_instapaper(url):
    """Sends individual links to Instapaper and returns True if successful."""
    if not INSTAPAPER_USER or not INSTAPAPER_PASS:
        return False
    api_url = "https://www.instapaper.com/api/add"
    unique_url = f"{url}?kobosync={int(time.time())}"
    try:
        r = requests.post(api_url, auth=(INSTAPAPER_USER, INSTAPAPER_PASS), data={'url': unique_url}, timeout=15)
        print(f"  [{r.status_code}] Direct Push: {unique_url}")
        return r.status_code == 200
    except Exception as e:
        print(f"  Error: {e}")
        return False

def get_weather_afd():
    """Scrapes raw NOAA text with better tag detection."""
    url = "https://forecast.weather.gov/product.php?site=iwx&issuedby=iwx&product=afd&format=ci&version=1&glossary=1"
    try:
        r = requests.get(url, timeout=20, headers={'User-Agent': 'Mozilla/5.0'})
        r.encoding = 'utf-8'
        if '<pre class="glossaryProduct">' in r.text:
            start = r.text.find('<pre class="glossaryProduct">') + 29
            end = r.text.find('</pre>', start)
            return r.text[start:end].replace('&nbsp;', ' ').replace('&amp;', '&')
        return "Weather discussion tag not found on NOAA page."
    except Exception as e:
        return f"Weather connection error: {e}"

def main():
    # 1. DIRECT NEWS & ARCHIVE BUILDING
    archive_html = "<ul>"
    print("Syncing News...")
    feeds = {
        "Guardian": "https://www.theguardian.com/news/series/the-long-read/rss",
        "NYT": "https://rss.nytimes.com/services/xml/rss/nyt/TheMorning.xml"
    }
    
    for name, feed_url in feeds.items():
        try:
            resp = requests.get(feed_url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
            feed = feedparser.parse(resp.content)
            limit = 10 if name == "Guardian" else 2
            count = 0
            for entry in feed.entries:
                if count >= limit: break
                if not any(s in entry.link.lower() for s in ['sport', 'football', 'podcast', 'audio']):
                    success = add_url_to_instapaper(entry.link)
                    if success:
                        archive_html += f'<li><a href="{entry.link}">{entry.title}</a> ({name})</li>'
                        count += 1
                        time.sleep(2)
        except Exception as e:
            print(f"Feed error: {e}")
    
    archive_html += "</ul>"

    # 2. BUILDING THE PAGE
    print("Building Newsletter...")
    weather_raw = get_weather_afd()
    current_dt = datetime.now().strftime("%B %d, %Y at %I:%M %p")

    # Construct the HTML body directly (Avoiding Markdown errors)
    html_content = f"""
    <h1>liroh daily</h1>
    <p><strong>Updated:</strong> {current_dt}</p>
    <hr>
    <h2>🌩️ Weather Discussion (IWX)</h2>
    <div class="weather-block">{weather_raw}</div>
    <hr>
    <h2>📰 Today's Archive</h2>
    <p>The following articles were sent to your Instapaper feed:</p>
    {archive_html}
    <hr>
    <h2>🤖 Reddit Highlights</h2>
    <div class="reddit-block">Awaiting API Credentials...</div>
    """

    # 3. FINAL WRAPPER
    html_wrapper = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <link rel="stylesheet" href="style.css">
    <title>liroh daily</title>
</head>
<body>
    {html_content}
</body>
</html>"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_wrapper)
    print("Success: index.html created.")

if __name__ == "__main__":
    main()