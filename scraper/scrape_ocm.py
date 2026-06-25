#!/usr/bin/env python3
"""Pull Vietnam non-VinFast charging stations from the OpenChargeMap (OCM) API.

OCM is an open, crowd-sourced global registry. Unlike sacdien.net it carries an
explicit operational status (StatusType.IsOperational) and a last-verified date —
the best available signal for "is this charger still alive" short of the operator's
own app (real-time availability is not in any open source).

Needs a FREE api key: register at https://openchargemap.org -> My Apps -> get key.
Pass it via --key or the OCM_API_KEY env var.

ponytail: stdlib only. Output (data/ocm.json) is merged into stations.json by
scrape_sacdien.py --merge, with the same proximity dedup that drops overlaps.

Usage:
    OCM_API_KEY=xxxx python scrape_ocm.py        # -> ../data/ocm.json
    python scrape_ocm.py --key xxxx --max 2000
    python scrape_ocm.py --self-check            # offline mapping assertions
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "ocm.json")
API = "https://api.openchargemap.io/v3/poi/"
VINFAST_RE = re.compile(r"vinfast|v-?green|vgreen", re.I)


def fetch_pois(key: str, max_results: int) -> list[dict]:
    q = urllib.parse.urlencode({
        "output": "json", "countrycode": "VN", "maxresults": max_results,
        "compact": "false", "verbose": "true", "key": key,
    })
    req = urllib.request.Request(API + "?" + q, headers={"User-Agent": "SacDienMap/0.1"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.load(r)


def _max_power(connections: list) -> str | None:
    kw = [c.get("PowerKW") for c in connections or [] if isinstance(c, dict) and c.get("PowerKW")]
    return f"{int(max(kw))}kW" if kw else None


def _connectors(connections: list) -> str | None:
    names = []
    for c in connections or []:
        ct = (c or {}).get("ConnectionType") or {}
        if ct.get("Title"):
            names.append(ct["Title"])
    return ", ".join(dict.fromkeys(names)) or None


def to_record(poi: dict) -> dict | None:
    ai = poi.get("AddressInfo") or {}
    lat, lng = ai.get("Latitude"), ai.get("Longitude")
    if lat is None or lng is None:
        return None
    if not (7.0 <= float(lat) <= 24.0 and 101.0 <= float(lng) <= 111.0):
        return None  # sanity: inside Vietnam
    op = (poi.get("OperatorInfo") or {}).get("Title")
    st = poi.get("StatusType") or {}
    operational = st.get("IsOperational")  # True / False / None(unknown)

    name = ai.get("Title") or "Trạm sạc"
    if VINFAST_RE.search(f"{name} {op or ''}"):
        return None  # non-VinFast only

    address = ", ".join(p for p in dict.fromkeys(
        filter(None, [ai.get("AddressLine1"), ai.get("Town"), ai.get("StateOrProvince")])))
    updated = (poi.get("DateLastStatusUpdate") or poi.get("DateLastVerified") or "")[:10] or None

    return {
        "id": f"ocm:{poi.get('ID')}",
        "source": "OpenChargeMap",
        "name": name,
        "brand": op if op and op.lower() not in ("(unknown operator)", "unknown") else None,
        "lat": round(float(lat), 6),
        "lng": round(float(lng), 6),
        "address": address or None,
        "province": ai.get("StateOrProvince") or ai.get("Town"),
        "phone": ai.get("ContactTelephone1"),
        "hours": None,
        "power_kw": _max_power(poi.get("Connections")),
        "connector": _connectors(poi.get("Connections")),
        "vehicle_types": ["Ô tô điện"],  # OCM POIs are overwhelmingly car AC/DC
        "payment": None,
        "operational": operational,
        "last_updated": updated,
        "url": ai.get("RelatedURL") or f"https://openchargemap.io/site/poi/details/{poi.get('ID')}",
    }


def self_check() -> None:
    sample = {
        "ID": 12345,
        "AddressInfo": {"Title": "Mercedes Haxaco Q1", "AddressLine1": "1 Lê Duẩn",
                        "Town": "Quận 1", "StateOrProvince": "TP. Hồ Chí Minh",
                        "Latitude": 10.78, "Longitude": 106.7, "ContactTelephone1": "0900"},
        "OperatorInfo": {"Title": "EverEV"},
        "StatusType": {"IsOperational": True, "Title": "Operational"},
        "DateLastVerified": "2026-03-15T00:00:00Z",
        "Connections": [
            {"ConnectionType": {"Title": "CCS (Type 2)"}, "PowerKW": 60},
            {"ConnectionType": {"Title": "Type 2"}, "PowerKW": 22},
        ],
    }
    r = to_record(sample)
    assert r["id"] == "ocm:12345" and r["source"] == "OpenChargeMap", r
    assert r["brand"] == "EverEV" and r["operational"] is True, r
    assert r["power_kw"] == "60kW", r["power_kw"]
    assert r["connector"] == "CCS (Type 2), Type 2", r["connector"]
    assert r["province"] == "TP. Hồ Chí Minh" and r["last_updated"] == "2026-03-15", r
    # VinFast must be dropped
    vin = dict(sample, OperatorInfo={"Title": "V-GREEN"})
    assert to_record(vin) is None
    # missing coords -> dropped
    assert to_record({"ID": 1, "AddressInfo": {"Title": "x"}}) is None
    print("self-check OK")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", default=os.environ.get("OCM_API_KEY", ""))
    ap.add_argument("--max", type=int, default=5000)
    ap.add_argument("--self-check", action="store_true")
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()
    if args.self_check:
        self_check()
        return
    if not args.key:
        sys.exit("Need an OpenChargeMap API key: --key <key> or OCM_API_KEY env. "
                 "Get a free one at https://openchargemap.org -> My Apps.")
    pois = fetch_pois(args.key, args.max)
    records = [r for r in (to_record(p) for p in pois) if r]
    n_op = sum(1 for r in records if r["operational"] is True)
    n_bad = sum(1 for r in records if r["operational"] is False)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    json.dump({"count": len(records), "stations": records},
              open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"Wrote {len(records)} OCM stations ({n_op} operational, {n_bad} reported down) "
          f"from {len(pois)} VN POIs -> {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
