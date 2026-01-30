import requests
import os
import feedparser
import time
from datetime import datetime

# --- CONFIGURATION ---
INSTAPAPER_USER = os.environ.get("INSTAPAPER_USER")
INSTAPAPER_PASS = os.environ.get("INSTAPAPER_PASS")

def add_url_to_instapaper(url):
    """Adds news links directly to Instapaper with a unique sync tag."""
    if not INSTAPAPER_USER or not INSTAPAPER_PASS:
        print("  Error: Missing Credentials in Python Environment")
        return

    api_url = "https://www.instapaper.com/api/add"
    # Tagging the URL ensures Instapaper doesn't filter it as a duplicate
    unique_url = f"{url}?kobosync={int(time.time())}"
    
    # We use basic auth for the POST request
    try:
        r = requests.post(
            api_url, 
            auth=(INSTAPAPER_USER, INSTAPAPER_PASS),
            data={'url': unique_url},
            timeout=15
        )
        print(f"  [{r.status_code}] Direct Push: {unique_url}")
        time.sleep(3) 
    except Exception as e:
        print(f"  Connection Error: {e}")

def get_weather_afd():
    """Scrapes and reflows weather text to avoid 'skinny column' receipt syndrome."""
    url = "https://forecast.weather.gov/product.php?site=iwx&issuedby=iwx&product=afd&format=ci&version=1&glossary=1"
    try:
        r = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
        r.encoding = 'utf-8'
        start = r.text.find('<pre class="glossaryProduct">') + 29
        end = r.text.find('</pre>', start)
        raw_text = r.text[start:end].replace('&nbsp;', ' ').replace('&amp;', '&')
        
        # Remove hard line breaks but keep paragraphs
        lines = raw_text.splitlines()
        reflowed = ""
        for line in lines:
            stripped = line.strip()
            if not stripped:
                reflowed += "\n\n"
            else:
                reflowed += stripped + " "
        return reflowed
    except:
        return "Weather currently unavailable."

def main():
    # 1. DIRECT NEWS (Guardian & NYT)
    print("Sending News Direct to Instapaper...")
    feeds = {
        "Guardian": "https://www.theguardian.com/news/series/the-long-read/rss",
        "NYT": "https://rss.nytimes.com/services/xml/rss/nyt/TheMorning.xml"
    }
    for name, feed_url in feeds.items():
        try:
            resp = requests.get(feed_url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
            feed = feedparser.parse(resp.content)
            limit = 10 if name == "Guardian" else 2
            count = 0
            for entry in feed.entries:
                if count >= limit: break
                
                # Filter: Sports and Podcasts
                is_excluded = any(s in entry.link.lower() for s in ['sport', 'football', 'soccer', 'podcast', 'audio'])
                
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

    # Pre-formatting for HTML
    weather_html = f"<pre>{weather_content}</pre>"
    current_date = datetime.now().strftime("%B %d, %Y")

    # Replace placeholders in the template
    final_body = template.replace("{{date}}", current_date)
    final_body = final_body.replace("{{weather}}", weather_html)
    final_body = final_body.replace("{{news}}", "*Articles sent separately.*")
    final_body = final_body.replace("{{reddit}}", "*(Awaiting API Credentials)*")

    # 3. HTML Wrapper
    # Use a standard string (no 'f' at the start) to avoid CSS brace errors
    html_wrapper = """<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: sans-serif; line-height: 1.6; max-width: 800px; margin: 40px auto; padding: 20px; }
        pre { background: #f4f4f4; padding: 15px; white-space: pre-wrap; word-wrap: break-word; font-size: 16px; }
    </style>
</head>
<body>
    {content}
</body>
</html>"""

    # We plug the body in using .format()
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_wrapper.format(content=final_body))
    
    print("Success: index.html created.")

if __name__ == "__main__":
    main()
if __name__ == "__main__":
    main()