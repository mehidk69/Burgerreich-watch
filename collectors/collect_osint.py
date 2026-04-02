#!/usr/bin/env python3
"""
BURGERREICH_watch@ Auto-Collector

Scrapes public OSINT sources for:
  1. Fleet positions (USNI Fleet Tracker)
  2. Casualty updates (CENTCOM / DoD)
  3. Equipment losses (Atlantic Council tracker)

Outputs: site/data/fleet.json, site/data/casualties.json, site/data/losses.json

These feed both the dashboard and the report template generator.
"""

import json
import re
import os
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("[COLLECTOR] Install: pip install requests beautifulsoup4 lxml")
    exit(1)

DATA_DIR = Path(__file__).parent.parent / "site" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "BURGERREICH-watch/1.0 (OSINT dashboard; contact: dasdemarc.substack.com)"
}


# ══════════════════════════════════════════════════════════════
# 1. FLEET POSITIONS — USNI News Fleet Tracker
# ══════════════════════════════════════════════════════════════

def collect_fleet():
    """Scrape latest USNI Fleet Tracker for carrier/ARG positions."""
    print("[FLEET] Fetching USNI Fleet Tracker index...")
    
    # Get the fleet tracker category page to find latest post
    index_url = "https://news.usni.org/category/fleet-tracker"
    resp = requests.get(index_url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    
    soup = BeautifulSoup(resp.text, "lxml")
    
    # Find first article link (latest tracker post)
    link = None
    for a in soup.select("article a, h2 a, .entry-title a"):
        href = a.get("href", "")
        if "fleet-and-marine-tracker" in href or "fleet-tracker" in href:
            link = href
            break
    
    if not link:
        # Fallback: construct likely URL
        now = datetime.now(timezone.utc)
        link = f"https://news.usni.org/category/fleet-tracker"
        print("[FLEET] Could not find latest tracker link, using index")
    
    print(f"[FLEET] Fetching: {link}")
    resp = requests.get(link, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    
    text = resp.text
    soup = BeautifulSoup(text, "lxml")
    
    # Get article body text
    article = soup.select_one(".entry-content, article, .post-content")
    if not article:
        print("[FLEET] Could not find article content")
        return None
    
    body = article.get_text(separator="\n")
    
    # Parse carrier positions
    carriers = []
    carrier_patterns = [
        r"(USS\s+[\w\.\s]+)\s*\((CVN-\d+)\).*?(?:is\s+(?:in|operating|underway|en route)\s+(?:in\s+)?(?:the\s+)?([\w\s,]+?)(?:\.|,|\n))",
        r"Aircraft carrier\s+(USS\s+[\w\.\s]+)\s*\((CVN-\d+)\)\s+(?:is\s+(?:in|operating|underway)\s+(?:in\s+)?(?:the\s+)?([\w\s,]+?)(?:\.|,|\n))",
    ]
    
    for pattern in carrier_patterns:
        for match in re.finditer(pattern, body, re.IGNORECASE):
            name = match.group(1).strip()
            hull = match.group(2).strip()
            location = match.group(3).strip()
            
            # Determine status
            status = "DEPLOYED"
            if "homeport" in body[max(0,match.start()-100):match.end()+100].lower() or "in port" in location.lower():
                status = "HOMEPORT"
            elif "maintenance" in body[max(0,match.start()-100):match.end()+100].lower():
                status = "MAINTENANCE"
            elif "en route" in body[max(0,match.start()-100):match.end()+100].lower():
                status = "TRANSIT"
            
            # Avoid duplicates
            if not any(c["hull"] == hull for c in carriers):
                carriers.append({
                    "name": name,
                    "hull": hull,
                    "status": status,
                    "location": location[:80],  # trim
                    "source": "USNI Fleet Tracker",
                    "scraped": datetime.now(timezone.utc).isoformat()
                })
    
    # Parse ARG/MEU positions
    args = []
    arg_patterns = [
        r"(USS\s+[\w\.\s]+)\s*\((LH[AD]-\d+)\).*?(?:is\s+(?:in|operating|underway|en route)\s+(?:in\s+)?(?:the\s+)?([\w\s,]+?)(?:\.|,|\n))",
    ]
    
    for pattern in arg_patterns:
        for match in re.finditer(pattern, body, re.IGNORECASE):
            name = match.group(1).strip()
            hull = match.group(2).strip()
            location = match.group(3).strip()
            
            status = "DEPLOYED"
            if "homeport" in body[max(0,match.start()-100):match.end()+100].lower():
                status = "HOMEPORT"
            elif "en route" in body[max(0,match.start()-100):match.end()+100].lower():
                status = "TRANSIT"
            
            if not any(a["hull"] == hull for a in args):
                args.append({
                    "name": name,
                    "hull": hull,
                    "status": status,
                    "location": location[:80],
                    "source": "USNI Fleet Tracker",
                    "scraped": datetime.now(timezone.utc).isoformat()
                })
    
    # Also grab the battle force numbers from the top
    bf_match = re.search(r"Total Battle Force.*?(\d+)\s*\(", body)
    total_bf = bf_match.group(1) if bf_match else None
    
    deployed_match = re.search(r"Deployed.*?(\d+)", body)
    total_deployed = deployed_match.group(1) if deployed_match else None
    
    result = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "source_url": link,
        "total_battle_force": total_bf,
        "total_deployed": total_deployed,
        "carriers": carriers,
        "args": args
    }
    
    outpath = DATA_DIR / "fleet.json"
    with open(outpath, "w") as f:
        json.dump(result, f, indent=2)
    
    print(f"[FLEET] Found {len(carriers)} carriers, {len(args)} ARGs")
    print(f"[FLEET] Saved: {outpath}")
    return result


# ══════════════════════════════════════════════════════════════
# 2. CASUALTIES — Wikipedia ongoing conflict page + CENTCOM
# ══════════════════════════════════════════════════════════════

def collect_casualties():
    """Scrape casualty figures from Wikipedia's Iran war page."""
    print("[CASUALTIES] Fetching Wikipedia 2026 Iran war page...")
    
    url = "https://en.wikipedia.org/wiki/2026_Iran_war"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    
    soup = BeautifulSoup(resp.text, "lxml")
    
    # Look for casualty numbers in the infobox
    infobox = soup.select_one(".infobox, .vevent")
    casualties = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "source": "Wikipedia / CENTCOM",
        "source_url": url,
        "operations": []
    }
    
    body = soup.get_text()
    
    # Try to find US casualty figures
    kia_patterns = [
        r"(\d+)\s+(?:US|American|United States)\s+(?:service members?|soldiers?|troops?)\s+killed",
        r"(\d+)\s+killed\s+in\s+action",
        r"US[:\s]+(\d+)\s+killed",
    ]
    
    wia_patterns = [
        r"(\d+\+?)\s+(?:US|American)\s+(?:service members?|soldiers?|troops?)\s+wounded",
        r"(\d+\+?)\s+wounded\s+in\s+action",
    ]
    
    us_kia = None
    us_wia = None
    
    for p in kia_patterns:
        m = re.search(p, body, re.IGNORECASE)
        if m:
            us_kia = m.group(1)
            break
    
    for p in wia_patterns:
        m = re.search(p, body, re.IGNORECASE)
        if m:
            us_wia = m.group(1)
            break
    
    if us_kia:
        casualties["operations"].append({
            "name": "Operation Epic Fury",
            "kia": us_kia,
            "wia": us_wia or "unknown",
            "period": "Feb 28, 2026 – present",
            "source": "Wikipedia / CENTCOM"
        })
    
    # Static entries for prior incidents (these don't change)
    casualties["operations"].extend([
        {"name": "Tower 22 (Jordan)", "kia": "3", "wia": "47", "period": "Jan 28, 2024", "source": "DoD"},
        {"name": "Syria ISIS Ambush", "kia": "3", "wia": "3", "period": "Dec 14, 2025", "source": "CENTCOM"},
    ])
    
    outpath = DATA_DIR / "casualties.json"
    with open(outpath, "w") as f:
        json.dump(casualties, f, indent=2)
    
    print(f"[CASUALTIES] US KIA: {us_kia}, WIA: {us_wia}")
    print(f"[CASUALTIES] Saved: {outpath}")
    return casualties


