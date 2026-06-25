#!/usr/bin/env python3
"""Turn the curated dealer seed (scraper/dealers_seed.json) into station records.

The seed has addresses but no coordinates (we never fabricate them). This geocodes
each address via OSM Nominatim — free, no API key — and writes normalized records to
data/dealers.json with approx=true (a geocoded pin is street-accurate at best).

ponytail: stdlib only; runs occasionally (dealers change rarely), so its output is
committed and merged into stations.json by scrape_sacdien.py --merge. Not in the
daily CI hot path. Ceiling: Nominatim is rate-limited (1 req/s) and Vietnamese
ward-merge addresses geocode roughly — hence approx=true and a city-fallback query.

Usage:
    python scrape_dealers.py                 # geocode seed -> ../data/dealers.json
    python scrape_dealers.py --self-check    # offline parser/slug assertions
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request

HERE = os.path.dirname(__file__)
SEED = os.path.join(HERE, "dealers_seed.json")
OUT = os.path.join(HERE, "..", "data", "dealers.json")
UA = "SacDienMap/0.1 (non-commercial EV station directory; contact: set-your-email)"
NOMINATIM = "https://nominatim.openstreetmap.org/search"

CITY_NORM = [
    (("hồ chí minh", "ho chi minh", "hcm", "sài gòn", "saigon"), "Ho Chi Minh City"),
    (("hà nội", "hanoi", "ha noi"), "Hanoi"),
    (("đà nẵng", "da nang"), "Da Nang"),
    (("huế", "hue"), "Hue"),
    (("hạ long", "ha long"), "Ha Long"),
]


def slugify(s: str) -> str:
    s = s.replace("đ", "d").replace("Đ", "d")  # not NFD-decomposable; map first
    s = unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode()
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s.lower())).strip("-")


def norm_city(city: str) -> str:
    low = city.lower()
    for needles, name in CITY_NORM:
        if any(n in low for n in needles):
            return name
    return city.split("/")[0].split(",")[0].strip()


def power_of(notes: str | None) -> str | None:
    nums = [int(n) for n in re.findall(r"(\d{2,3})\s*kW", notes or "", re.I)]
    return f"{max(nums)}kW" if nums else None


def connector_of(notes: str | None) -> str | None:
    t = (notes or "")
    found = []
    if re.search(r"CCS2|CCS", t):
        found.append("CCS2")
    if re.search(r"Type ?2|Mennekes", t, re.I):
        found.append("Type 2")
    if re.search(r"CHAdeMO", t, re.I):
        found.append("CHAdeMO")
    return ", ".join(dict.fromkeys(found)) or None


def geocode(query: str) -> tuple[float, float] | None:
    url = f"{NOMINATIM}?" + urllib.parse.urlencode(
        {"q": query, "format": "json", "limit": 1, "countrycodes": "vn"})
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.load(r)
        if data:
            lat, lng = float(data[0]["lat"]), float(data[0]["lon"])
            if 7.0 <= lat <= 24.0 and 101.0 <= lng <= 111.0:  # sanity: inside VN
                return lat, lng
    except Exception as e:  # network / parse — caller falls back / skips
        print(f"  geocode error '{query}': {e}", file=sys.stderr)
    return None


def to_record(d: dict, pos: tuple[float, float]) -> dict:
    return {
        "id": f"dealer:{slugify(d['brand'] + '-' + d['name'])}",
        "source": f"Đại lý {d['brand']}",
        "name": d["name"],
        "brand": d["brand"],
        "lat": round(pos[0], 6),
        "lng": round(pos[1], 6),
        "address": d.get("address"),
        "province": norm_city(d.get("city", "")),
        "phone": d.get("phone"),
        "hours": None,
        "power_kw": power_of(d.get("charger_notes")),
        "connector": connector_of(d.get("charger_notes")),
        "vehicle_types": ["Ô tô điện"],
        "payment": None,
        "url": d.get("source_url"),
        "approx": True,
    }


def run() -> list[dict]:
    seed = json.load(open(SEED, encoding="utf-8"))["dealers"]
    out: list[dict] = []
    for i, d in enumerate(seed):
        pos = (d.get("lat"), d.get("lng")) if d.get("lat") and d.get("lng") else None
        if pos is None:
            city = norm_city(d["city"])
            # Try: full address, then each address part that looks like a street
            # (has a house number or "đường"), each + the normalized city.
            queries = [f"{d['address']}, Vietnam"]
            for part in d["address"].split(","):
                p = part.strip()
                if re.search(r"\d", p) or re.search(r"đường|duong", p, re.I):
                    queries.append(f"{p}, {city}, Vietnam")
            for q in queries:
                pos = geocode(q)
                time.sleep(1.1)  # Nominatim policy: <= 1 req/sec
                if pos:
                    break
        if pos is None:
            print(f"  ! no geocode: {d['name']} ({d['address']})", file=sys.stderr)
            continue
        out.append(to_record(d, pos))
        print(f"  ok {d['brand']:6} {d['name'][:38]:38} -> {pos[0]:.4f},{pos[1]:.4f}",
              file=sys.stderr)
    return out


def self_check() -> None:
    assert slugify("Audi Hồ Chí Minh (Quận 1)") == "audi-ho-chi-minh-quan-1"
    assert slugify("BYD Đà Nẵng") == "byd-da-nang"
    assert norm_city("Ho Chi Minh City") == "Ho Chi Minh City"
    assert norm_city("TP. Hồ Chí Minh") == "Ho Chi Minh City"
    assert norm_city("Ha Long, Quảng Ninh") == "Ha Long"
    assert power_of("DC 180 kW (ABB) plus AC 11 kW") == "180kW"
    assert power_of("no numbers here") is None
    assert connector_of("DC fast 120 kW CCS2 and Type 2") == "CCS2, Type 2"
    r = to_record({"brand": "Audi", "name": "Audi Hà Nội", "address": "8 Phạm Hùng, Hà Nội",
                   "city": "Hà Nội", "charger_notes": "DC 180 kW CCS2"}, (21.0, 105.78))
    assert r["id"] == "dealer:audi-audi-ha-noi" and r["source"] == "Đại lý Audi"
    assert r["approx"] is True and r["power_kw"] == "180kW" and r["province"] == "Hanoi"
    assert r["vehicle_types"] == ["Ô tô điện"]
    print("self-check OK")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-check", action="store_true")
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()
    if args.self_check:
        self_check()
        return
    records = run()
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    json.dump({"count": len(records), "stations": records},
              open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"Wrote {len(records)} dealer stations -> {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
