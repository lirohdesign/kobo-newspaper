import requests
import os
import feedparser
import re
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
            raw = r.text[start:end].replace('&nbsp;', ' ').replace('&amp;', '&')
            
            # 1. remove glossary hyperlinks (keeps the text between the <a> tags)
            clean_text = re.sub(r'<a [^>]*>(.*?)</a>', r'\1', raw)
            
            # 2. handle kobo-friendly paragraph wrapping
            paragraphs = clean_text.split('\n\n')
            html_paragraphs = []
            for p in paragraphs:
                cleaned_p = p.replace('\n', ' ').strip()
                if cleaned_p:
                    # wrap in <p> tags for instapaper/kobo parsing
                    html_paragraphs.append(f'<p>{cleaned_p}</p>')
            return "".join(html_paragraphs)
        return "<p>weather data currently unavailable.</p>"
    except:
        return "<p>weather connection error.</p>"

def update_archive_index():
    if not os.path.exists("old_issues"):
        return
    files = sorted([f for f in os.listdir("old_issues") if f.endswith(".html")], reverse=True)
    links = "".join([f'<li><a href="old_issues/{f}">{f.replace(".html", "")}</a></li>' for f in files])
    
    index_html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><link rel="stylesheet" href="../style.css"></head>
    <body>
        <div class="masthead">old issues</div>
        <p><a href="../index.html">← back to current</a></p>
        <ul>{links}</ul>
    </body></html>"""
    with open("archive.html", "w", encoding="utf-8") as f:
        f.write(index_html)

def main():
    # 1. cst time handling (utc-6)
    utc_now = datetime.utcnow()
    cst_now = utc_now - timedelta(hours=6)
    date_str = cst_now.strftime("%b %d, %y").lower()
    time_str = cst_now.strftime("%I:%M %p").lower()
    file_date = cst_now.strftime("%Y-%m-%d")

    # 2. sync news (guardian)
    archive_items = []
    feed_url = "https://www.theguardian.com/news/series/the-long-read/rss"
    
    print(f"syncing news at {time_str} cst...")
    try:
        resp = requests.get(feed_url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
        feed = feedparser.parse(resp.content)
        print(f"  found {len(feed.entries)} entries.")
        
        count = 0
        for entry in feed.entries:
            if count >= 10: break
            
            # surgical filter: only block if it's a dedicated podcast page or sport section
            # this allows long reads that happen to have an 'audio' player inside them
            link_low = entry.link.lower()
            is_podcast_page = "/podcasts/" in link_low or "/video/" in link_low
            is_sport = "/sport/" in link_low or "/football/" in link_low
            
            if not (is_podcast_page or is_sport):
                if add_url_to_instapaper(entry.link):
                    archive_items.append(f'<li><a href="{entry.link}">{entry.title.lower()}</a></li>')
                    count += 1
                    time.sleep(1)
        print(f"  successfully synced {count} articles.")
    except Exception as e:
        print(f"  news sync failed: {e}")
    
    # 3. build body
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

    # 4. save and archive
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