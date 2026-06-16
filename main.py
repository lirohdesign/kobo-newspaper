import requests
import os
import re
import json
import ssl
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

from bs4 import BeautifulSoup
import importlib.util

try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CONTEXT = None

# --- settings ---
INSTAPAPER_USER = os.environ.get("INSTAPAPER_USER")
INSTAPAPER_PASS = os.environ.get("INSTAPAPER_PASS")
INSTAPAPER_USER_KIDS = os.environ.get("INSTAPAPER_USER_KIDS")
INSTAPAPER_PASS_KIDS = os.environ.get("INSTAPAPER_PASS_KIDS")
GUARDIAN_API_KEY = os.environ.get("GUARDIAN_API_KEY")
NWS_CWA = os.environ.get("NWS_CWA", "iwx")

# Set to False to stop sending Guardian articles to Instapaper (links still
# show up in the daily build either way). Flip back to True when reading more.
SEND_GUARDIAN_TO_INSTAPAPER = False

# Now stored in your persistent archive folder
SENT_LOG_PATH = "old_issues/sent_articles.json"

def add_to_instapaper(url, user=None, pwd=None):
    print(f"DEBUG: Attempting Instapaper add: {url}")
    api_url = "https://www.instapaper.com/api/add"
    try:
        r = requests.post(api_url, auth=(user or INSTAPAPER_USER, pwd or INSTAPAPER_PASS), data={'url': url}, timeout=15)
        print(f"DEBUG: Instapaper Response: {r.status_code}")
        return r.status_code == 200
    except Exception as e:
        print(f"DEBUG: Instapaper Error: {e}")
        return False

def get_timestamp():
    cst_now = datetime.utcnow() - timedelta(hours=6)
    return cst_now.strftime("%d%b%y %H%M").lower()

def update_archive_index():
    if not os.path.exists("old_issues"):
        os.makedirs("old_issues")
    files = sorted([f for f in os.listdir("old_issues") if f.endswith(".html")], reverse=True)
    links = "".join([f'<li><a href="old_issues/{f}">{f.replace(".html", "")}</a></li>' for f in files])
    
    html = f"""<!DOCTYPE html><html>
<head><meta charset='UTF-8'><link rel='stylesheet' href='style.css'></head>
<body><h1>liroh archive</h1><nav><a href="index.html">back to home</a></nav><ul>{links}</ul></body></html>"""
    
    with open("archive.html", "w", encoding="utf-8") as f:
        f.write(html)

def collect_weather(ts):
    print("DEBUG: Collecting Weather...")
    cwa = NWS_CWA.lower()
    url = f"https://forecast.weather.gov/product.php?site={cwa}&issuedby={cwa}&product=afd&format=ci&version=1&glossary=1"
    try:
        r = requests.get(url, timeout=20, headers={'User-Agent': 'Mozilla/5.0'})
        if '<pre class="glossaryProduct">' in r.text:
            start = r.text.find('<pre class="glossaryProduct">') + 29
            end = r.text.find('</pre>', start)
            raw = r.text[start:end].replace('&nbsp;', ' ').replace('&amp;', '&')
            clean_text = re.sub(r'<a [^>]*>(.*?)</a>', r'\1', raw)
            paragraphs = [p.replace('\n', ' ').strip() for p in clean_text.split('\n\n') if p.strip()]
            content = "".join([f'<p>{p}</p>' for p in paragraphs])
            
            html = f"""<!DOCTYPE html><html><head><meta charset='UTF-8'><link rel='stylesheet' href='style.css'></head>
            <body><h1>liroh weather {ts}</h1>{content}</body></html>"""
            with open("weather.html", "w", encoding="utf-8") as f:
                f.write(html)
            return content
    except Exception as e:
        print(f"DEBUG: Weather Error: {e}")
    return ""

def collect_nyt(ts):
    print("DEBUG: Collecting NYT Briefing...")
    path = "nyt_morning.html" 
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw_html = f.read()
            clean = re.sub(r'<(style|script)[^>]*>.*?</\1>', '', raw_html, flags=re.DOTALL)
            content_blocks = re.findall(r'<(p|h2|h3|li)[^>]*>(.*?)</\1>', clean, flags=re.DOTALL)
            content = "".join([f'<{tag}>{re.sub(r"<[^>]+>", "", text).strip()}</{tag}>' for tag, text in content_blocks if tag in ('h2', 'h3') or len(text) > 40])
            
            html = f"""<!DOCTYPE html><html><head><meta charset='UTF-8'><link rel='stylesheet' href='style.css'></head>
            <body><h1>liroh nyt morning {ts}</h1>{content}</body></html>"""
            with open("nyt.html", "w", encoding="utf-8") as f:
                f.write(html)
            return content
        except Exception as e:
            print(f"DEBUG: NYT Error: {e}")
    return ""

