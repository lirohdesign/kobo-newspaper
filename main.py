import requests
import os
import feedparser

# --- CONFIGURATION ---
INSTAPAPER_USER = os.environ.get("INSTAPAPER_USER")
INSTAPAPER_PASS = os.environ.get("INSTAPAPER_PASS")

def add_url_to_instapaper(url):
    """Sends a simple URL to Instapaper."""
    api_url = "https://www.instapaper.com/api/add"
    data = {
        'username': INSTAPAPER_USER,
        'password': INSTAPAPER_PASS,
        'url': url
    }
    r = requests.post(api_url, data=data)
    print(f"  [{r.status_code}] Sent URL: {url}")

def add_text_to_instapaper(title, body):
    """Sends raw text (Weather) to Instapaper."""
    api_url = "https://www.instapaper.com/api/add"
    data = {
        'username': INSTAPAPER_USER,
        'password': INSTAPAPER_PASS,
        'url': f"https://daily-paper.local/{title.replace(' ', '_')}", 
        'title': title,
        'content': body
    }
    requests.post(api_url, data=data)

def get_weather_afd():
    """Scrapes raw text from IWX Weather Discussion."""
    url = "https://forecast.weather.gov/product.php?site=iwx&issuedby=iwx&product=afd&format=ci&version=1&glossary=1"
    try:
        r = requests.get(url, timeout=15)
        start_tag = '<pre class="glossaryProduct">'
        start_idx = r.text.find(start_tag) + len(start_tag)
        end_idx = r.text.find('</pre>', start_idx)
        raw_text = r.text[start_idx:end_idx]
        return f"IWX WEATHER DISCUSSION\n\n{raw_text.replace('&nbsp;', ' ')}"
    except:
        return "Weather currently unavailable."

def main():
    if not INSTAPAPER_USER or not INSTAPAPER_PASS:
        print("Error: Missing Instapaper Credentials.")
        return

    # 1. WEATHER (Full Text)
    print("Syncing Weather...")
    add_text_to_instapaper("Daily Weather Briefing", get_weather_afd())

    # 2. NEWS (Guardian Deeply Read + NYT)
    print("Syncing News Feeds...")
    
    # Guardian Long Read and NYT The Morning
    feeds = {
        "NYT": "https://rss.nytimes.com/services/xml/rss/nyt/TheMorning.xml",
        "Guardian": "https://www.theguardian.com/news/series/the-long-read/rss"
    }

    for name, url in feeds.items():
        feed = feedparser.parse(url)
        count = 0
        for entry in feed.entries:
            if count >= 2: break # Limit to 2 per section
            
            # --- SPORTS FILTER ---
            # Skips if 'sport' is in the URL or title
            dislike_keywords = ['sport', 'football', 'soccer', 'cricket', 'rugby']
            if any(word in entry.link.lower() or word in entry.title.lower() for word in dislike_keywords):
                continue
                
            add_url_to_instapaper(entry.link)
            count += 1

    # 3. REDDIT (Placeholder)
    print("Reddit Sync: Blocked (Waiting for API Credentials)")

if __name__ == "__main__":
    main()