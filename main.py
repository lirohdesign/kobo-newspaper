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
    print("DEBUG: Updating Archive Index...")
    if not os.path.exists("old_issues"):
        os.makedirs("old_issues")
    files = sorted([f for f in os.listdir("old_issues") if f.endswith(".html")], reverse=True)
    links = "".join([f'<li><a href="old_issues/{f}">{f.replace(".html", "")}</a></li>' for f in files])
    
    html = f"""<!DOCTYPE html><html>
<head><meta charset='UTF-8'><link rel='stylesheet' href='style.css'></head>
<body><h1>liroh archive</h1><nav><a href="index.html">back to home</a></nav><ul>{links}</ul></body></html>"""
    
    with open("archive.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"DEBUG: Archive index updated with {len(files)} issues.")

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
            print("DEBUG: Weather successfully collected.")
            return content
    except Exception as e:
        print(f"DEBUG: Weather Error: {e}")
    return ""

def collect_nyt(ts):
    print("DEBUG: Collecting NYT Morning Briefing...")
    path = "nyt_morning.html" 
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw_html = f.read()
            clean = re.sub(r'<(style|script)[^>]*>.*?</\1>', '', raw_html, flags=re.DOTALL)
            content_blocks = re.findall(r'<(p|h3)[^>]*>(.*?)</\1>', clean, flags=re.DOTALL)
            content = "".join([f'<{tag}>{re.sub(r"<[^>]+>", "", text).strip()}</{tag}>' for tag, text in content_blocks if len(text) > 40])
            
            html = f"""<!DOCTYPE html><html><head><meta charset='UTF-8'><link rel='stylesheet' href='style.css'></head>
            <body><h1>liroh nyt morning {ts}</h1>{content}</body></html>"""
            with open("nyt.html", "w", encoding="utf-8") as f:
                f.write(html)
            print("DEBUG: NYT Morning briefing processed.")
            return content
        except Exception as e:
            print(f"DEBUG: NYT Processing Error: {e}")
    else:
        print("DEBUG: NYT local file (nyt_morning.html) not found.")
    return ""

def sync_private_feeds():
    print("--- PRIVATE RSS DEBUG START ---")
    raw_feeds = os.environ.get("PRIVATE_FEEDS")
    if not raw_feeds:
        print("CRITICAL: PRIVATE_FEEDS environment variable is EMPTY or MISSING.")
        return
    
    try:
        feeds = json.loads(raw_feeds)
        print(f"INFO: Successfully parsed {len(feeds)} feed(s).")
    except Exception as e:
        print(f"ERROR: JSON Parsing failed: {e}")
        return

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
    }

    for url in feeds:
        proxied_url = f"https://api.allorigins.win/get?url={url}"
        print(f"INFO: Fetching RSS via Proxy from: {url}")
        try:
            r = requests.get(proxied_url, timeout=20)
            if r.status_code == 200:
                data = r.json()
                xml_content = data.get('contents', '')
                all_links = re.findall(r'<item>.*?<link>(.*?)</link>', xml_content, re.DOTALL)
                article_links = [l.strip() for l in all_links if "/p/" in l]
                print(f"INFO: Found {len(article_links)} article links in private feed.")
                
                if article_links:
                    newest_post = article_links[0]
                    print(f"INFO: Sending newest private post: {newest_post}")
                    add_to_instapaper(newest_post)
            else:
                print(f"ERROR: Proxy returned {r.status_code}")
        except Exception as e:
            print(f"ERROR: Private feed loop failed: {e}")
    print("--- PRIVATE RSS DEBUG END ---")

def main():
    try:
        print("--- BUILD START ---")
        ts = get_timestamp()
        file_date = (datetime.utcnow() - timedelta(hours=6)).strftime("%Y-%m-%d")
        base_url = "https://lirohdesign.github.io/kobo-newspaper"
        
        if not os.path.exists("old_issues"): os.makedirs("old_issues")

        weather_content = collect_weather(ts)
        nyt_content = collect_nyt(ts)

        # Guardian Processing
        sent_log_path = "sent_articles.json"
        sent_ids = []
        if os.path.exists(sent_log_path):
            try:
                with open(sent_log_path, "r") as f:
                    sent_ids = json.load(f)
                print(f"DEBUG: Loaded {len(sent_ids)} IDs from log.")
            except Exception as e:
                print(f"DEBUG: Log file load error (starting fresh): {e}")

        print("DEBUG: Fetching Guardian pool...")
        params = {'api-key': GUARDIAN_API_KEY, 'page-size': 50, 'type': 'article', 'section': '-sport,-football', 'show-fields': 'wordcount,trailText', 'order-by': 'newest'}
        r = requests.get("https://content.guardianapis.com/search", params=params, timeout=15)
        raw_pool = r.json().get('response', {}).get('results', [])
        print(f"DEBUG: Guardian Pool contains {len(raw_pool)} articles.")
        
        links_list_html = []
        newly_sent_ids = []

        for article in raw_pool:
            if len(links_list_html) >= 10: break
            fields = article.get('fields', {})
            word_count = int(fields.get('wordcount', 0))
            if article.get('id') in sent_ids or word_count < 1000: continue

            article_url = article.get('webUrl')
            print(f"DEBUG: New article found: {article.get('webTitle')}")
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
        print(f"DEBUG: Final Guardian links list contains {len(links_list_html)} items.")
        
        # links.html for Instapaper
        links_page = f"""<!DOCTYPE html><html><head><meta charset='UTF-8'><link rel='stylesheet' href='style.css'></head>
        <body><h1>liroh links {ts}</h1>{links_final_content}</body></html>"""
        with open("links.html", "w", encoding="utf-8") as f:
            f.write(links_page)

        # index.html MASTER EDITION
        master_index = f"""<!DOCTYPE html><html>
<head><meta charset='UTF-8'><link rel='stylesheet' href='style.css'></head>
<body>
    <h1>liroh daily {ts}</h1>
    <nav><a href="weather.html">weather</a> | <a href="nyt.html">nyt</a> | <a href="links.html">links</a> | <a href="archive.html">archive</a></nav>
    <section><h2>01. weather</h2>{weather_content if weather_content else '<p>unavailable</p>'}</section>
    <hr>
    <section><h2>02. nyt briefing</h2>{nyt_content if nyt_content else '<p>unavailable</p>'}</section>
    <hr>
    <section><h2>03. daily links</h2>{links_final_content}</section>
</body></html>"""
        
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(master_index)
        
        with open(f"old_issues/{file_date}.html", "w", encoding="utf-8") as f:
            f.write(master_index.replace("style.css", "../style.css"))

        # Instapaper Sends for local files
        print("DEBUG: Sending local file links to Instapaper...")
        if weather_content: 
            add_to_instapaper(f"{base_url}/weather.html?v={ts}")
        if nyt_content: 
            add_to_instapaper(f"{base_url}/nyt.html?v={ts}")
        add_to_instapaper(f"{base_url}/links.html?v={ts}")

        update_archive_index()
        sync_private_feeds()
        
        with open(sent_log_path, "w") as f:
            json.dump((newly_sent_ids + sent_ids)[:200], f)
        print("DEBUG: Article log saved.")
            
        print("--- BUILD SUCCESSFUL ---")
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")

if __name__ == "__main__":
    main()