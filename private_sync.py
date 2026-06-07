import requests
import os
import re
import json
import hashlib
from datetime import datetime

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

    # Initialize or Load the Hash Log (Handles GitHub Cache behavior)
    if not os.path.exists(LOG_FILE):
        print("DEBUG: No local log file found. Starting fresh.")
        sent_hashes = []
    else:
        with open(LOG_FILE, "r") as f:
            sent_hashes = json.load(f)
    
    print(f"DEBUG: Initialized with {len(sent_hashes)} existing hashes.")

    try:
        feeds = json.loads(raw_feeds)
    except Exception as e:
        print(f"ERROR: Could not parse PRIVATE_FEEDS: {e}")
        feeds = []

    for url in feeds:
        # Each feed gets its own try/except: one feed's fetch failure shouldn't
        # abort the remaining feeds or skip the hash-log save below.
        try:
            print(f"INFO: Fetching feed {get_hash(url)[:8]}...")

            r = requests.get(url, timeout=25, headers={'User-Agent': 'Mozilla/5.0'})
            if r.status_code != 200:
                print(f"ERROR: Feed returned {r.status_code}")
                continue

            items = re.findall(r'<item>(.*?)</item>', r.text, re.DOTALL)
            print(f"DEBUG: Found {len(items)} item(s) in feed.")

            backlog_queue = []

            for item in items:
                link_match = re.search(r'<link>(.*?)</link>', item)
                if not link_match: continue

                link = link_match.group(1).strip()
                link_hash = get_hash(link)
                pub_date = parse_substack_date(item)

                # 1. NEW CONTENT (Post-Cutoff)
                # In TEST_MODE, we treat the first unseen item as "new" regardless of date
                if pub_date and (pub_date > CUTOFF_DATE or TEST_MODE):
                    if link_hash not in sent_hashes:
                        print(f"INFO: New article detected: {link_hash[:8]}...")
                        if add_to_instapaper(link):
                            sent_hashes.append(link_hash)
                            if TEST_MODE: break # Stop early in Test Mode

                # 2. BACKLOG (Pre-Cutoff)
                elif link_hash not in sent_hashes:
                    backlog_queue.append(link)

            # 3. SUNDAY BACKLOG (Limit 2, only if not in Test Mode)
            if is_sunday and backlog_queue and not TEST_MODE:
                print(f"INFO: Sunday mode active. Processing {min(len(backlog_queue), 2)} backlog items.")
                backlog_count = 0
                for link in backlog_queue:
                    if backlog_count >= 2: break
                    if add_to_instapaper(link):
                        sent_hashes.append(get_hash(link))
                        backlog_count += 1

        except Exception as e:
            print(f"ERROR: Failed to process feed: {e}")

    # Save the updated Hash Log (always — so progress survives a single feed's failure)
    with open(LOG_FILE, "w") as f:
        # Store the last 200 hashes to keep the cache light
        json.dump(sent_hashes[-200:], f)
    print(f"DEBUG: Hash log updated. Total count: {len(sent_hashes)}")

    print("--- SYNC COMPLETE ---")

if __name__ == "__main__":
    sync()