def _first_tuesday_of_month(year, month):
    d = datetime(year, month, 1)
    days_ahead = (1 - d.weekday()) % 7
    return d + timedelta(days=days_ahead)


def _timing_label(days_away):
    if days_away <= 0:
        return "today"
    elif days_away == 1:
        return "tomorrow"
    elif days_away <= 6:
        return f"in {days_away} days"
    elif days_away <= 13:
        return "next week"
    return ""


def _run_scraper(scraper_filename):
    path = Path(scraper_filename)
    if not path.exists():
        print(f"DEBUG: Calendar scraper not found — {scraper_filename}")
        return ""
    spec = importlib.util.spec_from_file_location("_scraper", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.collect()


def collect_calendar(today):
    """Read calendar.json, return (active_html, upcoming_html).

    active_html — cards for events due today/this month, each showing either
    scraped content or a fallback reminder with a direct link.
    upcoming_html — plain list of events arriving within lookahead_days.
    """
    try:
        cal = json.loads(Path("calendar.json").read_text())
    except Exception as e:
        print(f"DEBUG: calendar.json error — {e}")
        return "", ""

    lookahead = timedelta(days=cal.get("lookahead_days", 14))
    active_cards = []
    upcoming_items = []

    for event in cal.get("events", []):
        trigger = event.get("trigger")
        label = event["label"]
        url = event.get("url", "")
        due_today = False
        timing = ""
        next_date = None

        if trigger == "first_tuesday_monthly":
            ft = _first_tuesday_of_month(today.year, today.month)
            days_away = (ft.date() - today.date()).days
            due_today = abs(days_away) <= 1
            timing = _timing_label(max(0, days_away))
            if ft.date() >= today.date():
                next_date = ft
            else:
                nm = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
                next_date = _first_tuesday_of_month(nm.year, nm.month)

        elif trigger == "annual_window":
            months = event.get("months", [])
            due_today = today.month in months
            if due_today:
                timing = "this month"
                next_date = today
            else:
                future = [datetime(today.year, m, 1) for m in months
                          if datetime(today.year, m, 1).date() >= today.date()]
                if not future:
                    future = [datetime(today.year + 1, m, 1) for m in months]
                next_date = min(future) if future else None

        elif trigger == "manual":
            for d_str in event.get("dates", []):
                try:
                    d = datetime.strptime(d_str, "%Y-%m-%d")
                    days_away = (d.date() - today.date()).days
                    if abs(days_away) <= 1:
                        due_today = True
                        timing = _timing_label(max(0, days_away))
                    if d.date() >= today.date() and (next_date is None or d < next_date):
                        next_date = d
                except ValueError:
                    pass

        if due_today:
            print(f"DEBUG: Calendar — due: {label}")
            link_html = f"<a href='{url}'>{label}</a>" if url else label
            timing_html = f"<p class='metadata'>{timing}</p>" if timing else ""

            scraper_content = ""
            if event.get("scraper"):
                scraper_content = _run_scraper(event["scraper"])

            if scraper_content:
                active_cards.append(
                    f"<div class='article-entry'><h3>{link_html}</h3>"
                    f"{timing_html}{scraper_content}</div>"
                )
            else:
                # Fallback: always surface the event even without a scraper
                check_note = f"No automated fetch available. <a href='{url}'>Check source →</a>" if url else "No automated fetch — check source manually."
                active_cards.append(
                    f"<div class='article-entry'><h3>{link_html}</h3>"
                    f"{timing_html}<p class='metadata'>{check_note}</p></div>"
                )

        elif next_date and (next_date.date() - today.date()) <= lookahead:
            days_away = (next_date.date() - today.date()).days
            tl = _timing_label(days_away)
            link_html = f"<a href='{url}'>{label}</a>" if url else label
            upcoming_items.append(f"<li>{link_html} &mdash; {tl}</li>")

    active_html = "\n".join(active_cards)
    upcoming_html = (f"<h3>upcoming</h3><ul>{''.join(upcoming_items)}</ul>"
                     if upcoming_items else "")
    return active_html, upcoming_html


def collect_cinema(ts):
    print("DEBUG: Collecting Cinema...")
    try:
        venues_data = json.loads(Path("venues.json").read_text())
    except Exception as e:
        print(f"DEBUG: Cinema venues.json error: {e}")
        return ""

    user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

    def fetch_html(url):
        req = urllib.request.Request(url, headers={"User-Agent": user_agent})
        with urllib.request.urlopen(req, timeout=20, context=SSL_CONTEXT) as resp:
            return resp.read().decode("utf-8", errors="replace")

    def parse_vickers(html):
        soup = BeautifulSoup(html, "html.parser")
        films = []
        for block in soup.find_all(class_="podsfilm"):
            title_el = block.find(class_="podsfilmtitlelink")
            if not title_el:
                continue
            series_el = block.find(class_="podsfilmseries")
            info_el = block.find(class_="showinfodiv")
            blurb_el = block.find(class_="arthouseblurb")
            showtime_els = block.find_all(class_="arthousebutton")
            films.append({
                "title": title_el.get_text(strip=True),
                "series": series_el.get_text(strip=True) if series_el else "",
                "info": info_el.get_text(strip=True) if info_el else "",
                "blurb": blurb_el.get_text(strip=True) if blurb_el else "",
                "showtimes": [s.get_text(strip=True) for s in showtime_els if s.get_text(strip=True)],
            })
        return films

    parsers = {"vickers": parse_vickers}

    def render_film(film):
        series_badge = f"<p class='metadata'>{film['series'].upper()}</p>" if film["series"] else ""
        showtimes_html = ""
        if film["showtimes"]:
            times = " &nbsp;·&nbsp; ".join(film["showtimes"])
            showtimes_html = f"<p class='metadata'>{times}</p>"
        return f"<div class='article-entry'>{series_badge}<h3>{film['title']}</h3><p class='metadata'>{film['info']}</p><p>{film['blurb']}</p>{showtimes_html}</div>"

    sections = []
    for venue in venues_data.get("venues", []):
        vid = venue["id"]
        parser = parsers.get(vid)
        if not parser:
            continue
        try:
            html = fetch_html(venue["url"])
            films = parser(html)
            print(f"DEBUG: {venue['name']}: {len(films)} films")
            if films:
                film_html = "\n".join(render_film(f) for f in films)
                sections.append(f"<h2>{venue['name']}</h2>\n{film_html}")
            else:
                sections.append(f"<h2>{venue['name']}</h2><p>No listings found.</p>")
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
            print(f"DEBUG: {venue['name']} fetch failed — {exc}")
            sections.append(f"<h2>{venue['name']}</h2><p>Unavailable.</p>")

    content = "\n<hr>\n".join(sections)
    with open("cinema.html", "w", encoding="utf-8") as f:
        f.write(f"<!DOCTYPE html><html><head><meta charset='UTF-8'><link rel='stylesheet' href='style.css'></head><body><h1>liroh cinema {ts}</h1>{content}</body></html>")
    return content


def main():
    try:
        print("--- BUILD START ---")
        ts = get_timestamp()
        file_date = (datetime.utcnow() - timedelta(hours=6)).strftime("%Y-%m-%d")
        base_url = "https://lirohdesign.github.io/kobo-newspaper"
        
        # Ensure the folder exists before any logic runs
        if not os.path.exists("old_issues"):
            os.makedirs("old_issues")
            
        today = datetime.utcnow() - timedelta(hours=6)
        weather_content = collect_weather(ts)
        nyt_content = collect_nyt(ts)
        cinema_content = collect_cinema(ts)
        calendar_active, calendar_upcoming = collect_calendar(today)

        # Load existing Sent IDs from the archive folder
        try:
            sent_ids = json.load(open(SENT_LOG_PATH)) if os.path.exists(SENT_LOG_PATH) else []
        except:
            sent_ids = []
        
        # Section include-list mirrors the trades/market-sentiment/climate/policy
        # buckets in taste.md — deliberately leaves out politics/us-news/uk-news,
        # where slugfest and hot-take material concentrates and a length+recency
        # filter has no way to tell that apart from signal.
        params = {'api-key': GUARDIAN_API_KEY, 'page-size': 50, 'type': 'article', 'section': 'environment|world|global-development|business|science', 'show-fields': 'wordcount,trailText', 'order-by': 'newest'}
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
            if SEND_GUARDIAN_TO_INSTAPAPER:
                add_to_instapaper(article_url)

            read_time = max(1, word_count // 200)
            item = f"""<div class='article-entry'>
            <h3><a href='{article_url}'>{article.get('webTitle')}</a></h3>
            <p class='metadata'>{word_count} words // ~{read_time} min read</p>
            <div class='trail-text'>{fields.get('trailText', '')}</div>
            </div>"""
            links_list_html.append(item)
            newly_sent_ids.append(article.get('id'))

        if links_list_html:
            links_final_content = "".join(links_list_html)
        else:
            links_final_content = (
                f"<p class='metadata'>No new articles met the criteria as of {ts}. "
                f"The filter looks for pieces of 1,000 words or more from The Guardian's "
                f"environment, world, global development, business, and science sections "
                f"that have not previously appeared here.</p>"
            )
        
        with open("links.html", "w", encoding="utf-8") as f:
            f.write(f"<!DOCTYPE html><html><head><meta charset='UTF-8'><link rel='stylesheet' href='style.css'></head><body><h1>liroh links {ts}</h1>{links_final_content}</body></html>")

        calendar_section = "\n".join(filter(None, [calendar_active, calendar_upcoming])) or "<p class='metadata'>No events due or upcoming in the next 14 days.</p>"

        # MASTER index.html
        master_index = f"""<!DOCTYPE html><html><head><meta charset='UTF-8'><link rel='stylesheet' href='style.css'></head>
<body><h1>liroh daily {ts}</h1><nav><a href="weather.html">weather</a> | <a href="nyt.html">nyt</a> | <a href="links.html">links</a> | <a href="cinema.html">cinema</a> | <a href="archive.html">archive</a></nav>
<section><h2>01. weather</h2>{weather_content if weather_content else '<p>unavailable</p>'}</section><hr>
<section><h2>02. nyt briefing</h2>{nyt_content if nyt_content else '<p>unavailable</p>'}</section><hr>
<section><h2>03. daily links</h2>{links_final_content}</section><hr>
<section><h2>04. cinema</h2>{cinema_content if cinema_content else '<p>unavailable</p>'}</section><hr>
<section><h2>05. calendar</h2>{calendar_section}</section></body></html>"""
        
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(master_index)
        
        with open(f"old_issues/{file_date}.html", "w", encoding="utf-8") as f:
            f.write(master_index.replace("style.css", "../style.css"))

        # Instapaper Sends for local pages
        if weather_content: add_to_instapaper(f"{base_url}/weather.html?v={ts}")
        if nyt_content: add_to_instapaper(f"{base_url}/nyt.html?v={ts}")
        add_to_instapaper(f"{base_url}/links.html?v={ts}")
        if cinema_content: add_to_instapaper(f"{base_url}/cinema.html?v={ts}")

        update_archive_index()
        
        # Save updated log back to the archive folder
        with open(SENT_LOG_PATH, "w") as f:
            json.dump((newly_sent_ids + sent_ids)[:200], f)
            
        print("--- BUILD SUCCESSFUL ---")
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")

def kids_main():
    from math_generator import collect_math_challenge
    from would_you_rather import collect_wyr
    from kids_weather import collect_kids_weather
    from apod_scrape import collect_apod
    from on_this_day import collect_on_this_day

    try:
        print("--- KIDS BUILD START ---")
        ts = get_timestamp()
        file_date = (datetime.utcnow() - timedelta(hours=6)).strftime("%Y-%m-%d")
        today = datetime.utcnow() - timedelta(hours=6)
        base_url = "https://lirohdesign.github.io/kobo-newspaper"

        if not os.path.exists("old_issues"):
            os.makedirs("old_issues")

        weather_content = collect_kids_weather(ts)
        math_content = collect_math_challenge(today)
        wyr_content = collect_wyr(today)
        apod_content = collect_apod()
        otd_content = collect_on_this_day(today)

        page = f"""<!DOCTYPE html><html><head><meta charset='UTF-8'><link rel='stylesheet' href='style-kids.css'></head>
<body><h1>liroh kids {ts}</h1>
<section><h2>01. weather</h2>{weather_content if weather_content else '<p>unavailable</p>'}</section><hr>
<section><h2>02. math challenge</h2>{math_content}</section><hr>
<section><h2>03. would you rather</h2>{wyr_content}</section><hr>
<section><h2>04. space</h2>{apod_content if apod_content else '<p>unavailable</p>'}</section><hr>
<section><h2>05. on this day</h2>{otd_content if otd_content else '<p>unavailable</p>'}</section>
</body></html>"""

        with open("index-kids.html", "w", encoding="utf-8") as f:
            f.write(page)

        with open(f"old_issues/{file_date}-kids.html", "w", encoding="utf-8") as f:
            f.write(page.replace("style-kids.css", "../style-kids.css"))

        if INSTAPAPER_USER_KIDS and INSTAPAPER_PASS_KIDS:
            add_to_instapaper(
                f"{base_url}/index-kids.html?v={ts}",
                user=INSTAPAPER_USER_KIDS,
                pwd=INSTAPAPER_PASS_KIDS
            )

        update_archive_index()
        print("--- KIDS BUILD SUCCESSFUL ---")
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["standard", "kids"], default="standard")
    args = parser.parse_args()
    if args.mode == "kids":
        kids_main()
    else:
        main()