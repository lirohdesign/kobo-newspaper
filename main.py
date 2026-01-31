import requests
import os
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

def get_timestamp():
    cst_now = datetime.utcnow() - timedelta(hours=6)
    return cst_now.strftime("%d%b%y %H%M").lower()

def update_archive_index():
    if not os.path.exists("old_issues"):
        os.makedirs("old_issues")
    files = sorted([f for f in os.listdir("old_issues") if f.endswith(".html")], reverse=True)
    links = "".join([f'<li><a href="old_issues/{f}">{f.replace(".html", "")}</a></li>' for f in files])
    
    html = f"""<!DOCTYPE html><html>
<head><meta charset='UTF-8'><link rel='stylesheet' href='style.css'></head>
<body><h1>liroh archive</h1><nav><a href="index.html">back to home</a></nav><ul>{links}</ul></body></html>"""
    
    with open("archive.html", "w", encoding="utf-8") as f:
        f.write(html)

def collect_weather(ts):
    url = "https://forecast.weather.gov/product.php?site=iwx&issuedby=iwx&product=afd&format=ci&version=1&glossary=1"
    try:
        r = requests.get(url, timeout=20, headers={'User-Agent': 'Mozilla/5.0'})
        if '<pre class="glossaryProduct">' in r.text:
            start = r.text.find('<pre class="glossaryProduct">') + 29
            end = r.text.find('</pre>', start)
            raw = r.text[start:end].replace('&nbsp;', ' ').replace('&amp;', '&')
            clean_text = re.sub(r'<a [^>]*>(.*?)</a>', r'\1', raw)
            paragraphs = [p.replace('\n', ' ').strip() for p in clean_text.split('\n\n') if p.strip()]
            html_p = "".join([f'<p>{p}</p>' for p in paragraphs])
            
            weather_html = f"""<!DOCTYPE html><html>
<head><meta charset='UTF-8'><link rel='stylesheet' href='style.css'></head>
<body><h1>liroh weather {ts}</h1>{html_p}</body></html>"""
            
            with open("weather.html", "w", encoding="utf-8") as f:
                f.write(weather_html)
            return True
    except:
        pass
    return False

def collect_nyt(ts):
    path = "nyt_morning.html"
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw_html = f.read()
            clean = re.sub(r'<(style|script)[^>]*>.*?</\1>', '', raw_html, flags=re.DOTALL)
            content_blocks = re.findall(r'<(p|h3)[^>]*>(.*?)</\1>', clean, flags=re.DOTALL)
            processed = "".join([f'<{tag}>{re.sub(r"<[^>]+>", "", text).strip()}</{tag}>' for tag, text in content_blocks if len(text) > 40])
            
            nyt_html = f"""<!DOCTYPE html><html>
<head><meta charset='UTF-8'><link rel='stylesheet' href='style.css'></head>
<body><h1>liroh nyt morning {ts}</h1>{processed}</body></html>"""
            
            with open("nyt.html", "w", encoding="utf-8") as f:
                f.write(nyt_html)
            return True
        except:
            pass
    return False

def main():
    try:
        print("--- BUILD START ---")
        ts = get_timestamp()
        file_date = (datetime.utcnow() - timedelta(hours=6)).strftime("%Y-%m-%d")
        base_url = "https://lirohdesign.github.io/kobo-newspaper"
        
        # Ensure folders exist
        if not os.path.exists("old_issues"):
            os.makedirs("old_issues")

        # 1. Load History
        sent_log_path = "sent_articles.json"
        sent_ids = json.load(open(sent_log_path)) if os.path.exists(sent_log_path) else []

        # 2. Build local files
        weather_ready = collect_weather(ts)
        nyt_ready = collect_nyt(ts)

        # 3. Guardian Processing
        params = {'api-key': GUARDIAN_API_KEY, 'page-size': 50, 'type': 'article', 'section': '-sport,-football', 'show-fields': 'wordcount,trailText', 'order-by': 'newest'}
        r = requests.get("https://content.guardianapis.com/search", params=params, timeout=15)
        raw_pool = r.json().get('response', {}).get('results', [])
        
        front_page_items = []
        newly_sent_ids = []

        for article in raw_pool:
            if len(front_page_items) >= 10: break
            fields = article.get('fields', {})
            word_count = int(fields.get('wordcount', 0))
            if article.get('id') in sent_ids or word_count < 1000: continue

            article_url = article.get('webUrl')
            # Send individual article to instapaper
            add_to_instapaper(article_url)
            
            read_time = max(1, word_count // 200)
            item_html = f"""<div class='article-entry'>
<h3><a href='{article_url}'>{article.get('webTitle').lower()}</a></h3>
<p class='metadata'>{word_count} words // ~{read_time} min read</p>
<div class='trail-text'>{fields.get('trailText', '')}</div>
</div>"""
            front_page_items.append(item_html)
            newly_sent_ids.append(article.get('id'))

        # 4. Final Hub Assembly
        hub_html = f"""<!DOCTYPE html><html>
<head><meta charset='UTF-8'><link rel='stylesheet' href='style.css'></head>
<body>
<h1>liroh links {ts}</h1>
<nav><a href="weather.html">weather</a> | <a href="nyt.html">nyt briefing</a> | <a href="archive.html">archive</a></nav>
<section>{''.join(front_page_items)}</section>
</body></html>"""
        
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(hub_html)
            
        # Save a copy to the archive
        with open(f"old_issues/{file_date}.html", "w", encoding="utf-8") as f:
            f.write(hub_html)

        # 5. Send main packets to Instapaper
        if weather_ready: add_to_instapaper(f"{base_url}/weather.html")
        if nyt_ready: add_to_instapaper(f"{base_url}/nyt.html")
        add_to_instapaper(f"{base_url}/index.html")

        # 6. Cleanup & History
        update_archive_index()
        with open(sent_log_path, "w") as f:
            json.dump((newly_sent_ids + sent_ids)[:200], f)
        if os.path.exists("nyt_morning.html"): os.remove("nyt_morning.html")
        print("--- BUILD SUCCESSFUL ---")
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")

if __name__ == "__main__":
    main()