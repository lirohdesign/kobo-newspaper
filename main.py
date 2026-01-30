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
            # Wrap the entire weather block in a div that Instapaper recognizes as 'content'
            return f'<div class="instapaper_body"><h3>today\'s weather discussion</h3>{"".join(html_p)}</div>'
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
                # Change the list item to include a small snippet or 'Read more' text
                # This adds 'weight' to the section so the bot doesn't ignore it.
                links_html.append(f'<li><strong>{entry.title.lower()}</strong> — <a href="{entry.link}">read full article at the guardian</a></li>')
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
            with open(path, "r", encoding="utf-8") as f:
                raw_html = f.read()
            
            # 1. Strip scripts/styles to prevent layout hijacking
            clean = re.sub(r'<(style|script)[^>]*>.*?</\1>', '', raw_html, flags=re.DOTALL)
            
            # 2. Extract P, H3, and IMG tags
            content_blocks = re.findall(r'<(p|h3|img)[^>]*>(.*?)</\1>|<img[^>]*>', clean, flags=re.DOTALL)
            
            html_out = []
            for match in content_blocks:
                # Reconstruct the tag without any of its original attributes (IDs, classes, styles)
                # except for the 'src' on images.
                full_tag = match[0] or "" 
                
                if 'img' in full_tag or '<img' in str(match):
                    # Extract just the SRC to avoid tracking pixels or oversized fixed widths
                    src_match = re.search(r'src="([^"]+)"', str(match))
                    if src_match:
                        src = src_match.group(1)
                        # Skip tiny tracking pixels (usually 1x1 or containing 'spacer')
                        if "spacer" not in src and "tracking" not in src:
                            html_out.append(f'<img src="{src}" style="max-width: 100%; height: auto; margin: 1em 0;">')
                else:
                    tag_type = match[0]
                    text_content = re.sub(r'<[^>]+>', '', match[1]) # Strip links inside the text
                    if len(text_content.strip()) > 30:
                        html_out.append(f'<{tag_type}>{text_content.strip()}</{tag_type}>')
            
            return "".join(html_out)
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
        nyt_content = collect_nyt() 

        html_body = f"""
        <div id="instapaper_filler">
            <article>
                <h1>liroh daily: {date_str}</h1>
                
                <section id="weather-section">
                    <h2>01. weather discussion</h2>
                    {weather_content}
                </section>
                
                <hr>
                
                <section id="nyt-section">
                    <h2>02. the morning news</h2>
                    {nyt_content}
                </section>
                
                <hr>
                
                <section id="links-section">
                    <h2>03. daily links</h2>
                    <ul>{news_content}</ul>
                </section>
            </article>
        </div>
        """

        # Define final_html BEFORE trying to write files
        final_html = f"<!DOCTYPE html><html><head><meta charset='UTF-8'><link rel='stylesheet' href='style.css'></head><body>{html_body}</body></html>"

        # ENSURE FOLDER EXISTS
        if not os.path.exists("old_issues"):
            os.makedirs("old_issues")
            print("DIAGNOSTIC: Created old_issues directory.")

        # Save to main index
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(final_html)
            print("DIAGNOSTIC: index.html written.")

        # Save to archive folder
        archive_path = f"old_issues/{file_date}.html"
        with open(archive_path, "w", encoding="utf-8") as f:
            f.write(final_html.replace('href="style.css"', 'href="../style.css"'))
        
        update_archive_index()

        if os.path.exists("nyt_morning.html"):
            os.remove("nyt_morning.html")
            print("DIAGNOSTIC: NYT temp file cleared.")
        
        print("--- BUILD SUCCESSFUL ---")
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")

if __name__ == "__main__":
    main()