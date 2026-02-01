import requests
import os
import re
import json

INSTAPAPER_USER = os.environ.get("INSTAPAPER_USER")
INSTAPAPER_PASS = os.environ.get("INSTAPAPER_PASS")

def add_to_instapaper(url):
    print(f"DEBUG: Sending to Instapaper: {url}")
    api_url = "https://www.instapaper.com/api/add"
    try:
        r = requests.post(api_url, auth=(INSTAPAPER_USER, INSTAPAPER_PASS), data={'url': url}, timeout=15)
        print(f"DEBUG: Instapaper Response: {r.status_code}")
        return r.status_code == 200 or r.status_code == 201
    except:
        return False

def sync():
    print("--- PRIVATE RSS SYNC START ---")
    raw_feeds = os.environ.get("PRIVATE_FEEDS")
    if not raw_feeds:
        print("CRITICAL: No feeds found.")
        return

    # These are the exact headers used during the successful run
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
    }

    try:
        feeds = json.loads(raw_feeds)
        for url in feeds:
            print(f"INFO: Fetching RSS from: {url}")
            try:
                # We go back to the DIRECT Substack URL as we did in the success
                r = requests.get(url, timeout=20, headers=headers)
                print(f"INFO: HTTP Status: {r.status_code}")
                
                if r.status_code == 200:
                    # Exact regex protocol from the success run
                    all_links = re.findall(r'<item>.*?<link>(.*?)</link>', r.text, re.DOTALL)
                    article_links = [l.strip() for l in all_links if "/p/" in l]
                    
                    print(f"INFO: Found {len(article_links)} links.")
                    
                    if article_links:
                        newest = article_links[0]
                        success = add_to_instapaper(newest)
                        print(f"INFO: Final Result: {success}")
                else:
                    print(f"ERROR: Server returned {r.status_code}")
                    # Print the first bit of text to see if it's the "Just a moment" block
                    print(f"SAMPLE: {r.text[:100]}")
            except Exception as e:
                print(f"ERROR: Fetch failed: {e}")
    except Exception as e:
        print(f"ERROR: JSON Parsing: {e}")
    print("--- PRIVATE RSS SYNC END ---")

if __name__ == "__main__":
    sync()