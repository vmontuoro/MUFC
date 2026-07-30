#!/usr/bin/env python3
"""Server-side capture of Manningham United Blues' full-season home fixtures from
Dribl's JSON API, one file per ground -> build/raw_<ground>.txt (8-line format that
dribl_parse.py consumes). Pure stdlib so it runs on a bare GitHub Actions runner.

This replaces the browser/get_page_text capture used inside Cowork: a GitHub Actions
runner has open egress and can hit mc-api.dribl.com directly, which the Cowork sandbox
cannot. If Dribl ever bot-blocks non-browser requests this is where it will surface
(HTTP 403); adjust the User-Agent / headers below if so.

Season / tenant / ground IDs may change each season -- grab fresh ones from the ground
filter URLs on fv.dribl.com if a run comes back empty.
"""
import json, sys, time, urllib.request, urllib.error, urllib.parse
from datetime import datetime
from zoneinfo import ZoneInfo
import os

SEASON = "nPmrj2rmow"
TENANT = "w8zdBWPmBX"
GROUNDS = {                      # filename stem -> (ground id, sane minimum count)
    "pettys":  ("gld49gj0mW", 250),
    "powl":    ("AnmYl5x1dz", 150),
    "timber":  ("jJmXYXRWNn", 0),
    "wilsons": ("gld4npypNW", 0),   # real Wilsons Rd Reserve id; expected 0 fixtures
}
SYD = ZoneInfo("Australia/Sydney")
HERE = os.path.dirname(os.path.abspath(__file__))
HEADERS = {
    "Accept": "application/json",
    # Browser-like UA in case Dribl filters obvious bots. Harmless if not needed.
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
}


def _get(url, tries=4):
    last = None
    for n in range(tries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            last = e
            time.sleep(2 * (n + 1))
    raise SystemExit(f"FATAL: could not fetch {url}\n  last error: {last}")


def fetch_ground(gid):
    base = (f"https://mc-api.dribl.com/api/fixtures"
            f"?season={SEASON}&tenant={TENANT}&ground={gid}")
    url, out, guard = base, [], 0
    while url and guard < 200:
        guard += 1
        j = _get(url)
        out.extend(j.get("data", []))
        nxt = (j.get("links") or {}).get("next")
        if not nxt:
            break
        # links.next drops the query params -> lift just the cursor onto the full base
        cur = urllib.parse.parse_qs(urllib.parse.urlparse(nxt).query).get("cursor", [None])[0]
        if not cur:
            break
        url = base + "&cursor=" + urllib.parse.quote(cur)
    return out


def fmt(a):
    d = datetime.fromisoformat(a["date"].replace("Z", "+00:00")).astimezone(SYD)
    return "\n".join([
        d.strftime("%a %d %b %Y"),          # e.g. Sat 17 Jan 2026
        d.strftime("%H:%M"),                # 24h Sydney
        a["home_team_name"],
        "-",
        a["away_team_name"],
        f'{a["competition_name"]} | {a["league_name"]}',
        f'{a["ground_name"]} {a["field_name"]}',
        a.get("full_round", ""),
    ])


def main():
    summary = []
    ok = True
    for stem, (gid, floor) in GROUNDS.items():
        rows = fetch_ground(gid)
        text = "\n\n".join(fmt(f["attributes"]) for f in rows)
        path = os.path.join(HERE, f"raw_{stem}.txt")
        # Guard: never overwrite a good capture with a short/empty one.
        if len(rows) < floor:
            print(f"!! {stem}: {len(rows)} fixtures < expected minimum {floor} "
                  f"-- NOT writing (possible partial capture / API change)")
            ok = False
            continue
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        dates = sorted(f["attributes"]["date"] for f in rows) if rows else []
        span = (f'{datetime.fromisoformat(dates[0].replace("Z","+00:00")).astimezone(SYD):%d %b}'
                f' -> {datetime.fromisoformat(dates[-1].replace("Z","+00:00")).astimezone(SYD):%d %b}'
                ) if dates else "(empty)"
        summary.append((stem, len(rows), span))
        print(f"   {stem}: {len(rows)} fixtures  [{span}]  -> {os.path.basename(path)}")
    if not ok:
        raise SystemExit("Capture failed a sanity floor -- see messages above. "
                         "Existing raw_*.txt left untouched.")
    print("\nCapture OK:", ", ".join(f"{s}={n}" for s, n, _ in summary))


if __name__ == "__main__":
    main()
