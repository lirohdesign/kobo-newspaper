import requests
import os
import re
import json
import hashlib
from datetime import datetime, timedelta

# --- settings ---
INSTAPAPER_USER = os.environ.get("INSTAPAPER_USER")
INSTAPAPER_PASS = os.environ.get("INSTAPAPER_PASS")
GUARDIAN_API_KEY = os.environ.get("GUARDIAN_API_KEY")
PRIVATE_FEEDS = os.environ.get("PRIVATE_FEEDS", "[]")

def get_hash(text):
    return hashlib.sha256(text.encode()).hexdigest()

def add_to_instapaper(url):
    api_url = "https://www.instapaper.com/api/add"
    try:
        requests.post(api_url, auth=(INSTAPAPER_USER, INSTAPAPER_PASS), data={'url': url}, timeout=15)
        return True
    except:
        return False

def sync_private_feeds(sent_ids):
    try:
        feeds = json.loads(PRIVATE_FEEDS)
        newly_sent_hashes = []
        
        # --- TEST SETTINGS ---
        FORCE_TEST = True  # Set to False after you confirm Substack works!
        TEST_LIMIT = 2
        
        for url in feeds:
            try:
                r = requests.get(url, timeout=15)
                # re.DOTALL handles the multi-line XML structure of RSS
                all_links = re.findall(r'<item>.*?<link>(.*?)</link>', r.text, re.DOTALL)
                article_links = [l.strip() for l in all_links if "/p/" in l]
                
                if FORCE_TEST:
                    to_send = article_links[:TEST_LIMIT]
                else:
                    to_send = [l for l in article_links if get_hash(l) not in sent_ids]
                    to_send.reverse()
                
                is_sunday = datetime.utcnow().weekday() == 6
                daily_limit = TEST_LIMIT if FORCE_TEST else (2 if is_sunday else 1)

                for article_url in to_send[:daily_limit]:
                    if add_to_instapaper(article_url):
                        newly_sent_hashes.append(get_hash(article_url))
                        print(f"Private Sync: Sent {article_url[:40]}")
            except Exception as e:
                print(f"Feed error: {e}")
        return newly_sent_hashes
    except: return []

def main():
    try:
        print("--- BUILD START ---")
        ts = (datetime.utcnow() - timedelta(hours=6)).strftime("%d%b%y %H%M").lower()
        file_date = (datetime.utcnow() - timedelta(hours=6)).strftime("%Y-%m-%d")
        
        # Bulletproof Log Loading from root (main branch)
        sent_log_path = "sent_articles.json"
        sent_ids = []
        if os.path.exists(sent_log_path):
            try:
                with open(sent_log_path, "r") as f:
                    sent_ids = json.load(f)
            except: sent_ids = []

        # Guardian Fetch
        params = {'api-key': GUARDIAN_API_KEY, 'page-size': 50, 'show-fields': 'wordcount,trailText', 'order-by': 'newest'}
        r = requests.get("https://content.guardianapis.com/search", params=params, timeout=15)
        raw_pool = r.json().get('response', {}).get('results', [])
        
        links_list_html = []
        newly_sent_ids = []

        for article in raw_pool:
            if len(links_list_html) >= 10: break
            fields = article.get('fields', {})
            word_count = int(fields.get('wordcount', 0))
            if article.get('id') in sent_ids or word_count < 1000: continue

            article_url = article.get('webUrl')
            read_time = max(1, word_count // 200)
            item = f"<div class='article-entry'><h3><a href='{article_url}'>{article.get('webTitle')}</a></h3><p>{word_count} words // ~{read_time} min read</p></div>"
            
            links_list_html.append(item)
            newly_sent_ids.append(article.get('id'))
            add_to_instapaper(article_url)

        # Write Files
        links_html = "".join(links_list_html)
        with open("links.html", "w", encoding="utf-8") as f:
            f.write(f"<html><body><h1>links {ts}</h1>{links_html}</body></html>")
            
        # Archive
        if not os.path.exists("old_issues"): os.makedirs("old_issues")
        with open(f"old_issues/{file_date}.html", "w", encoding="utf-8") as f:
            f.write(f"<html><body><h1>daily {ts}</h1>{links_html}</body></html>")

        # Sync Private RSS
        private_hashes = sync_private_feeds(sent_ids)

        # Save Log back to root
        with open(sent_log_path, "w") as f:
            json.dump((newly_sent_ids + private_hashes + sent_ids)[:500], f)
            
        print("--- BUILD SUCCESSFUL ---")
    except Exception as e: print(f"CRITICAL ERROR: {e}")

if __name__ == "__main__": main()