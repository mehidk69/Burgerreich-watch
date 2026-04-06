"""
BURGERREICH_watch V3 — Commanders Collector

Source: .mil leadership pages for each COCOM
Extracts commander names via rank+name regex patterns.
"""

import re
from bs4 import BeautifulSoup
from base import BaseCollector

COCOM_PAGES = [
    ("centcom",   "https://www.centcom.mil/ABOUT-US/LEADERSHIP/"),
    ("eucom",     "https://www.eucom.mil/about-us/leadership/combatant-commander"),
    ("indopacom", "https://www.pacom.mil/Leadership/Commander/"),
    ("northcom",  "https://www.northcom.mil/Leadership/Commander/"),
    ("africom",   "https://www.africom.mil/about-the-command/leadership/commander"),
    ("southcom",  "https://www.southcom.mil/Leadership/Commander/"),
    ("stratcom",  "https://www.stratcom.mil/Leadership/Commander/"),
    ("socom",     "https://www.socom.mil/about/leadership"),
]

NAME_PATTERNS = [
    r'((?:Gen(?:eral)?|Adm(?:iral)?|GEN|ADM)\.?\s+[\w\.\s\-\']+?)(?:\n|,|Commander)',
    r'((?:Gen|Adm)\.?\s+[\w\.\s]+?)(?:\s+is\s+the|\s+assumed|\s+serves)',
    r'Commander[,:\s]+((?:Gen|Adm)\.?\s+[\w\.\s]+?)(?:\n|,|\.)',
]


class CommandersCollector(BaseCollector):
    name = "commanders"

    def collect(self):
        commanders = {}
        for cocom, url in COCOM_PAGES:
            commanders[cocom] = self._scrape_commander(cocom, url)

        self.save_json("commanders.json", {
            "updated": self.now,
            "commanders": commanders,
        })
        found = sum(1 for c in commanders.values() if "error" not in c["name"])
        print(f"  [commanders] {found}/{len(COCOM_PAGES)} found")

    def _scrape_commander(self, cocom: str, url: str) -> dict:
        try:
            body = BeautifulSoup(self.fetch(url), "lxml").get_text()
            for pat in NAME_PATTERNS:
                m = re.search(pat, body)
                if m:
                    return {"name": m.group(1).strip()[:60], "url": url}
            return {"name": "check manually", "url": url}
        except Exception as e:
            self.errors.append(f"{cocom}: {e}")
            return {"name": f"error: {e}", "url": url}


if __name__ == "__main__":
    CommandersCollector().run()
