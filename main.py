import requests
import os
import feedparser
import time
import re
import json
from datetime import datetime, timedelta

# --- settings ---
INSTAPAPER_USER = os.environ.get("INSTAPAPER_USER")
INSTAPAPER_PASS = os.environ.get("INSTAPAPER_PASS")
GUARDIAN_API_KEY = os.environ.get("GUARDIAN_API_KEY")

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
            return f'<div class="instapaper_body"><h3>today\'s weather discussion</h3>{"".join(html_p)}</div>'
    except:
        pass
    return "<p>weather unavailable.</p>"

def collect_guardian_api():
    """Fetches a clean pool of 50 articles using broad API filters."""
    if not GUARDIAN_API_KEY:
        print("DIAGNOSTIC: No Guardian API key found.")
        return []

    url = "https://content.guardianapis.com/search"
    params = {
        'api-key': GUARDIAN_API_KEY,
        'page-size': 50,
        'type': 'article',  # Kills liveblogs and crosswords
        'section': '-sport,-football,-community,-crosswords',  # Broad category filters
        'tag': '-tone/minutebyminute,-type/audio',  # Kills live updates and podcasts
        'show-fields': 'wordcount,trailText',
        'order-by': 'newest'
    }

    try:
        print("DIAGNOSTIC: Querying Guardian API for clean pool...")
        r = requests.get(url, params=params, timeout=15)
        data = r.json()
        results = data.get('response', {}).get('results', [])
        
        # SAVE RAW API OUTPUT FOR INSPECTION
        with open("guardian_raw.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        print("DIAGNOSTIC: guardian_raw.json updated with new API filters.")
        
        return results
    except Exception as e:
        print(f"DIAGNOSTIC ERROR (API Call): {e}")
        return []

def collect_nyt():
    path = "nyt_morning.html"
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw_html = f.read()
            clean = re.sub(r'<(style|script)[^>]*>.*?</\1>', '', raw_html, flags=re.DOTALL)
            content_blocks = re.findall(r'<(p|h3)[^>]*>(.*?)</\1>', clean, flags=re.DOTALL)
            html_out = []
            for tag, text in content_blocks:
                text_only = re.sub(r'<[^>]+>', '', text).strip()
                if len(text_only) > 40: 
                    html_out.append(f'<{tag}>{text_only}</{tag}>')
            return "".join(html_out)
        except Exception as e:
            print(f"DIAGNOSTIC ERROR (NYT): {e}")
    return ""

def update_archive_index():
    if not os.path.exists("old_issues"): return
    files = sorted([f for f in os.listdir("old_issues") if f.endswith(".html")], reverse=True)
    links = "".join([f'<li><a href="old_issues/{f}">{f.replace(".html", "")}</a></li>' for f in files])
    index_html = f"<!DOCTYPE html><html><body><h1>archive</h1><ul>{links}</ul></body></html>"
    with open("archive.html", "w", encoding="utf-8") as f: f.write(index_html)

def main():
    try:
        print("--- BUILD START ---")
        cst_now = datetime.utcnow() - timedelta(hours=6)
        date_str = cst_now.strftime("%b %d, %y").lower()
        time_str = cst_now.strftime("%I:%M %p").lower()
        file_date = cst_now.strftime("%Y-%m-%d")

        # 1. Load Sent History (Duplicate Prevention)
        sent_log_path = "sent_articles.json"
        if os.path.exists(sent_log_path):
            with open(sent_log_path, "r") as f:
                sent_ids = json.load(f)
        else:
            sent_ids = []

        # 2. Gather Content
        weather_content = collect_weather()
        nyt_content = collect_nyt()
        
        # 3. Process Guardian Pool (and update guardian_raw.json)
        raw_pool = collect_guardian_api()
        final_articles_html = []
        newly_sent_ids = []

        for article in raw_pool:
            if len(final_articles_html) >= 10:
                break
            
            article_id = article.get('id')
            title = article.get('webTitle', '').lower()
            link = article.get('webUrl', '')
            fields = article.get('fields', {})
            word_count = int(fields.get('wordcount', 0))

            # --- THE COMBING PHASE ---
            if article_id in sent_ids:
                continue
            
            if word_count < 1000:
                print(f"DIAGNOSTIC: Skipping short article ({word_count} words): {title[:30]}")
                continue

            # Success: Add to list and track
            add_to_instapaper(link)
            final_articles_html.append(f'<li><a href="{link}">{title}</a> — <small>{word_count} words</small></li>')
            newly_sent_ids.append(article_id)
            print(f"DIAGNOSTIC: Added {title[:30]} ({word_count} words)")

        # 4. Update History Log (keep last 200 entries)
        updated_history = (newly_sent_ids + sent_ids)[:200]
        with open(sent_log_path, "w") as f:
            json.dump(updated_history, f)

        # 5. Assemble HTML
        news_content = "".join(final_articles_html) if final_articles_html else "<li>no new long-form links found today.</li>"
        
        html_body = f"""
        <article class="h-entry">
            <header>
                <h1 class="p-name">liroh daily: {date_str} // {time_str} cst</h1>
            </header>
            <section class="e-content">
                <h2>01. weather discussion</h2>
                {weather_content}
            </section>
            <hr>
            <section class="e-content">
                <h2>02. the morning news</h2>
                <div class="nyt-text-section">
                    {nyt_content}
                </div>
            </section>
            <hr>
            <section class="e-content">
                <h2>03. daily links</h2>
                <ul>{news_content}</ul>
            </section>
        </article>
        """

        final_html = f"<!DOCTYPE html><html><head><meta charset='UTF-8'><link rel='stylesheet' href='style.css'></head><body>{html_body}</body></html>"

        if not os.path.exists("old_issues"):
            os.makedirs("old_issues")
        
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(final_html)
        
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