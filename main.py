import requests
import os
import json

# --- CONFIGURATION ---
# These must be set in your GitHub Secrets
INSTAPAPER_USER = os.environ.get("INSTAPAPER_USER")
INSTAPAPER_PASS = os.environ.get("INSTAPAPER_PASS")

# Once Reddit approves your app, add these to GitHub Secrets
REDDIT_ID = os.environ.get("REDDIT_ID")
REDDIT_SECRET = os.environ.get("REDDIT_SECRET")

def add_to_instapaper(title, body):
    """
    Sends raw text directly to Instapaper. 
    Using 'content' ensures your indents and line breaks are preserved.
    """
    api_url = "https://www.instapaper.com/api/add"
    data = {
        'username': INSTAPAPER_USER,
        'password': INSTAPAPER_PASS,
        'url': f"https://daily-paper.local/{title.replace(' ', '_')}", 
        'title': title,
        'content': body
    }
    try:
        r = requests.post(api_url, data=data, timeout=15)
        print(f"  [{r.status_code}] Sent: {title}")
    except Exception as e:
        print(f"  Error sending to Instapaper: {e}")

def get_weather_afd():
    """Scrapes raw fixed-width text from the IWX Weather Discussion."""
    url = "https://forecast.weather.gov/product.php?site=iwx&issuedby=iwx&product=afd&format=ci&version=1&glossary=1"
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        
        start_tag = '<pre class="glossaryProduct">'
        end_tag = '</pre>'
        start_idx = r.text.find(start_tag) + len(start_tag)
        end_idx = r.text.find(end_tag, start_idx)
        
        if start_idx == -1 or end_idx == -1:
            return "Could not find weather text block."
            
        raw_text = r.text[start_idx:end_idx]
        clean_text = raw_text.replace("&nbsp;", " ").replace("&amp;", "&")
        return f"IWX AREA FORECAST DISCUSSION\n\n{clean_text}"
    except Exception as e:
        return f"Weather Scrape Failed: {e}"

def main():
    if not INSTAPAPER_USER or not INSTAPAPER_PASS:
        print("Error: Missing Instapaper Credentials in Environment Variables.")
        return

    # --- 1. WEATHER SECTION ---
    print("Syncing Weather...")
    weather_report = get_weather_afd()
    add_to_instapaper("Daily Weather Briefing", weather_report)

    # --- 2. REDDIT SECTION (PLACEHOLDER) ---
    # This block is where the PRAW scraper will be inserted.
    # Logic: 
    # 1. Initialize PRAW with REDDIT_ID and REDDIT_SECRET.
    # 2. Iterate through your subreddit list (+ string).
    # 3. Use format_barebones() to create text with 4-space indents for comments.
    # 4. Push each thread to add_to_instapaper().
    
    print("Reddit Sync: Blocked (Waiting for API Approval/Credentials)")
    
    """
    FUTURE REDDIT CODE PREVIEW:
    import praw
    reddit = praw.Reddit(client_id=REDDIT_ID, client_secret=REDDIT_SECRET, user_agent="KoboBot")
    multi_sub = "aviation+meteorology+homestead+..."
    for post in reddit.subreddit(multi_sub).top(time_filter='day', limit=5):
        # Barebones formatting logic goes here
        # clean_text = format_barebones(post)
        # add_to_instapaper(post.title, clean_text)
    """

if __name__ == "__main__":
    main()