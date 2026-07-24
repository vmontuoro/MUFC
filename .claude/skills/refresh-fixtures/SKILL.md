---
name: refresh-fixtures
description: Refresh the Manningham United Blues fixtures site with new Dribl data and publish it. Use when the user has (re)captured Dribl fixtures and wants the pages updated/published, or says "update the fixtures", "refresh the data", "new Dribl data", "republish the site", "update the clash / setup page".
---

# Refresh the MUFC fixtures site from new Dribl data

The site is data-driven: Python generators in `build/` parse text dumps of Dribl's
fixtures page and produce the published files. Follow these steps in order.

Which generator produces which page:
Manual (non-Dribl) games live in `build/manual_games.py` and are injected into all four
generators: the recurring Saturday All-Abilities + Girls Clinic events, and the **Over 45 Men
Friday-night season** (`FRIDAY_O45` — edit that list to add/remove games; runs to 06 Nov, past
the FV season end). O45 games are ALWAYS at Pettys — even rounds whose fixture says "Away"
(those display the opponent as home side) — auto-placed on Pitch 1 (Bottom) unless Dribl
occupies it that evening, then Pitch 2. Manual games are flagged by the `[MANUAL ADD]` suffix
on the non-Manningham side; generators must use `manual_games.is_manual()/strip_mark()`, never
compare `== MARK` directly.

All four generators apply `build/overrides.json` and share one clash rule (`build/pitch_capacity.py`:
U14+/Seniors = 1.0 and must be alone, U10-13 = 0.5, U6-9 = 0.25, All-Abilities = 0.5; a field is
flagged only when concurrent games sum > 1.0). Two guards worth knowing:
- a malformed `overrides.json` now **raises** and fails the run — it is never silently ignored;
- an override whose `gkey` matches no fixture prints `! N override(s) matched NO fixture`. Read that
  warning: the move simply does not happen, and every page still renders fine without it.

- `gen_duties.py`   → `duties_data.js`  (the **setup/pack-up page** loads this — it's DECOUPLED, so refreshing data never touches that page's rich UI)
- `gen_clashes.py`  → `Manningham_schedule_clashes.html`  (whole file regenerated)
- `gen_fixtures.py` → `Manningham_fixtures.html`
- `gen_xlsx.py`     → `Manningham_fixtures_and_overlaps.xlsx`

## 0. Preconditions
- Working dir: `C:\Users\cenzo\Claude\Projects\Dribl scraper`
- The raw dumps must hold a **FULL-SEASON** capture: `build/raw_pettys.txt`, `build/raw_powl.txt`,
  `build/raw_timber.txt`, `build/raw_wilsons.txt`. **`raw_wilsons.txt` is normally EMPTY** — the club
  has no access to Wilsons Rd Reserve, so any fixture found there is flagged as a rule violation. If stale/missing, give the user the
  **cowork capture prompt** (below) and wait for the files.

