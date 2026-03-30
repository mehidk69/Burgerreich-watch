"""
CENTCOM press release collector.
Source: https://www.centcom.mil/MEDIA/PRESS-RELEASES/
RSS: https://www.centcom.mil/MEDIA/PRESS-RELEASES/RSS/
"""

from utils import fetch_rss, save_data, make_id, normalize_date, classify_tag

FEED_URL = "https://www.centcom.mil/DesktopModules/ArticleCS/RSS.ashx?ContentType=1&Site=104&max=20"
ALT_URL = "https://www.centcom.mil/MEDIA/PRESS-RELEASES/"
COCOM = "centcom"
SOURCE = "CENTCOM"
OUTPUT = "centcom.json"


def collect():
    entries = fetch_rss(FEED_URL)
    if not entries:
        print(f"[WARN] No RSS entries from {FEED_URL}, trying alt...")
        entries = fetch_rss(ALT_URL)

    items = []
    for entry in entries:
        title = entry.get("title", "").strip()
        if not title:
            continue

        link = entry.get("link", "")
        summary = entry.get("summary", "")
        published = entry.get("published", "")

        items.append({
            "id": make_id(title),
            "title": title,
            "url": link,
            "date": normalize_date(published),
            "source": SOURCE,
            "cocom": COCOM,
            "tag": classify_tag(title, summary),
            "summary": summary[:300] if summary else ""
        })

    save_data(OUTPUT, items)


if __name__ == "__main__":
    collect()
