"""
BURGERREICH_watch V3 — Base Collector

All collectors inherit from BaseCollector. Provides:
  - HTTP fetch with retries + backoff
  - RSS feed parsing
  - JSON save with dedup + cap
  - Auto-classification by keyword
  - Structured status reporting
"""

import hashlib
import json
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import requests

DATA_DIR = Path(__file__).parent.parent / "site" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "BURGERREICH-watch/3.0 (OSINT; dasdemarc.substack.com)"}
MAX_ITEMS = 50

# ── Tag classification keywords ──────────────────────────────
TAG_RULES = [
    ("alert",    ["strike", "engage", "intercept", "attack", "airstrike", "missile", "shoot"]),
    ("naval",    ["ship", "carrier", "fleet", "naval", "maritime", "vessel", "navy", "destroyer"]),
    ("air",      ["aircraft", "bomber", "fighter", "squadron", "air force", "flight",
                  "f-35", "f-16", "f-22", "b-52", "b-2", "kc-135", "mq-9"]),
    ("exercise", ["exercise", "drill", "training", "bilateral", "multilateral", "balikatan", "cope"]),
    ("posture",  ["deploy", "posture", "reposition", "rotate", "surge", "reinforce"]),
    ("ground",   ["soldier", "troop", "brigade", "battalion", "infantry", "army", "marine"]),
]


def classify_tag(title: str, summary: str = "") -> str:
    text = (title + " " + summary).lower()
    for tag, keywords in TAG_RULES:
        if any(kw in text for kw in keywords):
            return tag
    return "posture"


def make_id(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()[:12]


def normalize_date(date_str: str) -> str:
    if not date_str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        dt = parsedate_to_datetime(date_str)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return date_str


class BaseCollector(ABC):
    """Abstract base for all V3 collectors."""

    name: str = "base"

    def __init__(self):
        self.now = datetime.now(timezone.utc).isoformat()
        self.errors: list[str] = []

    # ── HTTP ─────────────────────────────────────────────────
    def fetch(self, url: str, timeout: int = 30, retries: int = 2) -> str:
        for attempt in range(retries + 1):
            try:
                resp = requests.get(url, headers=HEADERS, timeout=timeout)
                resp.raise_for_status()
                return resp.text
            except requests.RequestException as e:
                if attempt == retries:
                    raise
                wait = 3 * (attempt + 1)
                print(f"  [{self.name}] retry {attempt+1}/{retries} in {wait}s — {e}")
                time.sleep(wait)

    def fetch_rss(self, url: str, timeout: int = 30) -> list:
        import feedparser
        try:
            resp = requests.get(url, headers=HEADERS, timeout=timeout)
            resp.raise_for_status()
            return feedparser.parse(resp.text).entries
        except Exception as e:
            print(f"  [{self.name}] RSS fetch failed: {e}")
            return []

    # ── Storage ──────────────────────────────────────────────
    def save_json(self, filename: str, data):
        path = DATA_DIR / filename
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"  [{self.name}] saved {path.name}")

    def save_feed(self, filename: str, new_items: list):
        """Save feed items with dedup by ID and cap at MAX_ITEMS."""
        existing = self._load(filename)
        seen = set()
        merged = []
        for item in new_items + existing:
            item_id = item.get("id", make_id(item.get("title", "")))
            if item_id not in seen:
                seen.add(item_id)
                merged.append(item)
        merged.sort(key=lambda x: x.get("date", ""), reverse=True)
        merged = merged[:MAX_ITEMS]
        self.save_json(filename, merged)
        print(f"  [{self.name}] {len(merged)} items in {filename}")

    def _load(self, filename: str) -> list:
        path = DATA_DIR / filename
        if path.exists():
            try:
                with open(path) as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return []
        return []

    # ── Run wrapper ──────────────────────────────────────────
    def run(self) -> dict:
        """Execute collector, return status dict."""
        print(f"\n[{self.name}] collecting...")
        start = time.time()
        try:
            self.collect()
            elapsed = round(time.time() - start, 1)
            print(f"  [{self.name}] done ({elapsed}s)")
            return {"collector": self.name, "status": "ok", "elapsed": elapsed, "errors": self.errors}
        except Exception as e:
            elapsed = round(time.time() - start, 1)
            self.errors.append(str(e))
            print(f"  [{self.name}] FAILED ({elapsed}s): {e}")
            return {"collector": self.name, "status": "error", "elapsed": elapsed, "errors": self.errors}

    @abstractmethod
    def collect(self):
        """Override in subclasses to do the actual collection."""
        ...