## 0b. Manual overrides — ASK THE USER PER DATE
If `build/overrides.json` exists and is non-empty it holds fixture moves the club requested but
Dribl had not yet actioned. `python build/refresh.py` prints them grouped by date. **Before
publishing, ask the user for each of those dates** (AskUserQuestion) whether to:
- **keep** the override (FV still hasn't actioned it), or
- **drop** it (the fresh Dribl capture now contains FV's actioned fixture — the override is stale
  and would double-apply).
Then prune `build/overrides.json` accordingly and regenerate. Never decide this silently.

## 0c. Sanity-check the capture is not corrupt
A partial/interrupted save has produced a file with embedded null bytes before (silently halving the
season). Before regenerating:
```
python -c "
for f in ['pettys','powl','timber','wilsons']:
 raw=open(f'build/raw_{f}.txt','rb').read(); print(f, len(raw), 'nulls=', raw.count(bytes([0])))"
```
Any non-zero null count = corrupt; restore from git (`git checkout main -- build/raw_<x>.txt`) and re-capture.

## 1. Regenerate everything
```
python build/refresh.py
```
Rebuilds all four outputs. The "last updated" bar auto-stamps from the raw files' mtime.

## 2. VERIFY THE DATE RANGE — this is the critical check
Do NOT trust the game count alone. Confirm the output spans the whole remaining season:
```
python -c "import json; d=json.loads(open('duties_data.js',encoding='utf-8').read().split('var DATA=',1)[1].rstrip(';')); iso=sorted(set(g['iso'] for g in d)); print('games',len(d),'| dates',iso[0],'->',iso[-1])"
```
- Expect **17 Jul → 06 Nov** (the Over 45 Friday games run past the FV season, which ends
  mid-Sep; dates after ~13 Sep legitimately hold ONLY O45 games). If it stops early (e.g.
  "-> 2026-08-30") when later fixtures should exist, the parser dropped something — investigate
  before publishing.
- **Known trap:** Dribl varies month spelling ("Jul" vs "July", "Sep" vs "Sept"). The parser's
  `DATE_RE` accepts 3–9 letter months and `parse_date` matches on the first 3 letters — if a whole
  month vanishes, that regex or `MONTHS` lookup is the first suspect.
- A big drop vs the live site usually means a partial capture (Dribl's default 3-week window) —
  ask the user to re-capture the full season.

## 3. PII scan (must be 0)
```
grep -licE '[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}|\b04[0-9]{8}\b' duties_data.js Manningham_fixtures.html Manningham_schedule_clashes.html
```

## 4. Publish (ONLY these output files — never private CSVs / build tooling / worksheets)
```
git fetch origin main
git add -A   # gitignore whitelist keeps private CSVs/worksheets/junk out; this stages the
             # outputs + the build/raw_*.txt dumps + any pipeline/skill edits
git commit -m "Refresh fixtures from Dribl (<date>)"
git push origin main   # if origin moved, rebase onto it first
```
Then confirm live (wait for Pages build → "built"):
```
gh api repos/vmontuoro/MUFC/pages/builds/latest --jq '.status'
curl -s "https://vmontuoro.github.io/MUFC/duties_data.js?cb=$RANDOM" | grep -o 'DATA_UPDATED="[^"]*"'
```

## 5. (Optional) bump the restore-point tag
`git tag -f known-good-<date> HEAD && git push -f origin known-good-<date>`

## 6. If the manager worksheet needs refreshing too
The private `Manningham_manager_mapping_WORKSHEET_PRIVATE.xlsx` is rebuilt separately from
`TeamOfficials_*.csv` + `duties_data.js` (team names). It is PRIVATE — regenerate & send, never commit.

---

## Notes & gotchas
- `.gitignore` whitelists only published files; the officials CSV, `*_PRIVATE.*`, the `build/`
  pipeline and design files stay unpublished. Don't add them.
- Two windows editing this repo at once causes overwrite collisions — work in one window.
- **Month-name spelling** varies between captures (see step 2) — always verify the date RANGE.
- Dribl reuses the plain name `MUFC U13`/`MUFC U15` for BOTH the boys VYPL team and the girls CPL
  team. `gen_duties.py` disambiguates them to `... Boys (VYPL)` / `... Girls (CPL)` by competition —
  keep that logic if editing team names.
- Team-name cleaning, change-room allocation and U13-sharing live in `build/dribl_parse.py`,
  `build/gen_duties.py` and `build/gen_clashes.py`. Change rules there, then re-run refresh.
- September finals may be absent until Dribl schedules them.

## cowork capture prompt (give to the user when raw data is stale)
```
Task: Capture Manningham United Blues' full-season home fixtures from Dribl, one file per ground.
For EACH of the 4 ground URLs below: open it, change the date filter to the ENTIRE 2026 season
(from the first round to the last — NOT the default few weeks; try swapping date_range=default for
date_range=all), scroll so every fixture lazy-loads, then copy the full fixtures text and save
(overwrite) to the matching file in C:\Users\cenzo\Claude\Projects\Dribl scraper\build\ .
Keep each game's date, time, home, '-', away, competition, ground+pitch and round.
  Pettys Reserve  -> raw_pettys.txt : https://fv.dribl.com/fixtures/?date_range=default&season=nPmrj2rmow&ground=gld49gj0mW&timezone=Australia%2FSydney
  Powerful Owl    -> raw_powl.txt   : https://fv.dribl.com/fixtures/?date_range=default&season=nPmrj2rmow&ground=AnmYl5x1dz&timezone=Australia%2FSydney
  Timber Ridge    -> raw_timber.txt : https://fv.dribl.com/fixtures/?date_range=default&season=nPmrj2rmow&ground=jJmXYXRWNn&timezone=Australia%2FSydney
  Wilsons Rd Res  -> raw_wilsons.txt: (find Wilsons Rd Reserve in the ground filter) — expected to be EMPTY;
                    save an empty file if there are no fixtures. Any game here is a scheduling error.
```
