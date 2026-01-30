import requests
import os
import feedparser
import time
from datetime import datetime

def get_weather_afd():
    url = "https://forecast.weather.gov/product.php?site=iwx&issuedby=iwx&product=afd&format=ci&version=1&glossary=1"
    try:
        r = requests.get(url, timeout=15)
        r.encoding = 'utf-8'
        start = r.text.find('<pre class="glossaryProduct">') + 29
        end = r.text.find('</pre>', start)
        raw_text = r.text[start:end].replace('&nbsp;', ' ').replace('&amp;', '&')
        # Wrap in triple backticks for Markdown monospace
        return f"```\n{raw_text}\n```"
    except:
        return "Weather unavailable today."

def main():
    # 1. Gather Weather
    weather_md = get_weather_afd()

    # 2. Gather News
    news_md = ""
    feeds = {
        "Guardian": "https://www.theguardian.com/news/series/the-long-read/rss",
        "NYT": "https://rss.nytimes.com/services/xml/rss/nyt/TheMorning.xml"
    }
    for name, url in feeds.items():
        feed = feedparser.parse(url)
        limit = 10 if name == "Guardian" else 2
        for entry in feed.entries[:limit]:
            if not any(s in entry.link.lower() for s in ['sport', 'football', 'soccer']):
                news_md += f"* [{entry.title}]({entry.link})\n"

    # 3. Handle Template
    with open("newsletter_template.md", "r") as f:
        template = f.read()

    # Fill in the placeholders
    final_content = template.replace("{{date}}", datetime.now().strftime("%B %d, %Y"))
    final_content = final_content.replace("{{weather}}", weather_md)
    final_content = final_content.replace("{{news}}", news_md)
    final_content = final_content.replace("{{reddit}}", "*(Awaiting API Credentials)*")

    # 4. Save as HTML for GitHub Pages
    # We'll use a simple wrapper to make the Markdown look like a webpage
    html_wrapper = f"""
    <html>
    <head>
        <style>
            body {{ font-family: -apple-system, sans-serif; line-height: 1.6; max-width: 800px; margin: 40px auto; padding: 0 20px; }}
            pre {{ background: #f4f4f4; padding: 15px; overflow-x: auto; font-size: 13px; }}
            a {{ color: #0066cc; text-decoration: none; }}
            hr {{ border: 0; border-top: 1px solid #eee; margin: 40px 0; }}
        </style>
    </head>
    <body>
        {final_content.replace('```', '<pre>').replace('```', '</pre>').replace('\n', '<br>')}
    </body>
    </html>
    """

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_wrapper)