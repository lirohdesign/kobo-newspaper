import feedparser
import requests
import json
import os

# 1. YOUR MASTER CONFIG (Easy to edit as you grow)
# Tip: Use "-" in Reddit search to avoid "grungy" or "grind" content
CONFIG = [
    {"topic": "Aviation", "url": "https://www.reddit.com/r/aviation+drones+Tinywhoop/top/.rss?t=day", "limit": 3},
    {"topic": "Environment", "url": "https://www.reddit.com/r/climatechange+ecology/top/.rss?t=day", "limit": 3},
    {"topic": "Homesteading", "url": "https://www.reddit.com/r/homestead+homebuilding/top/.rss?t=day", "limit": 2}
]

# 2. INSTAPAPER CREDENTIALS (Stored securely in GitHub Secrets later)
INSTAPAPER_USER = os.environ.get("INSTAPAPER_USER")
INSTAPAPER_PASS = os.environ.get("INSTAPAPER_PASS")

def add_to_instapaper(link):
    """Sends a URL to your Instapaper account."""
    api_url = "https://www.instapaper.com/api/add"
    data = {
        'username': INSTAPAPER_USER,
        'password': INSTAPAPER_PASS,
        'url': link
    }
    try:
        r = requests.post(api_url, data=data)
        return r.status_code == 201
    except Exception as e:
        print(f"Error saving {link}: {e}")
        return False

def main():
    if not INSTAPAPER_USER or not INSTAPAPER_PASS:
        print("Error: Instapaper credentials not found in environment variables.")
        return

    for feed in CONFIG:
        print(f"Fetching {feed['topic']}...")
        data = feedparser.parse(feed['url'])
        
        for entry in data.entries[:feed['limit']]:
            print(f"  - Sending: {entry.title}")
            add_to_instapaper(entry.link)

if __name__ == "__main__":
    main()