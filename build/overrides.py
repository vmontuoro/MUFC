"""Manual fixture overrides — moves the club has requested but Dribl doesn't show yet.

`overrides.json` (same folder) is a list of records saved from the clash page's
"Copy/Download overrides JSON" button:

    [{"gkey": "2026-08-15|Pettys Reserve|Pitch 1E (Bottom Field)|08:30|Manningham ...",
      "iso": "2026-08-15", "to_ground": "Pettys Reserve", "to_field": "2",
      "to_pitch": "Pitch 2", ...}]

`gkey` is  iso|ground|pitch|time|home  (see gen_clashes.gkey_of) and is what ties a
record to a parsed fixture. Applying an override rewrites that game's ground/field/pitch
so clash detection runs against the *proposed* day; the original location is kept on
`moved_from` so the page can still show what it was.
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "overrides.json")


def load():
    """Read overrides.json -> list (missing/empty/corrupt file yields [])."""
    if not os.path.exists(PATH):
        return []
    try:
        with open(PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (ValueError, OSError) as e:
        print("  ! overrides.json ignored (%s)" % e)
        return []


def dates(ovr=None):
    """{iso: count} — used by refresh.py to report what is overridden."""
    out = {}
    for o in (load() if ovr is None else ovr):
        iso = o.get("iso") or o.get("gkey", "|").split("|")[0]
        out[iso] = out.get(iso, 0) + 1
    return out


def apply(games, gkey_of):
    """Rewrite overridden games in place. Returns the number applied."""
    ovr = load()
    if not ovr:
        return 0
    by_key = {o.get("gkey"): o for o in ovr if o.get("gkey")}
    n = 0
    for g in games:
        o = by_key.get(gkey_of(g))
        if not o:
            continue
        # gen_duties games have no "field" key — keep this tolerant of both game shapes
        g["moved_from"] = {"ground": g["ground"], "pitch": g["pitch"], "field": g.get("field", "")}
        g["override"] = True
        g["ground"] = o.get("to_ground", g["ground"])
        g["field"] = str(o.get("to_field", g.get("field", "")))
        g["pitch"] = o.get("to_pitch") or ("Pitch " + g["field"])
        n += 1
    return n
