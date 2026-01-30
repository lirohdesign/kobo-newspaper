import requests
import os
import feedparser
import time
import re
from datetime import datetime, timedelta

# --- settings ---
INSTAPAPER_USER = os.environ.get("INSTAPAPER_USER")
INSTAPAPER_PASS = os.environ.get("INSTAPAPER_PASS")

def add_to_instapaper(url):
    api_url = "https://www.instapaper.com/api/add"
    try:
        r = requests.post(api_url, auth=(INSTAPAPER_USER, INSTAPAPER_PASS), data={'url': url}, timeout=15)
        return r.status_code == 200
    except:
        return False

def collect_weather():
    url = "https://forecast.weather.gov/product.php?site=iwx&issuedby=iwx&product=afd&format=ci&version=1&glossary=1"
    try:
        r = requests.get(url, timeout=20, headers={'User-Agent': 'Mozilla/5.0'})
        r.encoding = 'utf-8'
        if '<pre class="glossaryProduct">' in r.text:
            start = r.text.find('<pre class="glossaryProduct">') + 29
            end = r.text.find('</pre>', start)
            raw = r.text[start:end].replace('&nbsp;', ' ').replace('&amp;', '&')
            clean_text = re.sub(r'<a [^>]*>(.*?)</a>', r'\1', raw)
            paragraphs = clean_text.split('\n\n')
            html_p = []
            for p in paragraphs:
                if p.strip():
                    clean_p = p.replace('\n', ' ').strip()
                    html_p.append(f'<p style="margin-bottom: 1em;">{clean_p}</p>')
            return "".join(html_p)
    except:
        pass
    return "<p>weather unavailable.</p>"

def collect_guardian_links():
    links_html = []
    feed_url = "https://www.theguardian.com/news/series/the-long-read/rss"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        print("DIAGNOSTIC: Fetching Guardian RSS...")
        resp = requests.get(feed_url, timeout=15, headers=headers)
        feed = feedparser.parse(resp.content)
        print(f"DIAGNOSTIC: Found {len(feed.entries)} entries.")
        count = 0
        for entry in feed.entries:
            if count >= 10: break
            link_low = entry.link.lower()
            if not any(x in link_low for x in ['/podcasts/', '/video/', '/sport/']):
                add_to_instapaper(entry.link)
                links_html.append(f'<li><a href="{entry.link}">{entry.title.lower()}</a></li>')
                count += 1
                print(f"DIAGNOSTIC: Added {entry.title[:30]}")
        return "".join(links_html)
    except Exception as e:
        print(f"DIAGNOSTIC ERROR (Guardian): {e}")
        return "<li>guardian sync error.</li>"

def update_archive_index():
    if not os.path.exists("old_issues"): return
    files = sorted([f for f in os.listdir("old_issues") if f.endswith(".html")], reverse=True)
    links = "".join([f'<li><a href="old_issues/{f}">{f.replace(".html", "")}</a></li>' for f in files])
    index_html = f"<!DOCTYPE html><html><body><h1>archive</h1><ul>{links}</ul></body></html>"
    with open("archive.html", "w", encoding="utf-8") as f: f.write(index_html)

def collect_nyt():
    path = "nyt_morning.html"
    if os.path.exists(path):
        try:
            print("DIAGNOSTIC: Found NYT morning file. Injecting...")
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Simple wrapper to keep it distinct in the newsletter
            return f'<div class="nyt-section">{content}</div>'
        except Exception as e:
            print(f"DIAGNOSTIC ERROR (NYT): {e}")
    return ""

def main():
    try:
        print("--- BUILD START ---")
        cst_now = datetime.utcnow() - timedelta(hours=6)
        date_str = cst_now.strftime("%b %d, %y").lower()
        time_str = cst_now.strftime("%I:%M %p").lower()
        file_date = cst_now.strftime("%Y-%m-%d")

        weather_content = collect_weather()
        news_content = collect_guardian_links()
        nyt_content = collect_nyt() # Get the NYT data

        html_body = f"""
        <header>
            <h1 class="masthead">liroh daily</h1>
            <h3 style="font-weight: normal; text-transform: lowercase;">
                <time>{date_str} // {time_str} cst</time>
            </h3>
        </header>
        <article>
            <section><h2>weather</h2>{weather_content}</section>
            <section><h2>the morning</h2>{nyt_content}</section>
            <section><h2>links</h2><ul>{news_content}</ul></section>
        </article>
        """

        # 1. Save the new issue to the archive folder
        archive_path = f"old_issues/{file_date}.html"
        with open(archive_path, "w", encoding="utf-8") as f:
            f.write(final_html.replace('href="style.css"', 'href="../style.css"'))
        
        # 2. Rebuild the archive list (KEEP THIS)
        update_archive_index()

        # 3. Clean up the temporary NYT file
        if os.path.exists("nyt_morning.html"):
            os.remove("nyt_morning.html")
            print("DIAGNOSTIC: NYT temp file cleared.")
        
        print("--- BUILD SUCCESSFUL ---")
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")

if __name__ == "__main__":
    main()