# ══════════════════════════════════════════════════════════════
# 3. EQUIPMENT LOSSES — Atlantic Council tracker
# ══════════════════════════════════════════════════════════════

def collect_losses():
    """Scrape equipment loss data from Atlantic Council tracker."""
    print("[LOSSES] Fetching Atlantic Council tracker...")
    
    url = "https://www.atlanticcouncil.org/commentary/trackers-and-data-visualizations/tracking-us-military-assets-in-the-iran-war/"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    
    soup = BeautifulSoup(resp.text, "lxml")
    body = soup.get_text()
    
    losses = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "source": "Atlantic Council / Open Source",
        "source_url": url,
        "items": []
    }
    
    # Parse known loss types
    loss_patterns = [
        (r"lost\s+(\w+)\s+MQ-9", "MQ-9 Reaper", "DESTROYED"),
        (r"(\d+)\s+F-15E\s+Strike\s+Eagle", "F-15E Strike Eagle", "DESTROYED"),
        (r"KC-135.*?crash", "KC-135 Stratotanker", "DESTROYED"),
        (r"F-35A.*?(?:damaged|struck|hit)", "F-35A Lightning II", "DAMAGED"),
        (r"(\d+)\s+(?:AN/TPY-2|THAAD)\s+radar", "AN/TPY-2 THAAD Radar", "HIT"),
        (r"AN/FPS-132.*?(?:struck|hit|destroyed)", "AN/FPS-132 Radar", "DESTROYED"),
        (r"Ford.*?(?:fire|repair|Souda)", "USS Gerald R. Ford (CVN-78)", "DAMAGED"),
    ]
    
    for pattern, equipment, status in loss_patterns:
        m = re.search(pattern, body, re.IGNORECASE)
        if m:
            qty_str = m.group(1) if m.lastindex and m.group(1).isdigit() else "1"
            # Convert word numbers
            word_nums = {"one":1,"two":2,"three":3,"four":4,"five":5,"six":6,"seven":7,"eight":8,"nine":9,
                        "ten":10,"eleven":11,"twelve":12,"thirteen":13,"fourteen":14,"fifteen":15}
            if qty_str.lower() in word_nums:
                qty = word_nums[qty_str.lower()]
            elif qty_str.isdigit():
                qty = int(qty_str)
            else:
                qty = 1
            
            losses["items"].append({
                "type": equipment,
                "qty": qty,
                "status": status,
                "source": "Atlantic Council"
            })
    
    # Try to find total cost estimate
    cost_match = re.search(r"\$(\d+\.?\d*)\s*billion", body, re.IGNORECASE)
    if cost_match:
        losses["total_cost_estimate"] = f"${cost_match.group(1)}B"
    
    outpath = DATA_DIR / "losses.json"
    with open(outpath, "w") as f:
        json.dump(losses, f, indent=2)
    
    print(f"[LOSSES] Found {len(losses['items'])} loss entries")
    print(f"[LOSSES] Saved: {outpath}")
    return losses


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("BURGERREICH_watch@ Auto-Collector")
    print(f"Running: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)
    
    errors = []
    
    try:
        collect_fleet()
    except Exception as e:
        print(f"[FLEET] ERROR: {e}")
        errors.append(f"fleet: {e}")
    
    try:
        collect_casualties()
    except Exception as e:
        print(f"[CASUALTIES] ERROR: {e}")
        errors.append(f"casualties: {e}")
    
    try:
        collect_losses()
    except Exception as e:
        print(f"[LOSSES] ERROR: {e}")
        errors.append(f"losses: {e}")
    
    print("=" * 60)
    if errors:
        print(f"[COLLECTOR] Completed with {len(errors)} error(s):")
        for e in errors:
            print(f"  - {e}")
    else:
        print("[COLLECTOR] All sources collected successfully.")
    
    # Write collection status
    status = {
        "last_run": datetime.now(timezone.utc).isoformat(),
        "errors": errors,
        "sources": [
            {"name": "USNI Fleet Tracker", "url": "https://news.usni.org/category/fleet-tracker", "type": "fleet"},
            {"name": "Wikipedia 2026 Iran war", "url": "https://en.wikipedia.org/wiki/2026_Iran_war", "type": "casualties"},
            {"name": "Atlantic Council tracker", "url": "https://www.atlanticcouncil.org/commentary/trackers-and-data-visualizations/tracking-us-military-assets-in-the-iran-war/", "type": "losses"},
        ]
    }
    with open(DATA_DIR / "collector_status.json", "w") as f:
        json.dump(status, f, indent=2)


if __name__ == "__main__":
    main()
