import requests
import os
import feedparser
import time
from datetime import datetime

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
    """generates a minimalist index of all files in old_issues/"""
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
    # 1. sync news
    archive_items = []
    feeds = {
        "guardian": "https://www.theguardian.com/news/series/the-long-read/rss",
        "nyt": "https://rss.nytimes.com/services/xml/rss/nyt/TheMorning.xml"
    }
    
    for name, feed_url in feeds.items():
        try:
            resp = requests.get(feed_url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
            feed = feedparser.parse(resp.content)
            limit = 10 if name == "guardian" else 2
            count = 0
            for entry in feed.entries:
                if count >= limit: break
                if not any(x in entry.link.lower() for x in ['/sport/', '/podcast/']):
                    if add_url_to_instapaper(entry.link):
                        archive_items.append(f'<li><a href="{entry.link}">{entry.title.lower()}</a></li>')
                        count += 1
                        time.sleep(1)
        except:
            continue
    
    # 2. build content
    weather_raw = get_weather_afd()
    now = datetime.now()
    date_str = now.strftime("%b %d, %y")
    time_str = now.strftime("%I:%M %p").lower()
    file_date = now.strftime("%Y-%m-%d")
    
    daily_links = "".join(archive_items) if archive_items else "<li>no links synced today.</li>"

    html_body = f"""
    <div class="masthead">liroh daily</div>
    <div class="timestamp">{date_str} // {time_str}</div>
    
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

    # 3. save live version
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(final_html)

    # 4. save to archive folder with adjusted CSS path
    if not os.path.exists("old_issues"):
        os.makedirs("old_issues")
    
    # replace the relative link so archived files can find the css one level up
    archive_html = final_html.replace('href="style.css"', 'href="../style.css"')
    
    with open(f"old_issues/{file_date}.html", "w", encoding="utf-8") as f:
        f.write(archive_html)
        
    # 5. update the index
    update_archive_index()
    print("success: newsletter and archive updated.")

if __name__ == "__main__":
    main()