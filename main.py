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
    print(f"  Sent News Link: {url}")

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
        return f"IWX WEATHER DISCUSSION\n\n{r.text[start_idx:end_idx].replace('&nbsp;', ' ')}"
    except:
        return "Weather unavailable."

def main():
    if not INSTAPAPER_USER: return

    # 1. WEATHER (Full Text)
    print("Fetching Weather...")
    add_text_to_instapaper("Daily Weather Briefing", get_weather_afd())

    # 2. NEWS (Guardian & NYT)
    print("Fetching News...")
    feeds = {
        "NYT": "https://rss.nytimes.com/services/xml/rss/nyt/TheMorning.xml",
        "Guardian": "https://www.theguardian.com/news/series/the-long-read/rss"
    }
    for name, url in feeds.items():
        feed = feedparser.parse(url)
        count = 0
        for entry in feed.entries:
            if count >= 2: break
            # Sport Filter
            if any(word in entry.link.lower() for word in ['sport', 'football', 'soccer']):
                continue
            add_url_to_instapaper(entry.link)
            count += 1

    # 3. REDDIT (Placeholder - Add your PRAW logic here once approved)
    print("Reddit: Skipping (Waiting for API Credentials)")

if __name__ == "__main__":
    main()