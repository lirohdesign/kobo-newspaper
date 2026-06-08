import requests
import os
import re
import json
from datetime import datetime, timedelta

# --- settings ---
INSTAPAPER_USER = os.environ.get("INSTAPAPER_USER")
INSTAPAPER_PASS = os.environ.get("INSTAPAPER_PASS")
GUARDIAN_API_KEY = os.environ.get("GUARDIAN_API_KEY")

# Set to False to stop sending Guardian articles to Instapaper (links still
# show up in the daily build either way). Flip back to True when reading more.
SEND_GUARDIAN_TO_INSTAPAPER = False

# Now stored in your persistent archive folder
SENT_LOG_PATH = "old_issues/sent_articles.json"

def add_to_instapaper(url):
    print(f"DEBUG: Attempting Instapaper add: {url}")
    api_url = "https://www.instapaper.com/api/add"
    try:
        r = requests.post(api_url, auth=(INSTAPAPER_USER, INSTAPAPER_PASS), data={'url': url}, timeout=15)
        print(f"DEBUG: Instapaper Response: {r.status_code}")
        return r.status_code == 200
    except Exception as e:
        print(f"DEBUG: Instapaper Error: {e}")
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
    print("DEBUG: Collecting Weather...")
    url = "https://forecast.weather.gov/product.php?site=iwx&issuedby=iwx&product=afd&format=ci&version=1&glossary=1"
    try:
        r = requests.get(url, timeout=20, headers={'User-Agent': 'Mozilla/5.0'})
        if '<pre class="glossaryProduct">' in r.text:
            start = r.text.find('<pre class="glossaryProduct">') + 29
            end = r.text.find('</pre>', start)
            raw = r.text[start:end].replace('&nbsp;', ' ').replace('&amp;', '&')
            clean_text = re.sub(r'<a [^>]*>(.*?)</a>', r'\1', raw)
            paragraphs = [p.replace('\n', ' ').strip() for p in clean_text.split('\n\n') if p.strip()]
            content = "".join([f'<p>{p}</p>' for p in paragraphs])
            
            html = f"""<!DOCTYPE html><html><head><meta charset='UTF-8'><link rel='stylesheet' href='style.css'></head>
            <body><h1>liroh weather {ts}</h1>{content}</body></html>"""
            with open("weather.html", "w", encoding="utf-8") as f:
                f.write(html)
            return content
    except Exception as e:
        print(f"DEBUG: Weather Error: {e}")
    return ""

def collect_nyt(ts):
    print("DEBUG: Collecting NYT Briefing...")
    path = "nyt_morning.html" 
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw_html = f.read()
            clean = re.sub(r'<(style|script)[^>]*>.*?</\1>', '', raw_html, flags=re.DOTALL)
            content_blocks = re.findall(r'<(p|h2|h3|li)[^>]*>(.*?)</\1>', clean, flags=re.DOTALL)
            content = "".join([f'<{tag}>{re.sub(r"<[^>]+>", "", text).strip()}</{tag}>' for tag, text in content_blocks if tag in ('h2', 'h3') or len(text) > 40])
            
            html = f"""<!DOCTYPE html><html><head><meta charset='UTF-8'><link rel='stylesheet' href='style.css'></head>
            <body><h1>liroh nyt morning {ts}</h1>{content}</body></html>"""
            with open("nyt.html", "w", encoding="utf-8") as f:
                f.write(html)
            return content
        except Exception as e:
            print(f"DEBUG: NYT Error: {e}")
    return ""

def main():
    try:
        print("--- BUILD START ---")
        ts = get_timestamp()
        file_date = (datetime.utcnow() - timedelta(hours=6)).strftime("%Y-%m-%d")
        base_url = "https://lirohdesign.github.io/kobo-newspaper"
        
        # Ensure the folder exists before any logic runs
        if not os.path.exists("old_issues"):
            os.makedirs("old_issues")
            
        weather_content = collect_weather(ts)
        nyt_content = collect_nyt(ts)

        # Load existing Sent IDs from the archive folder
        try:
            sent_ids = json.load(open(SENT_LOG_PATH)) if os.path.exists(SENT_LOG_PATH) else []
        except:
            sent_ids = []
        
        params = {'api-key': GUARDIAN_API_KEY, 'page-size': 50, 'type': 'article', 'section': '-sport,-football', 'show-fields': 'wordcount,trailText', 'order-by': 'newest'}
        r = requests.get("https://content.guardianapis.com/search", params=params, timeout=15)
        raw_pool = r.json().get('response', {}).get('results', [])
        
        links_list_html = []
        newly_sent_ids = []

        for article in raw_pool:
            if len(links_list_html) >= 10: break
            fields = article.get('fields', {})
            word_count = int(fields.get('wordcount', 0))
            if article.get('id') in sent_ids or word_count < 1000: continue

            article_url = article.get('webUrl')
            if SEND_GUARDIAN_TO_INSTAPAPER:
                add_to_instapaper(article_url)

            read_time = max(1, word_count // 200)
            item = f"""<div class='article-entry'>
            <h3><a href='{article_url}'>{article.get('webTitle')}</a></h3>
            <p class='metadata'>{word_count} words // ~{read_time} min read</p>
            <div class='trail-text'>{fields.get('trailText', '')}</div>
            </div>"""
            links_list_html.append(item)
            newly_sent_ids.append(article.get('id'))

        links_final_content = "".join(links_list_html)
        
        with open("links.html", "w", encoding="utf-8") as f:
            f.write(f"<!DOCTYPE html><html><head><meta charset='UTF-8'><link rel='stylesheet' href='style.css'></head><body><h1>liroh links {ts}</h1>{links_final_content}</body></html>")

        # MASTER index.html
        master_index = f"""<!DOCTYPE html><html><head><meta charset='UTF-8'><link rel='stylesheet' href='style.css'></head>
<body><h1>liroh daily {ts}</h1><nav><a href="weather.html">weather</a> | <a href="nyt.html">nyt</a> | <a href="links.html">links</a> | <a href="archive.html">archive</a></nav>
<section><h2>01. weather</h2>{weather_content if weather_content else '<p>unavailable</p>'}</section><hr>
<section><h2>02. nyt briefing</h2>{nyt_content if nyt_content else '<p>unavailable</p>'}</section><hr>
<section><h2>03. daily links</h2>{links_final_content}</section></body></html>"""
        
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(master_index)
        
        with open(f"old_issues/{file_date}.html", "w", encoding="utf-8") as f:
            f.write(master_index.replace("style.css", "../style.css"))

        # Instapaper Sends for local pages
        if weather_content: add_to_instapaper(f"{base_url}/weather.html?v={ts}")
        if nyt_content: add_to_instapaper(f"{base_url}/nyt.html?v={ts}")
        add_to_instapaper(f"{base_url}/links.html?v={ts}")

        update_archive_index()
        
        # Save updated log back to the archive folder
        with open(SENT_LOG_PATH, "w") as f:
            json.dump((newly_sent_ids + sent_ids)[:200], f)
            
        print("--- BUILD SUCCESSFUL ---")
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")

if __name__ == "__main__":
    main()