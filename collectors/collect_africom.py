"""
AFRICOM press release collector.
Source: https://www.africom.mil/pressrelease
"""

from utils import fetch_rss, save_data, make_id, normalize_date, classify_tag

FEED_URL = "https://www.africom.mil/DesktopModules/ArticleCS/RSS.ashx?ContentType=1&Site=106&max=20"
COCOM = "africom"
SOURCE = "AFRICOM"
OUTPUT = "africom.json"


def collect():
    entries = fetch_rss(FEED_URL)
    items = []
    for entry in entries:
        title = entry.get("title", "").strip()
        if not title:
            continue

        items.append({
            "id": make_id(title),
            "title": title,
            "url": entry.get("link", ""),
            "date": normalize_date(entry.get("published", "")),
            "source": SOURCE,
            "cocom": COCOM,
            "tag": classify_tag(title, entry.get("summary", "")),
            "summary": entry.get("summary", "")[:300]
        })

    save_data(OUTPUT, items)


if __name__ == "__main__":
    collect()
