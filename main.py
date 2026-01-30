def main():
    # 1. handle cst time (utc-6)
    utc_now = datetime.utcnow()
    cst_now = utc_now - timedelta(hours=6)
    date_str = cst_now.strftime("%b %d, %y").lower()
    time_str = cst_now.strftime("%I:%M %p").lower()
    file_date = cst_now.strftime("%Y-%m-%d")

    # 2. sync news (guardian) - captures links BEFORE building
    daily_links_list = []
    feed_url = "https://www.theguardian.com/news/series/the-long-read/rss"
    
    print(f"starting news sync at {time_str} cst...")
    try:
        resp = requests.get(feed_url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
        feed = feedparser.parse(resp.content)
        
        count = 0
        for entry in feed.entries:
            if count >= 10: break
            
            # surgical filter
            link_low = entry.link.lower()
            if not any(x in link_low for x in ['/podcasts/', '/video/', '/sport/', '/football/']):
                print(f"  sending to instapaper: {entry.title[:30]}...")
                success = add_url_to_instapaper(entry.link)
                
                # key fix: we only add to the newsletter if the push was attempted
                daily_links_list.append(f'<li><a href="{entry.link}">{entry.title.lower()}</a></li>')
                count += 1
                time.sleep(2) # gives the connection time to breathe
                
        print(f"  sync complete. captured {len(daily_links_list)} links.")
    except Exception as e:
        print(f"  news sync failed: {e}")
    
    # 3. build newsletter (only happens after sync is finished)
    weather_html_block = get_weather_afd()
    
    # join the list into a single string
    daily_links_html = "".join(daily_links_list) if daily_links_list else "<li>no links synced today.</li>"

    html_body = f"""
    <div class="masthead">liroh daily</div>
    <div class="timestamp">{date_str} // {time_str} cst</div>
    
    <h2>weather discussion</h2>
    <div class="weather-block">{weather_html_block}</div>
    
    <h2>daily links</h2>
    <ul>{daily_links_html}</ul>
    
    <h2>reddit highlights</h2>
    <p>awaiting credentials...</p>
    
    <hr style="margin-top:50px; border:0; border-top:1px dashed #ccc;">
    <p style="font-size:12px; text-align:center;"><a href="archive.html">view old issues</a></p>
    """

    final_html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><link rel="stylesheet" href="style.css"></head><body>{html_body}</body></html>"""

    # 4. save files
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(final_html)

    if not os.path.exists("old_issues"):
        os.makedirs("old_issues")
    
    archive_html = final_html.replace('href="style.css"', 'href="../style.css"')
    with open(f"old_issues/{file_date}.html", "w", encoding="utf-8") as f:
        f.write(archive_html)
        
    update_archive_index()
    print("success: index.html and archive updated.")