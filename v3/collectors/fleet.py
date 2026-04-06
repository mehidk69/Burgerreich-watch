"""
BURGERREICH_watch V3 — Fleet Positions Collector

Source: USNI Fleet & Marine Tracker (weekly)
Extracts carrier strike groups, ARGs, and battle force numbers.
"""

import re
from bs4 import BeautifulSoup
from base import BaseCollector


class FleetCollector(BaseCollector):
    name = "fleet"

    TRACKER_INDEX = "https://news.usni.org/category/fleet-tracker"

    # Homeport cities for status detection
    HOMEPORTS = {"norfolk", "san diego", "bremerton", "yokosuka", "pearl harbor", "mayport"}

    def collect(self):
        tracker_url = self._find_latest_tracker()
        if not tracker_url:
            raise RuntimeError("could not find latest USNI fleet tracker URL")

        print(f"  [fleet] fetching {tracker_url}")
        body = BeautifulSoup(self.fetch(tracker_url), "lxml").get_text(separator="\n")

        carriers = self._extract_ships(body, r'(USS\s+[\w\.\s]+?)\s*\((CVN-\d+)\)', "CVN")
        args = self._extract_ships(body, r'(USS\s+[\w\.\s]+?)\s*\((LH[AD]-\d+)\)', "LH")

        bf = re.search(r'Total Battle Force.*?(\d+)\s*\(', body)
        dep = re.search(r'Deployed.*?(\d+)', body)
        uw = re.search(r'Underway.*?(\d+)', body)

        self.save_json("fleet.json", {
            "updated": self.now,
            "source_url": tracker_url,
            "battle_force": bf.group(1) if bf else None,
            "deployed": dep.group(1) if dep else None,
            "underway": uw.group(1) if uw else None,
            "carriers": carriers,
            "args": args,
        })
        print(f"  [fleet] {len(carriers)} carriers, {len(args)} ARGs")

    def _find_latest_tracker(self) -> str | None:
        index_html = self.fetch(self.TRACKER_INDEX)
        soup = BeautifulSoup(index_html, "lxml")
        for a in soup.find_all("a", href=True):
            if "fleet-and-marine-tracker" in a["href"]:
                return a["href"]
        return None

    def _extract_ships(self, body: str, pattern: str, hull_prefix: str) -> list[dict]:
        ships = []
        full_pat = pattern + r'\s+(?:is|was|arrived|departed|returned|operating)\s+(?:\w+\s+)?(?:in\s+)?(?:the\s+)?([\w\s,\-]+?)(?:\.|,|$)'
        for m in re.finditer(full_pat, body, re.MULTILINE):
            hull = m.group(2).strip()
            if any(s["hull"] == hull for s in ships):
                continue
            location = m.group(3).strip()[:60]
            status = self._classify_status(body, m, location)
            ships.append({
                "name": m.group(1).strip(),
                "hull": hull,
                "location": location,
                "status": status,
            })
        return ships

    def _classify_status(self, body: str, match, location: str) -> str:
        ctx = body[max(0, match.start() - 200):match.end() + 200].lower()
        loc_lower = location.lower()

        if "maintenance" in ctx or "overhaul" in ctx:
            return "MAINTENANCE"
        if "homeport" in ctx or ("arrived" in ctx and any(hp in loc_lower for hp in self.HOMEPORTS)):
            return "HOMEPORT"
        if "en route" in ctx or "transit" in ctx:
            return "TRANSIT"
        return "DEPLOYED"


if __name__ == "__main__":
    FleetCollector().run()
