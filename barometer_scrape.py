import ssl
import urllib.request
import urllib.error

try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CONTEXT = None

URL = "https://ag.purdue.edu/commercialag/ageconomybarometer/"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


def collect():
    """Fetch the current Purdue Ag Economy Barometer report. Returns HTML content string."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return "<p>barometer_scrape: beautifulsoup4 not installed.</p>"

    try:
        req = urllib.request.Request(URL, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=20, context=SSL_CONTEXT) as r:
            soup = BeautifulSoup(r.read(), "html.parser")
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
        print(f"DEBUG: Barometer fetch failed — {e}")
        return ""

    article = soup.find("article")
    if not article:
        print("DEBUG: Barometer — no <article> found")
        return ""

    # Published / upcoming dates
    date_lines = []
    for p in article.find_all("p"):
        t = p.get_text(strip=True)
        if "published" in t.lower() or "upcoming" in t.lower():
            date_lines.append(t)

    # Latest report: first h2 after the "Reports" heading
    report_title = ""
    report_date = ""
    report_authors = ""
    report_summary = ""

    headings = article.find_all("h2")
    reports_heading = next((h for h in headings if h.get_text(strip=True).lower() == "reports"), None)

    if reports_heading:
        # The next h2 is the latest report title
        title_heading = reports_heading.find_next("h2")
        if title_heading:
            report_title = title_heading.get_text(strip=True)
            # Collect paragraphs until the next h2
            paras = []
            for sib in title_heading.next_siblings:
                if not hasattr(sib, "name"):
                    continue
                if sib.name == "h2":
                    break
                if sib.name == "p":
                    text = sib.get_text(strip=True)
                    if not text:
                        continue
                    # First paragraph tends to be date + authors
                    if not report_date and not report_authors:
                        report_date = text
                    else:
                        # Stop at "Read the Full Report" link paragraph
                        if "read the full report" in text.lower():
                            break
                        paras.append(text)
            report_summary = " ".join(paras)

    # Build output
    parts = []

    if date_lines:
        meta = " &nbsp;·&nbsp; ".join(date_lines)
        parts.append(f"<p class='metadata'>{meta}</p>")

    if report_title:
        title_html = f"<h3><a href='{URL}'>{report_title}</a></h3>"
        parts.append(title_html)

    if report_date:
        parts.append(f"<p class='metadata'>{report_date}</p>")

    if report_summary:
        parts.append(f"<p>{report_summary}</p>")
        parts.append(f"<p class='metadata'><a href='{URL}'>Read full report →</a></p>")

    if not parts:
        print("DEBUG: Barometer — parsed page but found no content")
        return ""

    print("DEBUG: Barometer — OK")
    return "\n".join(parts)


if __name__ == "__main__":
    print(collect())
