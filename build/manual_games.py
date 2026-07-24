"""Manually-added games (NOT from Dribl). Merged into every generator so they survive refresh.

Recurring every SATURDAY match day at Pettys Reserve:
  - All-Abilities : 10:00-11:30, Pitch 2 (Top Field)            (AAL, quarter pitch)
  - Girls Clinic  : 09:00-10:00, auto-placed on a free HALF pitch (1A/1B/2A/2B)

FRIDAY_O45: the Over 45 Men's Friday-night season (7:30pm). Never in the FV/Dribl fixture, and
ALWAYS physically played at Pettys — even the rounds whose fixture designates MUFC as "Away"
(an oddity of that competition; those rounds list the opponent as the home side). Preference is
the bottom pitch (Pitch 1) unless Dribl already has something on it that evening, then Pitch 2.

Manual games are flagged by the MARK suffix on the NON-Manningham side's name (bare MARK when
there is no real opponent). Generators must use is_manual()/strip_mark() rather than comparing
against MARK directly. Returns tuples shaped like dribl_parse.read():
(date_s,time_s,home,away,comp,pitch,rnd)
"""
MARK = "[MANUAL ADD]"
HALVES = ["Pitch 1A (Bottom Field)", "Pitch 1B (Bottom Field)",
          "Pitch 2A (Top Field)", "Pitch 2B (Top Field)"]

O45_TEAM = "Manningham United Blues FC Over 45 Men"
O45_COMP = "Masters Over 45 Friday Night"
# (round, date exactly as Dribl formats it, opponent, MUFC is the designated home side)
FRIDAY_O45 = [
    ("Round 2",  "Fri 10 Jul 2026", "Eltham Green",  True),
    ("Round 3",  "Fri 17 Jul 2026", "Eltham Red",    True),
    ("Round 4",  "Fri 24 Jul 2026", "Eltham Black",  True),
    ("Round 5",  "Fri 31 Jul 2026", "Eltham Blue",   True),
    ("Round 7",  "Fri 21 Aug 2026", "Eltham Orange", True),
    ("Round 9",  "Fri 4 Sep 2026",  "Eltham Blue",   False),
    ("Round 10", "Fri 11 Sep 2026", "Eltham Black",  False),
    ("Round 13", "Fri 9 Oct 2026",  "Eltham White",  True),
    ("Round 16", "Fri 30 Oct 2026", "Eltham Red",    False),
    ("Round 17", "Fri 6 Nov 2026",  "Diamond Creek", True),
]


def is_manual(home, away):
    """A game is manual when either side carries the MARK suffix."""
    return MARK in home or MARK in away


def strip_mark(name):
    """Remove the MARK suffix from a real name; a bare MARK (opponent-less event) is kept
    as-is — it IS that side's display text on the clash/fixtures pages."""
    s = name.replace(MARK, "").strip()
    return s or name.strip()


def _dur(s):  # rough occupancy length for the free-pitch check
    if "MiniRoos" in s or any(u in s for u in ("U07", "U08", "U09", "U10", "U11")): return 40
    if "Seniors" in s or "Reserve" in s or "Over 45" in s: return 90
    return 60

def build(pettys_tuples, parse_date):
    from collections import defaultdict
    occ = defaultdict(list); dates = {}
    for date_s, time_s, home, away, comp, pitch, rnd in pettys_tuples:
        d = parse_date(date_s); dates[d.isoformat()] = (d, date_s)
        hh, mm = map(int, time_s.split(":")); start = hh * 60 + mm
        sub = pitch.replace("Pettys Reserve", "").strip()
        occ[(d.isoformat(), sub)].append((start, start + _dur(home + " " + away)))
    out = []
    for iso in sorted(dates):
        d, date_s = dates[iso]
        if d.weekday() != 5:  # Saturdays only (Mon=0 .. Sat=5)
            continue
        # All-Abilities 10:00-11:30 on Pitch 2 (Top Field)
        out.append((date_s, "10:00", "Manningham United Blues FC All-Abilities", MARK,
                    "All Abilities League", "Pettys Reserve Pitch 2 (Top Field)", ""))
        # Girls Clinic 09:00-10:00 on the first free HALF pitch (needs half a pitch)
        cs, ce = 9 * 60, 10 * 60
        free = next((h for h in HALVES
                     if not any(s < ce and cs < e for s, e in occ.get((iso, h), []))), None)
        sub = free or HALVES[0]  # fall back to 1A (clash check will flag if truly none free)
        out.append((date_s, "09:00", "Manningham United Blues FC Girls Clinic", MARK,
                    "Girls Clinic", "Pettys Reserve " + sub, ""))
    # Over 45 Men, Friday nights 19:30 — bottom pitch (1) unless Dribl occupies it, then top (2)
    ks, ke = 19 * 60 + 30, 21 * 60
    for rnd, date_s, opp, mufc_home in FRIDAY_O45:
        iso = parse_date(date_s).isoformat()
        p1_busy = any("Pitch 1" in sub and any(s < ke and ks < e for s, e in spans)
                      for (d, sub), spans in occ.items() if d == iso)
        pitch = "Pettys Reserve Pitch 2 (Top Field)" if p1_busy else "Pettys Reserve Pitch 1 (Bottom Field)"
        opp += " " + MARK
        home, away = (O45_TEAM, opp) if mufc_home else (opp, O45_TEAM)
        out.append((date_s, "19:30", home, away, O45_COMP, pitch, rnd))
    return out
