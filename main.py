import requests
import os
import feedparser
import time
import re
from datetime import datetime, timedelta

# --- settings ---
INSTAPAPER_USER = os.environ.get("INSTAPAPER_USER")
INSTAPAPER_PASS = os.environ.get("INSTAPAPER_PASS")

# --- module 1: collection ---
def collect_weather():
    url = "https://forecast.weather.gov/product.php?site=iwx&issuedby=iwx&product=afd&format=ci&version=1&glossary=1"
    try:
        r = requests.get(url, timeout=20, headers={'User-Agent': 'Mozilla/5.0'})
        r.encoding = 'utf-8'
        if '<pre class="glossaryProduct">' in r.text:
            start = r.text.find('<pre class="glossaryProduct">') + 29
            end = r.text.find('</pre>', start)
            raw = r.text[start:end].replace('&nbsp;', ' ').replace('&amp;', '&')
            
            # Remove glossary hyperlinks
            clean_text = re.sub(r'<a [^>]*>(.*?)</a>', r'\1', raw)
            
            # Split into sections
            paragraphs = clean_text.split('\n\n')
            html_paragraphs = []
            
            for p in paragraphs:
                if p.strip():
                    # PERFORM THE REPLACE OUTSIDE THE F-STRING
                    clean_p = p.replace('\n', ' ').strip()
                    html_paragraphs.append(f'<p style="margin-bottom: 1em;">{clean_p}</p>')
            
            return "".join(html_paragraphs)
    except Exception as e:
        print(f"Weather error: {e}")
        return "<p>weather unavailable.</p>"

def collect_guardian_links():
    links_html = []
    feed_url = "https://www.theguardian.com/news/series/the-long-read/rss"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    
    try:
        print(f"--- DIAGNOSTIC START: News Collection ---")
        resp = requests.get(feed_url, timeout=15, headers=headers)
        feed = feedparser.parse(resp.content)
        print(f"DEBUG: Feed retrieved. Status: {resp.status_code}. Total entries in RSS: {len(feed.entries)}")
        
        count = 0
        for i, entry in enumerate(feed.entries):
            if count >= 10: 
                print(f"DEBUG: reached 10 article limit at RSS index {i}")
                break
            
            link_low = entry.link.lower()
            if not any(x in link_low for x in ['/podcasts/', '/video/', '/sport/', '/football/']):
                # 1. Trigger Instapaper sync
                add_to_instapaper(entry.link)
                
                # 2. Build the HTML string for this specific link
                captured_title = entry.title.lower()
                list_item = f'<li><a href="{entry.link}">{captured_title}</a></li>'
                
                # 3. Append to the list
                links_html.append(list_item)
                
                # 4. Diagnostic print
                count += 1
                print(f"DEBUG: [{count}/10] Appended to list: {captured_title[:40]}")
                time.sleep(1)
            else:
                print(f"DEBUG: Skipping filtered item: {link_low[:50]}...")

        # FINAL CHECK before returning
        result_string = "".join(links_html)
        print(f"DEBUG: Final joined string length: {len(result_string)} characters.")
        print(f"--- DIAGNOSTIC END: News Collection ---")
        
        return result_string
        
    except Exception as e:
        print(f"ERROR in collect_guardian_links: {e}")
        return "<li>guardian sync error.</li>"

def add_to_instapaper(url):
    api_url = "https://www.instapaper.com/api/add"
    try:
        r = requests.post(api_url, auth=(INSTAPAPER_USER, INSTAPAPER_PASS), 
                         data={'url': url}, timeout=15)
        return r.status_code == 200
    except:
        return False

# --- module 2: build ---
def main():
    # step A: handle time
    cst_now = datetime.utcnow() - timedelta(hours=6)
    date_str = cst_now.strftime("%b %d, %y").lower()
    time_str = cst_now.strftime("%I:%M %p").lower()
    
    # step B: collect data (the "step before build")
    print("starting collection...")
    weather_content = collect_weather()
    news_content = collect_guardian_links()
    
    # step C: assemble newsletter only AFTER data is in hand
    # wrap the core content in a way Instapaper respects
    html_body = f"""
    <header>
        <h1 class="masthead">liroh daily</h1>
        <h3 style="font-weight: normal; text-transform: lowercase;">
            <time>{date_str} // {time_str} cst</time>
        </h3>
    </header>
    
    <article id="main-content">
        <section>
            <h2>weather discussion</h2>
            <div class="weather-block">{weather_content}</div>
        </section>
        
        <section>
            <h2>daily links</h2>
            <ul>{news_content}</ul>
        </section>
    </article>
    """
    
    final_html = f"<!DOCTYPE html><html><head><meta charset='UTF-8'><link rel='stylesheet' href='style.css'></head><body>{html_body}</body></html>"
    

    with open("index.html", "w", encoding="utf-8") as f: 
        f.write(final_html)
    
    file_date = cst_now.strftime("%Y-%m-%d")
    if not os.path.exists("old_issues"): 
        os.makedirs("old_issues")
        
    with open(f"old_issues/{file_date}.html", "w", encoding="utf-8") as f:
        f.write(final_html.replace('href="style.css"', 'href="../style.css"'))
    
    print("build successful.")