"""
BURGERREICH_watch V3 — Equipment Losses Collector

Source: Atlantic Council Iran war tracker
Extracts US equipment loss/damage entries.
"""

import re
from bs4 import BeautifulSoup
from base import BaseCollector

WORD_NUMS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
}

# (regex, equipment name, status) — order matters for priority
LOSS_PATTERNS = [
    (r'(?:lost|destroyed)\s+(\w+)\s+MQ-9',         "MQ-9 Reaper",           "DESTROYED"),
    (r'(\d+)\s+F-15E',                              "F-15E Strike Eagle",    "DESTROYED"),
    (r'KC-135.*?crash',                              "KC-135 Stratotanker",   "DESTROYED"),
    (r'F-35A.*?(?:damaged|struck|hit)',              "F-35A Lightning II",    "DAMAGED"),
    (r'(\d+)\s+(?:AN/TPY-2|THAAD)',                 "AN/TPY-2 THAAD Radar",  "HIT"),
    (r'AN/FPS-132.*?(?:struck|hit)',                 "AN/FPS-132 Radar",      "DESTROYED"),
    (r'E-3.*?(?:destroyed|damaged|struck)',          "E-3 Sentry AWACS",      "DESTROYED"),
    (r'Ford.*?(?:fire|repair|Souda)',                "USS Ford (CVN-78)",     "DAMAGED"),
]


class LossesCollector(BaseCollector):
    name = "losses"

    URL = "https://www.atlanticcouncil.org/commentary/trackers-and-data-visualizations/tracking-us-military-assets-in-the-iran-war/"

    def collect(self):
        body = BeautifulSoup(self.fetch(self.URL), "lxml").get_text()

        items = []
        for pat, equip, status in LOSS_PATTERNS:
            m = re.search(pat, body, re.IGNORECASE)
            if m:
                qty = self._parse_qty(m)
                items.append({"type": equip, "qty": qty, "status": status})

        cost_m = re.search(r'\$(\d+\.?\d*)\s*billion', body, re.IGNORECASE)

        self.save_json("losses.json", {
            "updated": self.now,
            "source_url": self.URL,
            "items": items,
            "total_cost": f"${cost_m.group(1)}B" if cost_m else "unknown",
        })
        print(f"  [losses] {len(items)} entries, cost: {'$' + cost_m.group(1) + 'B' if cost_m else 'unknown'}")

    def _parse_qty(self, match) -> int:
        try:
            raw = match.group(1)
        except (IndexError, AttributeError):
            return 1
        if raw.isdigit():
            return int(raw)
        return WORD_NUMS.get(raw.lower(), 1)


if __name__ == "__main__":
    LossesCollector().run()
