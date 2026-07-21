#!/usr/bin/env python
"""Regenerate every published file from the current build/raw_*.txt Dribl dumps.

Usage:
    python build/refresh.py

Prereq: raw_pettys.txt / raw_powl.txt / raw_timber.txt in this folder must already
hold a FULL-SEASON capture from Dribl (date_range covering the whole season, not the
default few-weeks window). See the capture prompt in the refresh-fixtures skill.

Outputs (in the repo root):
    duties_data.js                       (data for the rich setup/pack-up page)
    Manningham_fixtures.html
    Manningham_schedule_clashes.html
    Manningham_fixtures_and_overlaps.xlsx

After running, commit & push those changed files.
"""
import subprocess, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
GENS = ["gen_duties.py", "gen_fixtures.py", "gen_clashes.py", "gen_xlsx.py"]

# Manual fixture overrides survive a refresh — surface them so the human can decide per date
# whether Dribl's fresh data has superseded them (see the refresh-fixtures skill).
try:
    import overrides
    _d = overrides.dates()
    if _d:
        print("!! MANUAL OVERRIDES PRESENT — confirm per date before publishing:")
        for iso in sorted(_d):
            print(f"     {iso}: {_d[iso]} game(s) moved")
        print("   Keep them, or drop dates FV has now actioned, by editing build/overrides.json.\n")
except Exception as e:
    print(f"  (overrides check skipped: {e})")

ok = True
for g in GENS:
    print(f"\n=== {g} ===")
    if subprocess.run([sys.executable, g], cwd=HERE).returncode != 0:
        ok = False
        print(f"!! FAILED: {g}")
print("\nAll regenerated — now commit & push the changed output files." if ok
      else "\nSome generators FAILED — fix the error above before publishing.")
sys.exit(0 if ok else 1)
