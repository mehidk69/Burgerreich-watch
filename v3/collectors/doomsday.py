"""
BURGERREICH_watch V3 — Doomsday Clock Collector

Source: Bulletin of the Atomic Scientists
Extracts current seconds-to-midnight reading.
"""

import re
from bs4 import BeautifulSoup
from base import BaseCollector


class DoomsdayCollector(BaseCollector):
    name = "doomsday"

    URL = "https://thebulletin.org/doomsday-clock/"

    PATTERNS = [
        r'(\d+)\s+seconds?\s+(?:to|before)\s+midnight',
        r'Clock.*?(\d+)\s+seconds',
    ]

    def collect(self):
        body = BeautifulSoup(self.fetch(self.URL), "lxml").get_text()

        seconds = None
        for pat in self.PATTERNS:
            m = re.search(pat, body, re.IGNORECASE)
            if m:
                seconds = m.group(1)
                break

        self.save_json("doomsday.json", {
            "updated": self.now,
            "seconds_to_midnight": seconds,
            "source": "Bulletin of the Atomic Scientists",
        })
        print(f"  [doomsday] {seconds}s to midnight")


if __name__ == "__main__":
    DoomsdayCollector().run()
