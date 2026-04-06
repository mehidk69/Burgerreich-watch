"""
BURGERREICH_watch V3 — Casualties Collector

Source: Wikipedia 2026 Iran war page
Extracts US KIA/WIA counts from article text.
"""

import re
from bs4 import BeautifulSoup
from base import BaseCollector


class CasualtiesCollector(BaseCollector):
    name = "casualties"

    URL = "https://en.wikipedia.org/wiki/2026_Iran_war"

    KIA_PATTERNS = [
        r'(\d+)\s+(?:U\.?S\.?|American|United States)\s+(?:service members?|soldiers?|troops?|military personnel)\s+(?:have been\s+)?killed',
        r'(\d+)\s+killed\s+in\s+action',
        r'(\d+)\s+US\s+(?:troops?\s+)?(?:have\s+)?(?:been\s+)?killed',
    ]

    WIA_PATTERNS = [
        r'(\d+[\+]?)\s+(?:U\.?S\.?|American)\s+(?:service members?|military personnel|troops?)\s+(?:have been\s+)?(?:wounded|injured)',
        r'approximately\s+(\d+[\+]?)\s+(?:U\.?S\.?|American)\s+.*?(?:wounded|injured)',
        r'(\d+[\+]?)\s+(?:U\.?S\.?|American)\s+.*?(?:wounded|injured)',
    ]

    def collect(self):
        body = BeautifulSoup(self.fetch(self.URL), "lxml").get_text()

        kia = self._first_match(body, self.KIA_PATTERNS)
        wia = self._first_match(body, self.WIA_PATTERNS)

        self.save_json("casualties.json", {
            "updated": self.now,
            "source": "Wikipedia / CENTCOM",
            "us_kia_confirmed": kia,
            "us_wia_confirmed": wia,
            "operations": [
                {"name": "Operation Epic Fury", "kia": kia or "13", "wia": wia or "348", "period": "Feb 28, 2026–present"},
                {"name": "Tower 22 (Jordan)", "kia": "3", "wia": "47", "period": "Jan 28, 2024"},
                {"name": "Syria ISIS Ambush", "kia": "3", "wia": "3", "period": "Dec 14, 2025"},
            ],
        })
        print(f"  [casualties] KIA: {kia}, WIA: {wia}")

    def _first_match(self, text: str, patterns: list[str]) -> str | None:
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                return m.group(1)
        return None


if __name__ == "__main__":
    CasualtiesCollector().run()
