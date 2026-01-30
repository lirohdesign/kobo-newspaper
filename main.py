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

    # 4. PRE-PROCESS the replacements to avoid f-string backslash errors
    # We turn the triple backticks into HTML <pre> tags here
    weather_html = weather_md.replace('```', '<pre>').replace('```', '</pre>')
    # We turn Markdown newlines into HTML breaks here
    news_html = news_md.replace('\n', '<br>')

    final_body = template.replace("{{date}}", datetime.now().strftime("%B %d, %Y"))
    final_body = final_body.replace("{{weather}}", weather_html)
    final_body = final_body.replace("{{news}}", news_html)
    final_body = final_body.replace("{{reddit}}", "*(Awaiting API Credentials)*")

    # 5. Save as HTML with a simple wrapper
    # Using a standard string (no 'f') avoids the CSS brace confusion
    html_wrapper = """
    <html>
    <head>
        <style>
            body { font-family: sans-serif; line-height: 1.6; max-width: 800px; margin: 40px auto; padding: 20px; }
            pre { background: #f4f4f4; padding: 15px; white-space: pre-wrap; word-wrap: break-word; font-size: 13px; }
            a { color: #0066cc; text-decoration: none; }
        </style>
    </head>
    <body>
        {content}
    </body>
    </html>
    """

    # This 'plugs' your final_body into the {content} placeholder safely
    final_html = html_wrapper.format(content=final_body)

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(final_html)
    print("Success: index.html created.")