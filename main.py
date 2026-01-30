import os
import feedparser
import time
from datetime import datetime

# --- CONFIGURATION ---
INSTAPAPER_USER = os.environ.get("INSTAPAPER_USER")
INSTAPAPER_PASS = os.environ.get("INSTAPAPER_PASS")

def add_url_to_instapaper(url):
    """Sends individual links to Instapaper using Basic Auth."""
    if not INSTAPAPER_USER or not INSTAPAPER_PASS:
        return
    api_url = "https://www.instapaper.com/api/add"
    unique_url = f"{url}?kobosync={int(time.time())}"
    try:
        # Using 'auth=' here matches the curl -u command in your yml
        r = requests.post(api_url, auth=(INSTAPAPER_USER, INSTAPAPER_PASS), data={'url': unique_url}, timeout=15)
        print(f"  [{r.status_code}] Direct Push: {unique_url}")
        time.sleep(2)
    except Exception as e:
        print(f"  Error: {e}")

def get_weather_afd():
    """Scrapes raw weather text. We will handle reflow via CSS now."""
    url = "https://forecast.weather.gov/product.php?site=iwx&issuedby=iwx&product=afd&format=ci&version=1&glossary=1"
    try:
        r = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
        r.encoding = 'utf-8'
        start = r.text.find('<pre class="glossaryProduct">') + 29
        end = r.text.find('</pre>', start)
        return r.text[start:end].replace('&nbsp;', ' ').replace('&amp;', '&')
    except:
        return "Weather unavailable."

def main():
    # 1. DIRECT NEWS
    print("Syncing News...")
    feeds = {
        "Guardian": "https://www.theguardian.com/news/series/the-long-read/rss",
        "NYT": "https://rss.nytimes.com/services/xml/rss/nyt/TheMorning.xml"
    }
    for name, url in feeds.items():
        try:
            resp = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
            feed = feedparser.parse(resp.content)
            limit = 10 if name == "Guardian" else 2
            count = 0
            for entry in feed.entries:
                if count >= limit: break
                # Podcast and Sport Filter
                if not any(s in entry.link.lower() for s in ['sport', 'football', 'podcast', 'audio']):
                    add_url_to_instapaper(entry.link)
                    count += 1
        except:
            continue

    # 2. NEWSLETTER CONTENT
    print("Building Newsletter...")
    weather_raw = get_weather_afd()
    
    with open("newsletter_template.md", "r") as f:
        template = f.read()

    # We use a simple div; the CSS file handles the 'Natural Flow' wrapping
    weather_html = f'<div class="weather-block">{weather_raw}</div>'
    
    final_body = template.replace("{{date}}", datetime.now().strftime("%B %d, %Y"))
    final_body = final_body.replace("{{weather}}", weather_html)
    final_body = final_body.replace("{{news}}", "*Articles sent separately.*")
    final_body = final_body.replace("{{reddit}}", '<div class="reddit-block">Awaiting API...</div>')

    # 3. HTML Wrapper (No more braces to crash Python!)
    html_wrapper = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <link rel="stylesheet" href="style.css">
</head>
<body>
    {content}
</body>
</html>"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_wrapper.format(content=final_body))
    print("Success: index.html created.")

if __name__ == "__main__":
    main()