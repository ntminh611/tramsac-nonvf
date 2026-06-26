#!/usr/bin/env python3
"""Scrape non-VinFast public charging stations from sacdien.net.

Source of truth is the RankMath JSON-LD (`<script type="application/ld+json">`)
embedded in every /tram/ page — structured, stable, far less brittle than DOM
scraping. We enumerate every station URL from the WordPress sitemaps, fetch each
page, and pull the `ElectricVehicleChargingStation` node out of the @graph.

ponytail: stdlib only (urllib/json/re) so this runs in GitHub Actions with zero
`pip install`. Brand is derived by keyword-matching the slug/name against the
site's known brand list — good enough; the AJAX-only brand taxonomy isn't worth
reverse-engineering for a sparse, secondary filter field.

Usage:
    python scrape_sacdien.py                 # full run -> ../data/stations.json
    python scrape_sacdien.py --limit 30      # quick sample
    python scrape_sacdien.py --self-check    # offline-ish parser assertions
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import gzip
import html
import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime, timezone

BASE = "https://sacdien.net"
SITEMAPS = [f"{BASE}/tram-sitemap{i}.xml" for i in range(1, 7)]
UA = "SacDienMap/0.1 (+https://github.com/; non-commercial EV station directory)"
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "stations.json")

# Brand slug -> display name. Order matters: longest/most-specific first so that
# e.g. "evercharge"/"bitcharge"/"dat-charge" win before the generic "charge".
BRANDS: list[tuple[str, str]] = [
    ("evercharge", "EverCharge"),
    ("esky-charge", "Esky Charge"),
    ("vt-charging", "VT Charging"),
    ("dat-charge", "Dat Charge"),
    ("co-charge", "Co-Charge"),
    ("rabbit-evc", "Rabbit EVC"),
    ("bitcharge", "BitCharge"),
    ("ev-power", "EV Power"),
    ("evia-hcx", "Evia HCX"),
    ("solarev", "SolarEV"),
    ("eboost", "EBOOST"),
    ("ev-one", "EV One"),
    ("evpay", "EVPay"),
    ("charge", "Charge"),
    ("evg", "EVG"),
]
# Anything matching these is excluded — the app is explicitly *non*-VinFast.
VINFAST_RE = re.compile(r"\b(vinfast|v-?green|vgreen)\b", re.I)


def in_vietnam(lat: float, lng: float) -> bool:
    """Generous VN bounding box — rejects garbage coords like lat=90 (real
    data-entry error seen on sacdien) while keeping every genuine station."""
    return 7.0 <= lat <= 24.0 and 101.0 <= lng <= 111.0

LD_RE = re.compile(
    r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.I | re.S,
)

# Price isn't in the JSON-LD — sacdien puts it in a body heading like
# "• Đơn giá: 7k đồng /kWh" (or "Đơn giá: Miễn phí"). Best-effort, often absent.
PRICE_RE = re.compile(r"Đơn giá\s*:?\s*([^<\n]{1,50})", re.I)


def extract_price(page: str) -> str | None:
    m = PRICE_RE.search(page)
    if not m:
        return None
    v = html.unescape(re.sub(r"\s+", " ", m.group(1))).strip(" :·•–-—")
    return v.replace(" /", "/") or None

# A top-level VN province/city looks like "TP. Đà Nẵng" / "Thành phố X" / "Tỉnh Y".
# sacdien's addressRegion is unreliable (often a district), so we hunt this shape.
PROV_RE = re.compile(r"(TP\.\s*[^,\-–—]+|Thành phố\s+[^,\-–—]+|Tỉnh\s+[^,\-–—]+)")


def pick_province(candidates: list[str | None]) -> str | None:
    for c in candidates:
        if not c:
            continue
        # "Phường X - TP. Y" -> prefer the segment after the last dash
        tail = re.split(r"\s[-–—]\s", c)[-1]
        m = PROV_RE.search(tail) or PROV_RE.search(c)
        if m:
            return _clean(m.group(1))
    # nothing matched the TP./Tỉnh shape — fall back to the first non-empty candidate
    return next((_clean(c) for c in candidates if c), None)


def fetch(url: str, retries: int = 3, timeout: int = 25) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip"})
    last = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                return raw.decode("utf-8", "replace")
        except (urllib.error.URLError, TimeoutError) as e:  # transient
            last = e
    raise RuntimeError(f"fetch failed: {url} ({last})")


def station_urls() -> list[str]:
    urls: list[str] = []
    for sm in SITEMAPS:
        xml = fetch(sm)
        urls += re.findall(r"<loc>\s*(https://sacdien\.net/tram/[^<\s]+?)\s*</loc>", xml)
    # de-dup, keep order
    seen: set[str] = set()
    return [u for u in urls if not (u in seen or seen.add(u))]


def brand_of(slug_and_name: str) -> str | None:
    hay = f"-{slug_and_name.lower()}-"
    for slug, name in BRANDS:
        if f"-{slug}-" in hay or f" {slug} " in f" {slug_and_name.lower()} ":
            return name
    return None


def _ascii_key(s: str) -> str:
    """Diacritic-stripped key for comparing place names — collapses Vietnamese
    tone-mark variants ('Hòa Quý' == 'Hoà Quý') that are different Unicode."""
    s = (s or "").replace("đ", "d").replace("Đ", "d")
    s = unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", s.lower())


def dedup_address(addr: str) -> str:
    """Drop repeated comma-atoms (e.g. a ward listed in both streetAddress and
    addressLocality, often as a tone-mark variant) keeping first occurrence."""
    seen: set[str] = set()
    out: list[str] = []
    for atom in (addr or "").split(","):
        atom = atom.strip()
        k = _ascii_key(atom)
        if atom and k and k not in seen:
            seen.add(k)
            out.append(atom)
    return ", ".join(out)


def _clean(v: str | None) -> str | None:
    if not v:
        return None
    v = html.unescape(re.sub(r"<[^>]+>", " ", v))  # strip stray html + decode entities
    v = re.sub(r"\s+", " ", v).strip(" -–—\t")
    # values like "kW -" / "kW" carry no real info
    return v or None if v.lower() not in {"kw", "kw -", "-"} else None


def find_station_node(ld_blocks: list) -> dict | None:
    """Return the ElectricVehicleChargingStation / LocalBusiness node from JSON-LD."""
    nodes: list[dict] = []
    for block in ld_blocks:
        graph = block.get("@graph") if isinstance(block, dict) else None
        nodes += graph if isinstance(graph, list) else [block]
    for n in nodes:
        if not isinstance(n, dict):
            continue
        t = n.get("@type", "")
        types = t if isinstance(t, list) else [t]
        add = n.get("additionalType", "")
        if "LocalBusiness" in types or "ElectricVehicleChargingStation" in str(add) + str(types):
            if n.get("geo"):
                return n
    return None


def parse_station(url: str, html: str) -> dict | None:
    blocks = []
    for raw in LD_RE.findall(html):
        try:
            blocks.append(json.loads(raw.strip()))
        except json.JSONDecodeError:
            continue
    node = find_station_node(blocks)
    if not node:
        return None

    geo = node.get("geo") or {}
    try:
        lat, lng = float(geo["latitude"]), float(geo["longitude"])
    except (KeyError, TypeError, ValueError):
        return None
    if not in_vietnam(lat, lng):  # drops data-entry garbage (e.g. lat=90)
        return None

    addr = node.get("address") or {}
    new_prov = next((_clean(p.get("value")) for p in node.get("additionalProperty") or []
                     if isinstance(p, dict) and p.get("name") == "New Province/City"), None)
    province = pick_province([new_prov, addr.get("addressRegion"),
                              addr.get("addressLocality"), addr.get("streetAddress")])
    # streetAddress usually already spells out ward+district+province; join the
    # JSON-LD parts then drop repeated atoms (diacritic-insensitive) so a ward
    # doesn't show twice as "Hòa Quý ... Hoà Quý".
    raw = ", ".join(p for p in (_clean(addr.get("streetAddress")),
                                _clean(addr.get("extendedAddress")),
                                _clean(addr.get("addressLocality")), province) if p)
    address = dedup_address(raw)

    connector = power = None
    vehicle_types: list[str] = []
    for feat in node.get("amenityFeature") or []:
        if not isinstance(feat, dict):
            continue
        name, val = feat.get("name", ""), _clean(feat.get("value"))
        if name == "Charging Type":
            connector = val
        elif name == "Output Power":
            power = val
        elif name == "For e-Vehicle Type" and val:
            vehicle_types = [v.strip() for v in re.split(r"[,/]", val) if v.strip()]

    slug = url.rstrip("/").rsplit("/", 1)[-1]
    name = _clean(node.get("name")) or slug
    if VINFAST_RE.search(f"{slug} {name} {address}"):
        return None  # explicitly excluded

    # dateModified (from the WebPage node) = when the listing was last edited.
    # Not live status, but a real freshness signal for "is this still around".
    last_updated = None
    for b in blocks:
        graph = b.get("@graph") if isinstance(b, dict) else None
        for n in (graph if isinstance(graph, list) else [b]):
            if isinstance(n, dict) and n.get("dateModified"):
                last_updated = str(n["dateModified"])[:10]
                break
        if last_updated:
            break

    return {
        "id": f"sacdien:{slug}",
        "source": "sacdien.net",
        "name": name,
        "brand": brand_of(f"{slug} {name}"),
        "lat": round(lat, 6),
        "lng": round(lng, 6),
        "address": address or None,
        "province": _clean(province),
        "phone": _clean(node.get("telephone")),
        "hours": _clean(node.get("openingHours")),
        "power_kw": power,
        "connector": connector,
        "vehicle_types": vehicle_types,
        "payment": _clean(node.get("paymentAccepted")),
        "price": extract_price(html),
        "last_updated": last_updated,
        "url": url,
    }


def _haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    from math import asin, cos, radians, sin, sqrt
    (la1, lo1), (la2, lo2) = a, b
    dla, dlo = radians(la2 - la1), radians(lo2 - lo1)
    h = sin(dla / 2) ** 2 + cos(radians(la1)) * cos(radians(la2)) * sin(dlo / 2) ** 2
    return 2 * 6371000 * asin(sqrt(h))


def merge_extra(stations: list[dict], path: str, near_m: float = 150) -> list[dict]:
    """Append extra source records (e.g. geocoded dealers), dropping any that sit
    within `near_m` of an existing station (same charger already covered)."""
    try:
        with open(path, encoding="utf-8") as f:
            extra = json.load(f)
        extra = extra.get("stations", extra) if isinstance(extra, dict) else extra
    except (OSError, json.JSONDecodeError) as e:
        print(f"  merge skipped ({path}): {e}", file=sys.stderr)
        return stations
    pts = [(s["lat"], s["lng"]) for s in stations]
    kept = 0
    for d in extra:
        here = (d["lat"], d["lng"])
        if any(_haversine_m(here, p) < near_m for p in pts):
            continue  # already represented by a nearby station
        stations.append(d)
        pts.append(here)
        kept += 1
    print(f"  merged {kept}/{len(extra)} from {path} ({len(extra) - kept} dedup'd)", file=sys.stderr)
    return stations


def scrape_one(url: str) -> dict | None:
    try:
        return parse_station(url, fetch(url))
    except Exception as e:  # one bad page shouldn't kill the run
        print(f"  ! {url}: {e}", file=sys.stderr)
        return None


def run(limit: int | None, workers: int) -> list[dict]:
    urls = station_urls()
    if limit:
        urls = urls[:limit]
    print(f"Found {len(urls)} station URLs; fetching with {workers} workers...", file=sys.stderr)
    out: list[dict] = []
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        for i, st in enumerate(ex.map(scrape_one, urls), 1):
            if st:
                out.append(st)
            if i % 100 == 0:
                print(f"  ...{i}/{len(urls)} ({len(out)} parsed)", file=sys.stderr)
    return out


# --- ponytail: one runnable check — parser must survive the real JSON-LD shape ---
SAMPLE = '''<script type="application/ld+json" class="rank-math-schema-pro">
{"@context":"https://schema.org","@graph":[
{"@type":"LocalBusiness","additionalType":"https://schema.org/ElectricVehicleChargingStation",
"name":"Trạm sạc EV Power - OMODA","description":"<p>x</p>",
"url":"https://sacdien.net/tram/tram-sac-ev-power-omoda-jaecoo-thanh-hoa/",
"address":{"@type":"PostalAddress","streetAddress":"1 Lê Lợi","addressLocality":"P. A",
"extendedAddress":"Q. B","addressRegion":"Thanh Hóa","addressCountry":"VN"},
"geo":{"@type":"GeoCoordinates","latitude":"19.80123","longitude":"105.77654"},
"openingHours":"Mở cửa","telephone":"0900000000","paymentAccepted":"QR Code, Tiền mặt",
"amenityFeature":[{"@type":"LocationFeatureSpecification","name":"Charging Type","value":"CCS2"},
{"@type":"LocationFeatureSpecification","name":"Output Power","value":"60 kW"},
{"@type":"LocationFeatureSpecification","name":"For e-Vehicle Type","value":"Ô tô điện"}],
"additionalProperty":[{"@type":"PropertyValue","name":"New Province/City","value":"Thanh Hóa"}]},
{"@type":"WebPage","dateModified":"2026-05-01T10:00:00+07:00"},
{"@type":"Organization","name":"SacDien.NET"}]}</script>
<h2 class="elementor-heading-title">• Đơn giá: 7k đồng /kWh</h2>'''


def self_check() -> None:
    u = "https://sacdien.net/tram/tram-sac-ev-power-omoda-jaecoo-thanh-hoa/"
    s = parse_station(u, SAMPLE)
    assert s, "should parse the sample station"
    assert s["lat"] == 19.80123 and s["lng"] == 105.77654, s
    assert s["brand"] == "EV Power", s["brand"]
    assert s["connector"] == "CCS2" and s["power_kw"] == "60 kW", s
    assert s["vehicle_types"] == ["Ô tô điện"], s
    assert s["province"] == "Thanh Hóa" and "Thanh Hóa" in s["address"], s
    assert s["price"] == "7k đồng/kWh", s["price"]
    # tone-mark variant ward must collapse, not repeat at the end
    assert dedup_address("126 X, Phường Hòa Quý, Quận Y, TP. Đà Nẵng, Phường Hoà Quý") == \
        "126 X, Phường Hòa Quý, Quận Y, TP. Đà Nẵng", "ward should dedup across tone variants"
    assert _clean("Lynk &amp; Co") == "Lynk & Co", "html entities must decode"
    assert s["last_updated"] == "2026-05-01", s["last_updated"]
    assert s["id"] == "sacdien:tram-sac-ev-power-omoda-jaecoo-thanh-hoa", s["id"]
    # brand disambiguation: generic "charge" must lose to specific brands
    assert brand_of("tram-sac-evercharge-hue") == "EverCharge"
    assert brand_of("tram-sac-bitcharge-hanoi") == "BitCharge"
    assert brand_of("tram-sac-charge-autocare-hanoi") == "Charge"
    assert brand_of("green-coffee-tan-phu") is None
    # vinfast must be excluded
    assert parse_station("https://sacdien.net/tram/vinfast-q1/",
                         SAMPLE.replace("EV Power - OMODA", "VinFast Q1")) is None
    # out-of-Vietnam garbage coords must be dropped (real case: lat=90)
    assert parse_station(u, SAMPLE.replace('"19.80123"', '"90.0"')) is None
    assert in_vietnam(10.78, 106.7) and not in_vietnam(90.0, 106.7)
    print("self-check OK")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--self-check", action="store_true")
    ap.add_argument("--merge", action="append", default=[],
                    help="extra stations JSON to merge in (repeatable), e.g. dealers")
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()

    if args.self_check:
        self_check()
        return

    stations = run(args.limit, args.workers)
    for path in args.merge:
        stations = merge_extra(stations, path)
    stations.sort(key=lambda s: (s.get("province") or "~", s["name"]))
    counts: dict[str, int] = {}
    for s in stations:
        counts[s["source"]] = counts.get(s["source"], 0) + 1
    doc = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_counts": counts,
        "count": len(stations),
        "stations": stations,
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print(f"Wrote {len(stations)} stations -> {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
