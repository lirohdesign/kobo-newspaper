import requests
import os
import re
import json

INSTAPAPER_USER = os.environ.get("INSTAPAPER_USER")
INSTAPAPER_PASS = os.environ.get("INSTAPAPER_PASS")

def add_to_instapaper(url):
    print(f"DEBUG: Attempting Instapaper add: {url}")
    api_url = "https://www.instapaper.com/api/add"
    try:
        r = requests.post(api_url, auth=(INSTAPAPER_USER, INSTAPAPER_PASS), data={'url': url}, timeout=15)
        print(f"DEBUG: Instapaper Response: {r.status_code}")
        return r.status_code == 200 or r.status_code == 201
    except Exception as e:
        print(f"DEBUG: Instapaper Error: {e}")
        return False

def sync():
    print("--- PRIVATE RSS SYNC START ---")
    raw_feeds = os.environ.get("PRIVATE_FEEDS")
    if not raw_feeds:
        print("CRITICAL: No feeds found in environment.")
        return

    try:
        feeds = json.loads(raw_feeds)
        for url in feeds:
            # THIS IS YOUR SUCCESSFUL PROTOCOL:
            proxied_url = f"https://api.allorigins.win/get?url={url}"
            print(f"INFO: Fetching RSS via Proxy from: {url}")
            
            try:
                r = requests.get(proxied_url, timeout=25)
                if r.status_code == 200:
                    # AllOrigins wraps the XML in a JSON object under 'contents'
                    data = r.json()
                    xml_content = data.get('contents', '')
                    
                    # Exact regex from successful run
                    all_links = re.findall(r'<item>.*?<link>(.*?)</link>', xml_content, re.DOTALL)
                    article_links = [l.strip() for l in all_links if "/p/" in l]
                    
                    print(f"INFO: Found {len(article_links)} article links.")
                    
                    if article_links:
                        newest_post = article_links[0]
                        print(f"INFO: Sending newest post to Instapaper: {newest_post}")
                        success = add_to_instapaper(newest_post)
                        print(f"INFO: Success: {success}")
                    else:
                        print("WARNING: No links found in content.")
                else:
                    print(f"ERROR: Proxy returned {r.status_code}")
            except Exception as e:
                print(f"ERROR: Fetch failed: {e}")
                
    except Exception as e:
        print(f"ERROR: JSON Parsing failed: {e}")
    print("--- PRIVATE RSS SYNC END ---")

if __name__ == "__main__":
    sync()