import requests
import os
import re
import json
import hashlib
from datetime import datetime

INSTAPAPER_USER = os.environ.get("INSTAPAPER_USER")
INSTAPAPER_PASS = os.environ.get("INSTAPAPER_PASS")
LOG_FILE = "sent_substack.json"
CUTOFF_DATE = datetime(2026, 1, 31)

# --- TEMP TEST SETTINGS ---
# Set this to True to force Sunday logic and ignore the 1/31 cutoff for one run
TEST_MODE = True 
# --------------------------

def get_hash(text):
    return hashlib.sha256(text.encode()).hexdigest()

def add_to_instapaper(url):
    print(f"DEBUG: Sending to Instapaper: {url}")
    api_url = "https://www.instapaper.com/api/add"
    try:
        r = requests.post(api_url, auth=(INSTAPAPER_USER, INSTAPAPER_PASS), data={'url': url}, timeout=15)
        return r.status_code in [200, 201]
    except:
        return False

def parse_substack_date(item_xml):
    date_match = re.search(r'<pubDate>(.*?)</pubDate>', item_xml)
    if date_match:
        try:
            return datetime.strptime(date_match.group(1)[:16], "%a, %d %b %Y")
        except: return None
    return None

def sync():
    # If TEST_MODE is on, we pretend it's Sunday
    is_sunday = True if TEST_MODE else (datetime.now().weekday() == 6)
    
    print(f"--- SYNC START (Sunday Mode: {is_sunday} | Test Mode: {TEST_MODE}) ---")
    
    raw_feeds = os.environ.get("PRIVATE_FEEDS")
    if not raw_feeds: return

    sent_hashes = json.load(open(LOG_FILE)) if os.path.exists(LOG_FILE) else []
    print(f"DEBUG: Current log has {len(sent_hashes)} hashes.")

    try:
        feeds = json.loads(raw_feeds)
        for url in feeds:
            proxied_url = f"https://api.allorigins.win/get?url={url}"
            r = requests.get(proxied_url, timeout=25)
            
            if r.status_code == 200:
                xml_content = r.json().get('contents', '')
                items = re.findall(r'<item>(.*?)</item>', xml_content, re.DOTALL)
                backlog_queue = []
                
                for item in items:
                    link_match = re.search(r'<link>(.*?)</link>', item)
                    if not link_match: continue
                    
                    link = link_match.group(1).strip()
                    link_hash = get_hash(link)
                    pub_date = parse_substack_date(item)
                    
                    print(f"DEBUG: Processing {link_hash[:8]}... (Date: {pub_date})")

                    # 1. NEW CONTENT (Always ignore cutoff in TEST_MODE to see a result)
                    if pub_date and (pub_date > CUTOFF_DATE or TEST_MODE):
                        if link_hash not in sent_hashes:
                            print(f"INFO: New article detected!")
                            if add_to_instapaper(link):
                                sent_hashes.append(link_hash)
                                if TEST_MODE: break # Stop after 1 in Test Mode
                    
                    # 2. BACKLOG
                    elif link_hash not in sent_hashes:
                        backlog_queue.append(link)

                # 3. SUNDAY BACKLOG
                if is_sunday and backlog_queue and not TEST_MODE:
                    for i in range(min(len(backlog_queue), 2)):
                        link = backlog_queue[i]
                        if add_to_instapaper(link):
                            sent_hashes.append(get_hash(link))
            else:
                print(f"ERROR: Proxy returned {r.status_code}")

        with open(LOG_FILE, "w") as f:
            json.dump(sent_hashes[-200:], f)
        print(f"DEBUG: Saved {len(sent_hashes)} total hashes to {LOG_FILE}")
            
    except Exception as e:
        print(f"ERROR: {e}")
    print("--- SYNC COMPLETE ---")

if __name__ == "__main__":
    sync()