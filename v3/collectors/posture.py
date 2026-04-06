"""
BURGERREICH_watch V3 — Troop Posture Collector

Source: Wikipedia 2026 US military buildup in the Middle East
Extracts troop counts and named deployments.
"""

import re
from bs4 import BeautifulSoup
from base import BaseCollector


TROOP_PATTERNS = [
    r'(\d{2},?\d{3})\s+(?:American|U\.?S\.?)\s+troops',
    r'(?:over|more than|at least)\s+(\d{2},?\d{3})\s+(?:troops|service members)',
    r'(\d{2},?\d{3})\s+U\.?S\.?\s+troops\s+(?:are\s+)?(?:now\s+)?(?:deployed|supporting)',
]

DEPLOY_PATTERNS = [
    (r'82nd Airborne.*?(?:deployed|arriving|arrived)',              "82nd Airborne Division"),
    (r'(?:USS\s+)?Tripoli.*?(?:arrived|entered|deployed)',         "Tripoli ARG"),
    (r'(?:USS\s+)?Boxer.*?(?:deployed|departed)',                  "Boxer ARG"),
    (r'F-22.*?(?:deployed|stationed)\s+(?:to|at)\s+([\w\s]+)',    "F-22 Raptors"),
    (r'F-15E.*?(?:relocated|deployed|moved)\s+(?:to|from)',       "F-15E Strike Eagles"),
    (r'Patriot.*?(?:deployed|battery)',                            "Patriot Battery"),
    (r'THAAD.*?(?:deployed|repositioned)',                         "THAAD System"),
    (r'B-52.*?(?:deployed|rotation|Diego Garcia)',                 "B-52 Bombers"),
    (r'101st Airborne.*?(?:deployed|arrived)',                     "101st Airborne Division"),
    (r'10th Mountain.*?(?:deployed|arrived)',                      "10th Mountain Division"),
]


class PostureCollector(BaseCollector):
    name = "posture"

    URL = "https://en.wikipedia.org/wiki/2026_United_States_military_buildup_in_the_Middle_East"

    def collect(self):
        body = BeautifulSoup(self.fetch(self.URL), "lxml").get_text()

        # Total troop count
        total = None
        for pat in TROOP_PATTERNS:
            m = re.search(pat, body, re.IGNORECASE)
            if m:
                total = m.group(1)
                break

        # Named deployments
        deployments = []
        for pat, asset_name in DEPLOY_PATTERNS:
            m = re.search(pat, body, re.IGNORECASE)
            if m:
                ctx = body[max(0, m.start() - 50):m.end() + 100].strip()[:120]
                deployments.append({"asset": asset_name, "context": ctx})

        self.save_json("posture.json", {
            "updated": self.now,
            "source": "Wikipedia — 2026 US military buildup in the Middle East",
            "total_middle_east": total,
            "deployments_mentioned": deployments,
        })
        print(f"  [posture] troops: {total}, deployments: {len(deployments)}")


if __name__ == "__main__":
    PostureCollector().run()
