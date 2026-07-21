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
GENS = ["gen_duties.py", "gen_fixtures.py", "gen_clashes.py", "gen_xlsx.py"]
ok = True
for g in GENS:
    print(f"\n=== {g} ===")
    if subprocess.run([sys.executable, g], cwd=HERE).returncode != 0:
        ok = False
        print(f"!! FAILED: {g}")
print("\nAll regenerated — now commit & push the changed output files." if ok
      else "\nSome generators FAILED — fix the error above before publishing.")
sys.exit(0 if ok else 1)
