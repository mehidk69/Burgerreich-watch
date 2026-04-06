"""
BURGERREICH_watch V3 — Unified COCOM RSS Collector

Replaces 5 identical V2 collectors (centcom, eucom, indopacom, africom, stratcom)
with a single data-driven collector. Add a new COCOM by adding one row to FEEDS.
"""

from base import BaseCollector, classify_tag, make_id, normalize_date

# ── Feed config: one row = one collector ─────────────────────
FEEDS = [
    {
        "cocom": "centcom",
        "source": "CENTCOM",
        "rss": "https://www.centcom.mil/DesktopModules/ArticleCS/RSS.ashx?ContentType=1&Site=104&max=20",
        "output": "centcom.json",
    },
    {
        "cocom": "eucom",
        "source": "EUCOM",
        "rss": "https://www.eucom.mil/DesktopModules/ArticleCS/RSS.ashx?ContentType=1&Site=105&max=20",
        "output": "eucom.json",
    },
    {
        "cocom": "indopacom",
        "source": "INDOPACOM",
        "rss": "https://www.pacom.mil/DesktopModules/ArticleCS/RSS.ashx?ContentType=1&Site=108&max=20",
        "output": "indopacom.json",
    },
    {
        "cocom": "africom",
        "source": "AFRICOM",
        "rss": "https://www.africom.mil/DesktopModules/ArticleCS/RSS.ashx?ContentType=1&Site=106&max=20",
        "output": "africom.json",
    },
    {
        "cocom": "stratcom",
        "source": "STRATCOM",
        "rss": "https://www.stratcom.mil/DesktopModules/ArticleCS/RSS.ashx?ContentType=1&Site=107&max=20",
        "output": "stratcom.json",
    },
    {
        "cocom": "socom",
        "source": "SOCOM",
        "rss": "https://www.socom.mil/DesktopModules/ArticleCS/RSS.ashx?ContentType=1&Site=110&max=20",
        "output": "socom.json",
    },
    {
        "cocom": "northcom",
        "source": "NORTHCOM",
        "rss": "https://www.northcom.mil/DesktopModules/ArticleCS/RSS.ashx?ContentType=1&Site=111&max=20",
        "output": "northcom.json",
    },
    {
        "cocom": "southcom",
        "source": "SOUTHCOM",
        "rss": "https://www.southcom.mil/DesktopModules/ArticleCS/RSS.ashx?ContentType=1&Site=109&max=20",
        "output": "southcom.json",
    },
]


class CocomCollector(BaseCollector):
    """Collects press releases from a single COCOM RSS feed."""

    def __init__(self, feed_cfg: dict):
        super().__init__()
        self.cfg = feed_cfg
        self.name = feed_cfg["cocom"]

    def collect(self):
        entries = self.fetch_rss(self.cfg["rss"])
        if not entries:
            self.errors.append(f"no entries from {self.cfg['rss']}")
            return

        items = []
        for entry in entries:
            title = entry.get("title", "").strip()
            if not title:
                continue
            summary = entry.get("summary", "")
            items.append({
                "id": make_id(title),
                "title": title,
                "url": entry.get("link", ""),
                "date": normalize_date(entry.get("published", "")),
                "source": self.cfg["source"],
                "cocom": self.cfg["cocom"],
                "tag": classify_tag(title, summary),
                "summary": summary[:300] if summary else "",
            })

        self.save_feed(self.cfg["output"], items)


def all_cocom_collectors() -> list[CocomCollector]:
    """Return a collector instance for every configured COCOM."""
    return [CocomCollector(cfg) for cfg in FEEDS]


if __name__ == "__main__":
    for c in all_cocom_collectors():
        c.run()
