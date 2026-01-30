import requests
import os
import feedparser
import time
from datetime import datetime, timedelta

# --- configuration ---
INSTAPAPER_USER = os.environ.get("INSTAPAPER_USER")
INSTAPAPER_PASS = os.environ.get("INSTAPAPER_PASS")

def add_url_to_instapaper(url):
    api_url = "https://www.instapaper.com/api/add"
    unique_url = f"{url}?kobosync={int(time.time())}"
    try:
        r = requests.post(api_url, auth=(INSTAPAPER_USER, INSTAPAPER_PASS), data={'url': unique_url}, timeout=15)
        return r.status_code == 200
    except:
        return False

def get_weather_afd():
    url = "https://forecast.weather.gov/product.php?site=iwx&issuedby=iwx&product=afd&format=ci&version=1&glossary=1"
    try:
        r = requests.get(url, timeout=20, headers={'User-Agent': 'Mozilla/5.0'})
        r.encoding = 'utf-8'
        if '<pre class="glossaryProduct">' in r.text:
            start = r.text.find('<pre class="glossaryProduct">') + 29
            end = r.text.find('</pre>', start)
            return r.text[start:end].replace('&nbsp;', ' ').replace('&amp;', '&')
        return "weather data currently unavailable."
    except:
        return "weather connection error."

def update_archive_index():
    if not os.path.exists("old_issues"):
        return
    files = sorted([f for f in os.listdir("old_issues") if f.endswith(".html")], reverse=True)
    links = "".join([f'<li><a href="old_issues/{f}">{f.replace(".html", "")}</a></li>' for f in files])
    
    index_html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><link rel="stylesheet" href="style.css"></head>
    <body>
        <div class="masthead">old issues</div>
        <p><a href="index.html">← back to current</a></p>
        <ul>{links}</ul>
    </body></html>"""
    with open("archive.html", "w", encoding="utf-8") as f:
        f.write(index_html)

def main():
    # 1. handle cst time (utc - 6)
    utc_now = datetime.utcnow()
    cst_now = utc_now - timedelta(hours=6)
    date_str = cst_now.strftime("%b %d, %y").lower()
    time_str = cst_now.strftime("%I:%M %p").lower()
    file_date = cst_now.strftime("%Y-%m-%d")

    # 2. sync guardian long reads
    archive_items = []
    feed_url = "https://www.theguardian.com/news/series/the-long-read/rss"
    
    print("syncing news...")
    try:
        resp = requests.get(feed_url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
        feed = feedparser.parse(resp.content)
        
        count = 0
        for entry in feed.entries:
            if count >= 10: break
            if not any(x in entry.link.lower() for x in ['/sport/', '/podcast/', '/audio/']):
                if add_url_to_instapaper(entry.link):
                    archive_items.append(f'<li><a href="{entry.link}">{entry.title.lower()}</a></li>')
                    count += 1
                    time.sleep(1)
    except Exception as e:
        print(f"feed error: {e}")
    
    # 3. build newsletter body
    weather_raw = get_weather_afd()
    daily_links = "".join(archive_items) if archive_items else "<li>no links synced today.</li>"

    html_body = f"""
    <div class="masthead">liroh daily</div>
    <div class="timestamp">{date_str} // {time_str} cst</div>
    
    <h2>weather discussion</h2>
    <div class="weather-block">{weather_raw}</div>
    
    <h2>daily links</h2>
    <ul>{daily_links}</ul>
    
    <h2>reddit highlights</h2>
    <p>awaiting credentials...</p>
    
    <hr style="margin-top:50px; border:0; border-top:1px dashed #ccc;">
    <p style="font-size:12px; text-align:center;"><a href="archive.html">view old issues</a></p>
    """

    final_html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><link rel="stylesheet" href="style.css"></head><body>{html_body}</body></html>"""

    # 4. save files
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(final_html)

    if not os.path.exists("old_issues"):
        os.makedirs("old_issues")
    
    archive_html = final_html.replace('href="style.css"', 'href="../style.css"')
    with open(f"old_issues/{file_date}.html", "w", encoding="utf-8") as f:
        f.write(archive_html)
        
    update_archive_index()
    print("success: liroh daily updated.")

if __name__ == "__main__":
    main()