#!/usr/bin/env python3
"""
BURGERREICH_watch V3 — Concurrent Runner

Single entry point. Runs all collectors concurrently using ThreadPoolExecutor,
merges COCOM feeds, and writes collector_status.json.

Usage:
    python run.py              # run all collectors
    python run.py cocom        # run only COCOM RSS feeds
    python run.py osint        # run only scraper collectors
    python run.py fleet        # run a single collector by name
"""

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

# Ensure collectors/ is on path
sys.path.insert(0, str(Path(__file__).parent))

from base import DATA_DIR, BaseCollector
from cocom_rss import all_cocom_collectors
from fleet import FleetCollector
from casualties import CasualtiesCollector
from losses import LossesCollector
from posture import PostureCollector
from commanders import CommandersCollector
from doomsday import DoomsdayCollector

# ── Collector registry ───────────────────────────────────────
SCRAPER_COLLECTORS = [
    FleetCollector,
    CasualtiesCollector,
    LossesCollector,
    PostureCollector,
    CommandersCollector,
    DoomsdayCollector,
]

# Merge config
COCOM_FEEDS = ["centcom.json", "eucom.json", "indopacom.json", "africom.json",
               "stratcom.json", "socom.json", "northcom.json", "southcom.json"]
MERGE_OUTPUT = DATA_DIR / "feed.json"
MAX_FEED = 100


def merge_feeds():
    """Merge all COCOM outputs into a single unified feed."""
    print("\n[merge] combining COCOM feeds...")
    all_items = []
    for fname in COCOM_FEEDS:
        fpath = DATA_DIR / fname
        if fpath.exists():
            try:
                with open(fpath) as f:
                    items = json.load(f)
                    all_items.extend(items)
                    print(f"  {fname}: {len(items)} items")
            except (json.JSONDecodeError, IOError) as e:
                print(f"  {fname}: ERROR — {e}")

    # Dedup by ID, sort by date, cap
    seen = set()
    unique = []
    for item in all_items:
        iid = item.get("id", "")
        if iid and iid not in seen:
            seen.add(iid)
            unique.append(item)
    unique.sort(key=lambda x: x.get("date", ""), reverse=True)
    unique = unique[:MAX_FEED]

    with open(MERGE_OUTPUT, "w") as f:
        json.dump(unique, f, indent=2)
    print(f"  [merge] {len(unique)} items → feed.json")


def build_collectors(mode: str) -> list[BaseCollector]:
    """Build collector list based on CLI mode."""
    if mode == "all":
        return all_cocom_collectors() + [cls() for cls in SCRAPER_COLLECTORS]
    elif mode == "cocom":
        return all_cocom_collectors()
    elif mode == "osint":
        return [cls() for cls in SCRAPER_COLLECTORS]
    else:
        # Single collector by name
        for cls in SCRAPER_COLLECTORS:
            if cls.name == mode:
                return [cls()]
        from cocom_rss import FEEDS, CocomCollector
        for cfg in FEEDS:
            if cfg["cocom"] == mode:
                return [CocomCollector(cfg)]
        print(f"Unknown collector: {mode}")
        sys.exit(1)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    now = datetime.now(timezone.utc)

    print("=" * 60)
    print(f"BURGERREICH_watch V3 — Collector Runner")
    print(f"Mode: {mode} | Time: {now.isoformat()}")
    print("=" * 60)

    collectors = build_collectors(mode)
    results = []

    start = time.time()
    # Run all collectors concurrently (I/O bound — threads are ideal)
    with ThreadPoolExecutor(max_workers=min(len(collectors), 12)) as pool:
        futures = {pool.submit(c.run): c for c in collectors}
        for future in as_completed(futures):
            results.append(future.result())

    # Merge COCOM feeds if we ran any
    if mode in ("all", "cocom") or any(r["collector"] in [f.replace(".json", "") for f in COCOM_FEEDS] for r in results):
        merge_feeds()

    # Write status
    elapsed = round(time.time() - start, 1)
    errors = [r for r in results if r["status"] == "error"]

    status = {
        "last_run": now.isoformat(),
        "mode": mode,
        "elapsed_total": elapsed,
        "collectors_run": len(results),
        "succeeded": len(results) - len(errors),
        "failed": len(errors),
        "results": results,
        "manual_items": [
            "Unconfirmed entries (editorial judgment)",
            "Contractor wartime surge numbers",
            "Flash brief BLUF bullets",
            "Ship coordinates (lat/lng for new positions)",
        ],
    }

    with open(DATA_DIR / "collector_status.json", "w") as f:
        json.dump(status, f, indent=2)

    print(f"\n{'=' * 60}")
    print(f"Done in {elapsed}s — {len(results) - len(errors)}/{len(results)} succeeded")
    if errors:
        for e in errors:
            print(f"  ✗ {e['collector']}: {', '.join(e['errors'])}")
    print("=" * 60)


if __name__ == "__main__":
    main()
