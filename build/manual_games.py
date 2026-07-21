"""Manually-added games (NOT from Dribl). Merged into every generator so they survive refresh.

Recurring every SATURDAY match day at Pettys Reserve:
  - All-Abilities : 10:00-11:30, Pitch 2 (Top Field)            (AAL, quarter pitch)
  - Girls Clinic  : 09:00-10:00, auto-placed on a free HALF pitch (1A/1B/2A/2B)

Both are flagged MANUAL via away == MARK so the generators can badge them and skip duty logic.
Returns tuples in the same shape as dribl_parse.read(): (date_s,time_s,home,away,comp,pitch,rnd)
"""
MARK = "[MANUAL ADD]"
HALVES = ["Pitch 1A (Bottom Field)", "Pitch 1B (Bottom Field)",
          "Pitch 2A (Top Field)", "Pitch 2B (Top Field)"]

def _dur(s):  # rough occupancy length for the free-pitch check
    if "MiniRoos" in s or any(u in s for u in ("U07", "U08", "U09", "U10", "U11")): return 40
    if "Seniors" in s or "Reserve" in s: return 90
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
    return out
