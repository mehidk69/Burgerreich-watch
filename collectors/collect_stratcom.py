"""
STRATCOM news collector.
Source: https://www.stratcom.mil/Media/News/
"""

from utils import fetch_rss, save_data, make_id, normalize_date, classify_tag

FEED_URL = "https://www.stratcom.mil/DesktopModules/ArticleCS/RSS.ashx?ContentType=1&Site=107&max=20"
COCOM = "stratcom"
SOURCE = "STRATCOM"
OUTPUT = "stratcom.json"


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
