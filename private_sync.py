import requests
import os
import re
import json
import hashlib
from datetime import datetime
import time

# --- SETTINGS ---
INSTAPAPER_USER = os.environ.get("INSTAPAPER_USER")
INSTAPAPER_PASS = os.environ.get("INSTAPAPER_PASS")
LOG_FILE = "sent_substack.json"
CUTOFF_DATE = datetime(2026, 1, 31)

# --- TEMP TEST LOGIC ---
# Set to True to ignore the cutoff and Sunday rule for one run. 
# Set to False for production.
TEST_MODE = False 
# -----------------------

def get_hash(text):
    """Generates a SHA-256 hash to keep private URLs out of logs."""
    return hashlib.sha256(text.encode()).hexdigest()

def add_to_instapaper(url):
    """Sends URL to Instapaper using the successful 200/201 protocol."""
    print(f"DEBUG: Attempting Instapaper add: {url}")
    api_url = "https://www.instapaper.com/api/add"
    try:
        r = requests.post(api_url, auth=(INSTAPAPER_USER, INSTAPAPER_PASS), data={'url': url}, timeout=15)
        print(f"DEBUG: Instapaper Response: {r.status_code}")
        return r.status_code in [200, 201]
    except Exception as e:
        print(f"DEBUG: Instapaper Error: {e}")
        return False

def parse_substack_date(item_xml):
    """Extracts the publication date from Substack RSS items."""
    date_match = re.search(r'<pubDate>(.*?)</pubDate>', item_xml)
    if date_match:
        try:
            # Parses standard RFC 822 format (e.g., Sat, 31 Jan 2026)
            return datetime.strptime(date_match.group(1)[:16], "%a, %d %b %Y")
        except:
            return None
    return None

def sync():
    # Detect Sunday (Day 6) or override with Test Mode
    is_sunday = True if TEST_MODE else (datetime.now().weekday() == 6)
    print(f"--- SUBSTACK SYNC START (Sunday Mode: {is_sunday} | Test Mode: {TEST_MODE}) ---")
    
    raw_feeds = os.environ.get("PRIVATE_FEEDS")
    if not raw_feeds:
        print("CRITICAL: PRIVATE_FEEDS environment variable is missing.")
        return

    # Initialize or Load the Hash Log
    if not os.path.exists(LOG_FILE):
        print("DEBUG: No local log file found. Starting fresh.")
        sent_hashes = []
    else:
        with open(LOG_FILE, "r") as f:
            sent_hashes = json.load(f)
    
    print(f"DEBUG: Initialized with {len(sent_hashes)} existing hashes.")

    try:
        feeds = json.loads(raw_feeds)
        for url in feeds:
            xml_content = ""
            # --- RESILIENCE: 3 ATTEMPTS WITH COOL-DOWN ---
            for attempt in range(3):
                try:
                    proxied_url = f"https://api.allorigins.win/get?url={url}"
                    print(f"INFO: Fetching via Proxy (Attempt {attempt + 1}): {url}")
                    r = requests.get(proxied_url, timeout=25)
                    if r.status_code == 200:
                        xml_content = r.json().get('contents', '')
                        if xml_content: break # Success!
                    else:
                        print(f"DEBUG: Proxy returned {r.status_code}")
                except Exception as e:
                    print(f"DEBUG: Attempt {attempt + 1} failed: {e}")
                
                if attempt < 2: # Don't sleep on the last attempt
                    time.sleep(2)
            
            if not xml_content:
                print(f"ERROR: Failed to fetch {url} after 3 attempts. Skipping.")
                continue
            # --------------------------------------------

            items = re.findall(r'<item>(.*?)</item>', xml_content, re.DOTALL)
            backlog_queue = []
            new_articles_found = 0
            
            for item in items:
                link_match = re.search(r'<link>(.*?)</link>', item)
                if not link_match: continue
                
                link = link_match.group(1).strip()
                link_hash = get_hash(link)
                pub_date = parse_substack_date(item)
                
                if pub_date and (pub_date > CUTOFF_DATE or TEST_MODE):
                    if link_hash not in sent_hashes:
                        print(f"INFO: New article detected: {link_hash[:8]}...")
                        if add_to_instapaper(link):
                            sent_hashes.append(link_hash)
                            new_articles_found += 1
                            if TEST_MODE: break
                
                elif link_hash not in sent_hashes:
                    backlog_queue.append(link)

            if is_sunday and backlog_queue and not TEST_MODE:
                print(f"INFO: Sunday mode active. Processing {min(len(backlog_queue), 2)} backlog items.")
                backlog_count = 0
                # Process the oldest items first (reverse the list)
                for link in reversed(backlog_queue):
                    if backlog_count >= 2: break
                    if add_to_instapaper(link):
                        sent_hashes.append(get_hash(link))
                        backlog_count += 1

        # Save the updated Hash Log
        with open(LOG_FILE, "w") as f:
            json.dump(sent_hashes[-200:], f)
        print(f"DEBUG: Hash log updated. Total count: {len(sent_hashes)}")
            
    except Exception as e:
        print(f"ERROR: Sync process failed: {e}")
    
    print("--- SYNC COMPLETE ---")