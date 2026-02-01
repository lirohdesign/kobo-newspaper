import requests
import os
import re
import json

INSTAPAPER_USER = os.environ.get("INSTAPAPER_USER")
INSTAPAPER_PASS = os.environ.get("INSTAPAPER_PASS")

def add_to_instapaper(url):
    api_url = "https://www.instapaper.com/api/add"
    try:
        r = requests.post(api_url, auth=(INSTAPAPER_USER, INSTAPAPER_PASS), data={'url': url}, timeout=15)
        return r.status_code == 200
    except:
        return False

def sync():
    print("--- SUBSTACK SYNC START ---")
    raw_feeds = os.environ.get("PRIVATE_FEEDS")
    if not raw_feeds:
        print("Error: No feeds found.")
        return

    feeds = json.loads(raw_feeds)
    for url in feeds:
        # Convert to RSSHub to bypass Substack's 403 block
        subdomain = url.split("//")[1].split(".")[0]
        fetch_url = f"https://rsshub.app/substack/posts/{subdomain}"
        
        print(f"Fetching: {fetch_url}")
        try:
            r = requests.get(fetch_url, timeout=25)
            if r.status_code == 200:
                all_links = re.findall(r'<link>(.*?)</link>', r.text)
                article_links = [l.strip() for l in all_links if "/p/" in l]
                if article_links:
                    print(f"Success! Sending: {article_links[0]}")
                    add_to_instapaper(article_links[0])
            else:
                print(f"Failed with status: {r.status_code}")
        except Exception as e:
            print(f"Error: {e}")
    print("--- SUBSTACK SYNC END ---")

if __name__ == "__main__":
    sync()