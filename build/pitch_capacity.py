"""The club's pitch-capacity convention — the single source of truth for "is this a clash?".

A physical pitch is worth 1.0. Age groups consume a share of it, so several small-sided
games legitimately share one field:

    U14+ / Seniors  1.0   (and must have the pitch to themselves)
    U10-U13         0.5
    U6-U9           0.25
    All-Abilities   0.5

A field is OVER CAPACITY when the games running at the same moment sum to more than 1.0.

This module exists because a simpler "two games on one field = clash" rule disagrees with
the convention: it flags four MiniRoos games sharing a quarter-pitched field as four
double-bookings. gen_clashes.py, gen_fixtures.py and gen_xlsx.py all import from here so
the published pages cannot drift apart on what counts as a clash.
"""

UNIT = {"TINY": .25, "SMALL": .25, "AAL": .5, "MID": .5, "BIG": 1.0}
CATLABEL = {"TINY": "U6/7", "SMALL": "U8/9", "MID": "U10-13", "BIG": "U14+", "AAL": "All-Abilities"}

BIG_ALONE = "U14+ must have the pitch to itself"
OVER_CAP = "Pitch over capacity"


def category(age, comp):
    """Age token (e.g. 'U09') + competition name -> capacity category."""
    if comp == "Girls Clinic":
        return "MID"
    if "All Abilities" in comp:
        return "AAL"
    if age in ("U06", "U07"):
        return "TINY"
    if age in ("U08", "U09"):
        return "SMALL"
    if age in ("U10", "U11", "U12", "U13"):
        return "MID"
    return "BIG"


def conflicts(games, key):
    """Find over-capacity moments.

    `games` need start/end (minutes) plus a "cat" key; `key(g)` returns whatever groups
    games onto one physical field (typically ground + date + field number).

    Yields dicts: {key, at, until, games, rule, units, mix}. One entry per distinct set of
    simultaneous games, so a three-way pile-up is reported once rather than three times.
    """
    buckets = {}
    for g in games:
        buckets.setdefault(key(g), []).append(g)
    out, seen = [], set()
    for k, gs in buckets.items():
        for t in sorted({g["start"] for g in gs}):
            active = [g for g in gs if g["start"] <= t < g["end"]]
            if len(active) < 2:
                continue
            sig = (k, tuple(sorted(id(x) for x in active)))
            if sig in seen:
                continue
            units = round(sum(UNIT[g["cat"]] for g in active), 3)
            nbig = sum(1 for g in active if g["cat"] == "BIG")
            rule = BIG_ALONE if nbig >= 1 else (OVER_CAP if units > 1.0 else None)
            if not rule:
                continue
            seen.add(sig)
            cnt = {}
            for g in active:
                cnt[g["cat"]] = cnt.get(g["cat"], 0) + 1
            out.append(dict(key=k, at=t, until=min(g["end"] for g in active), games=active, rule=rule,
                            units=units,
                            mix=", ".join("%d×%s" % (cnt[c], CATLABEL[c])
                                          for c in ["BIG", "MID", "SMALL", "TINY", "AAL"] if c in cnt)))
    return out
