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
            html_p = "".join([f'<p style="margin-bottom: 1em;">{p.replace("\n", " ").strip()}</p>' for p in paragraphs if p.strip()])
            
            # Create standalone page for Instapaper
            weather_html = f"<!DOCTYPE html><html><head><meta charset='UTF-8'></head><body><h1>Weather Discussion</h1>{html_p}</body></html>"
            with open("weather.html", "w", encoding="utf-8") as f:
                f.write(weather_html)
            return True
    except:
        pass
    return False

def collect_guardian_api():
    if not GUARDIAN_API_KEY: return []
    url = "https://content.guardianapis.com/search"
    params = {
        'api-key': GUARDIAN_API_KEY,
        'page-size': 50,
        'type': 'article',
        'section': '-sport,-football,-community,-crosswords',
        'tag': '-tone/minutebyminute,-type/audio',
        'show-fields': 'wordcount,trailText',
        'order-by': 'newest'
    }
    try:
        r = requests.get(url, params=params, timeout=15)
        data = r.json()
        with open("guardian_raw.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        return data.get('response', {}).get('results', [])
    except:
        return []

def collect_nyt():
    path = "nyt_morning.html"
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw_html = f.read()
            clean = re.sub(r'<(style|script)[^>]*>.*?</\1>', '', raw_html, flags=re.DOTALL)
            content_blocks = re.findall(r'<(p|h3)[^>]*>(.*?)</\1>', clean, flags=re.DOTALL)
            processed_content = "".join([f'<{tag}>{re.sub(r"<[^>]+>", "", text).strip()}</{tag}>' for tag, text in content_blocks if len(text) > 40])
            
            # Create standalone NYT page
            nyt_html = f"<!DOCTYPE html><html><head><meta charset='UTF-8'></head><body><h1>NYT Morning Briefing</h1>{processed_content}</body></html>"
            with open("nyt.html", "w", encoding="utf-8") as f:
                f.write(nyt_html)
            return True
        except:
            pass
    return False

def main():
    try:
        print("--- BUILD START ---")
        base_url = "https://lirohdesign.github.io/kobo-newspaper"
        
        # 1. Duplicate Prevention
        sent_log_path = "sent_articles.json"
        if os.path.exists(sent_log_path):
            with open(sent_log_path, "r") as f:
                sent_ids = json.load(f)
        else:
            sent_ids = []

        # 2. Weather & NYT Packets
        if collect_weather():
            add_to_instapaper(f"{base_url}/weather.html")
            print("DIAGNOSTIC: Weather packet sent.")

        if collect_nyt():
            add_to_instapaper(f"{base_url}/nyt.html")
            print("DIAGNOSTIC: NYT packet sent.")

        # 3. Guardian Processing
        raw_pool = collect_guardian_api()
        front_page_items = []
        newly_sent_ids = []

        for article in raw_pool:
            if len(front_page_items) >= 10: break
            
            a_id = article.get('id')
            fields = article.get('fields', {})
            word_count = int(fields.get('wordcount', 0))
            
            # 1,000 word threshold + check for duplicates
            if a_id in sent_ids or word_count < 1000: continue

            article_url = article.get('webUrl')
            # Send full article to Instapaper queue
            add_to_instapaper(article_url)
            
            # Add to Front Page summary
            read_time = max(1, word_count // 200)
            item_html = f"""
            <div style="margin-bottom: 2.5em; border-bottom: 1px solid #ccc; padding-bottom: 1em;">
                <h3 style="text-transform: lowercase;"><a href="{article_url}">{article.get('webTitle')}</a></h3>
                <p style="font-size: 0.9em; color: #666;">{word_count} words // ~{read_time} min read</p>
                <div style="margin-top: 0.5em;">{fields.get('trailText', '')}</div>
            </div>
            """
            front_page_items.append(item_html)
            newly_sent_ids.append(a_id)
            print(f"DIAGNOSTIC: Added {a_id[:30]}")

        # 4. Generate Front Page Packet
        front_page_html = f"""
        <!DOCTYPE html><html><head><meta charset='UTF-8'></head>
        <body style="font-family: serif; max-width: 600px; margin: auto; padding: 20px;">
            <h1 style="border-bottom: 2px solid #000;">Guardian Front Page</h1>
            <p style="font-style: italic;">{datetime.now().strftime('%B %d, %Y')}</p>
            {''.join(front_page_items) if front_page_items else '<p>No new long-form links today.</p>'}
        </body></html>
        """
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(front_page_html)
        
        # Send Front Page to Instapaper
        add_to_instapaper(f"{base_url}/index.html")
        print("DIAGNOSTIC: Front Page packet sent.")

        # 5. Persistent History Update
        with open(sent_log_path, "w") as f:
            json.dump((newly_sent_ids + sent_ids)[:200], f)

        print("--- BUILD SUCCESSFUL ---")
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")

if __name__ == "__main__":
    main()