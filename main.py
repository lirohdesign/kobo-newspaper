import requests
import os
import feedparser
import time
from datetime import datetime

# --- CONFIGURATION ---
INSTAPAPER_USER = os.environ.get("INSTAPAPER_USER")
INSTAPAPER_PASS = os.environ.get("INSTAPAPER_PASS")

def add_url_to_instapaper(url):
    """Adds a unique tag to ensure Instapaper accepts the link every time."""
    api_url = "https://www.instapaper.com/api/add"
    # Tagging the URL with a timestamp prevents Instapaper's duplicate filter from blocking it
    unique_url = f"{url}?kobosync={int(time.time())}"
    data = {'username': INSTAPAPER_USER, 'password': INSTAPAPER_PASS, 'url': unique_url}
    try:
        r = requests.post(api_url, data=data, timeout=15)
        print(f"  [{r.status_code}] Direct Push: {unique_url}")
        time.sleep(3) 
    except Exception as e:
        print(f"  Error: {e}")

def get_weather_afd():
    """Scrapes and REFLOWS text from IWX Weather Discussion."""
    url = "https://forecast.weather.gov/product.php?site=iwx&issuedby=iwx&product=afd&format=ci&version=1&glossary=1"
    try:
        r = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
        r.encoding = 'utf-8'
        start = r.text.find('<pre class="glossaryProduct">') + 29
        end = r.text.find('</pre>', start)
        raw_text = r.text[start:end].replace('&nbsp;', ' ').replace('&amp;', '&')
        
        # WEATHER REFLOW: This removes the hard line breaks so the text wraps naturally.
        # It replaces single newlines with spaces, but keeps double newlines as paragraphs.
        lines = raw_text.splitlines()
        reflowed_text = ""
        for line in lines:
            line = line.strip()
            if not line:
                reflowed_text += "\n\n" # Preserve paragraph breaks
            else:
                reflowed_text += line + " "
        return reflowed_text
    except:
        return "Weather unavailable today."

def main():
    # 1. DIRECT NEWS (Guardian & NYT)
    print("Sending News Direct...")
    feeds = {
        "Guardian": "https://www.theguardian.com/news/series/the-long-read/rss",
        "NYT": "https://rss.nytimes.com/services/xml/rss/nyt/TheMorning.xml"
    }
    for name, url in feeds.items():
        try:
            resp = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
            feed = feedparser.parse(resp.content)
            limit = 10 if name == "Guardian" else 2
            count = 0
            for entry in feed.entries:
                if count >= limit: break
                
                # UPDATED FILTER: Excludes sports and podcasts
                is_excluded = any(s in entry.link.lower() for s in ['sport', 'football', 'soccer', 'podcast'])
                
                if not is_excluded:
                    add_url_to_instapaper(entry.link)
                    count += 1
        except Exception as e:
            print(f"Feed error: {e}")

    # 2. NEWSLETTER CONTENT (Weather)
    print("Building Newsletter...")
    weather_content = get_weather_afd()
    
    with open("newsletter_template.md", "r") as f:
        template = f.read()

    current_date = datetime.now().strftime("%B %d, %Y")
    final_body = template.replace("{{date}}", current_date)
    final_body = final_body.replace("{{weather}}", weather_content)
    final_body = final_body.replace("{{news}}", "*Articles sent separately.*")
    final_body = final_body.replace("{{reddit}}", "*(Awaiting API Credentials)*")

    # 3. HTML Wrapper
    # We use white-space: pre-wrap to allow the reflowed weather to wrap on small screens.
    html_wrapper = """<!DOCTYPE html><html><head><style>
        body {{ font-family: -apple-system, sans-serif; line-height: 1.6; max-width: 800px; margin: 40px auto; padding: 20px; color: #111; }}
        pre {{ white-space: pre-wrap; word-wrap: break-word; font-family: inherit; font-size: 16px; }}
        a {{ color: #0066cc; text-decoration: none; }}
    </style></head><body>{content}</body></html>"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_wrapper.format(content=final_body))
    print("Success: index.html created.")

if __name__ == "__main__":
    main()