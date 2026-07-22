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


class OverridesError(RuntimeError):
    """overrides.json exists but is unusable — never swallowed."""


def load():
    """Read overrides.json -> list. A missing file yields []; a corrupt one RAISES.

    This deliberately does not fall back to []. The file is hand-edited between
    refreshes, and quietly ignoring a stray comma would regenerate every page with
    all manual moves dropped — a published site that looks perfectly healthy while
    silently sending teams back to the pitches they were moved off.
    """
    if not os.path.exists(PATH):
        return []
    try:
        with open(PATH, encoding="utf-8") as f:
            data = json.load(f)
    except (ValueError, OSError) as e:
        raise OverridesError(
            "%s is unreadable (%s).\n"
            "     Fix the file (or delete it if the moves are no longer wanted) and re-run —\n"
            "     refusing to publish with the manual moves silently dropped." % (PATH, e)) from e
    if not isinstance(data, list):
        raise OverridesError("%s must hold a JSON list of override records, got %s"
                             % (PATH, type(data).__name__))
    return data


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
    unmatched = set(by_key)
    n = 0
    for g in games:
        key = gkey_of(g)
        o = by_key.get(key)
        if not o:
            continue
        unmatched.discard(key)
        # gen_duties games have no "field" key — keep this tolerant of both game shapes
        g["moved_from"] = {"ground": g["ground"], "pitch": g["pitch"], "field": g.get("field", "")}
        g["override"] = True
        g["ground"] = o.get("to_ground", g["ground"])
        g["field"] = str(o.get("to_field", g.get("field", "")))
        g["pitch"] = o.get("to_pitch") or ("Pitch " + g["field"])
        n += 1
    if unmatched:
        # A gkey that ties to no fixture does nothing at all — the move just never
        # happens. Loud, because the page still renders fine without it.
        print("  ! %d override(s) matched NO fixture and had no effect:" % len(unmatched))
        for k in sorted(unmatched):
            print("      %s" % k)
    return n
