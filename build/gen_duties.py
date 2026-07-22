import re, json, datetime as dt, os
from dribl_parse import read
HERE=os.path.dirname(os.path.abspath(__file__)); OUTDIR=os.path.dirname(HERE)
OUT=os.path.join(OUTDIR,"Manningham_setup_packup_plan.html")
files={"Pettys Reserve":os.path.join(HERE,"raw_pettys.txt"),"Powerful Owl Park":os.path.join(HERE,"raw_powl.txt"),"Timber Ridge Reserve":os.path.join(HERE,"raw_timber.txt"),"Wilsons Rd Reserve":os.path.join(HERE,"raw_wilsons.txt")}
MONTHS={m:i for i,m in enumerate(["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"],1)}
CUTOFF=dt.date(2026,7,17)
GORD={"Pettys Reserve":0,"Powerful Owl Park":1,"Timber Ridge Reserve":2,"Wilsons Rd Reserve":3}
def parse_date(s):
    p=s.split(); return dt.date(int(p[3]),MONTHS[p[2][:3]],int(p[1]))
def age_token(t):
    if "17/18" in t: return "U17/18"
    m=re.search(r'(U\d{2}|Seniors|Reserves)',t); return m.group(1) if m else ""
def band(age,comp):
    if "All Abilities" in comp: return "AAL"
    if age in ("U06","U07"): return "U7"
    if age in ("U08","U09"): return "U8/9"
    if age in ("U10","U11","U12","U13"): return "U10-13"
    return "SNR"
MINI={"U7","U8/9","U10-13","AAL"}
import manual_games
games=[]
for ground,path in files.items():
    _tuples=read(path)
    if ground=="Pettys Reserve": _tuples=list(_tuples)+manual_games.build(_tuples,parse_date)
    for date_s,time_s,home,away,comp,pitch,rnd in _tuples:
        d=parse_date(date_s)
        if d<CUTOFF: continue
        man=(away==manual_games.MARK)
        hh,mm=map(int,time_s.split(":")); start=hh*60+mm
        plabel=pitch.replace(ground,"").strip()
        home_mufc="Manningham United Blues" in home; away_mufc="Manningham United Blues" in away
        mufc=home_mufc or away_mufc
        age=age_token(home if home_mufc else (away if away_mufc else home)); bd=band(age,comp)
        if comp=="Girls Clinic": bd="U10-13"
        team=((home if home_mufc else away) if mufc else home).replace("Manningham United Blues FC","MUFC")
        if re.match(r'MUFC U\d+$',team):  # Dribl reuses plain "MUFC U15" for both boys VYPL and girls CPL
            if "Community Premier League Girls" in comp: team+=" Girls (CPL)"
            elif "Victorian Youth Premier League" in comp: team+=" Boys (VYPL)"
        games.append(dict(date=d,iso=d.isoformat(),datedisp=d.strftime("%a %d %b %Y"),time=time_s,start=start,
            ground=ground,gord=GORD[ground],pitch=plabel,age=age,band=bd,home=home,away=away,
            team=team,mufc=mufc,home_mufc=home_mufc,
            elig=(not (mufc and not home_mufc)) and not man,manual=man,rnd=rnd.replace("Round ","R"),comp=comp.split("|")[0].strip(),
            setup=False,packup=False,stasks=[],ptasks=[],poles_out=False,poles_away=False,stretch_out=False,stretch_away=False))
import overrides as _ovr
def gkey_of(g):
    """Must match gen_clashes.gkey_of exactly: iso|ground|pitch|time|home"""
    return "|".join([g["iso"],g["ground"],g["pitch"],g["time"],g["home"]])
# Apply saved manual moves BEFORE duty logic, so set-up/pack-up is worked out for the pitch
# the game will actually be played on.
if _ovr.apply(games,gkey_of):
    for g in games:
        if g.get("override"): g["gord"]=GORD.get(g["ground"],g["gord"])
groups={}
for g in games: groups.setdefault((g["ground"],g["iso"],g["pitch"]),[]).append(g)
for grp in groups.values():
    grp.sort(key=lambda x:x["start"])
    for j,g in enumerate(grp):
        if not (g["band"] in MINI and g["elig"]): continue
        prevb=grp[j-1]["band"] if j>0 else None; nextb=grp[j+1]["band"] if j<len(grp)-1 else None
        if prevb!=g["band"]:
            g["setup"]=True
            g["stasks"]=["Bring out the goals","Bring out the corner poles","If the pitch has no line markings, lay yellow flat plates"]
            if g["age"] in ("U12","U13"): g["stasks"].append("Collect spare linesman flags from the ref / marshall room")
        if nextb!=g["band"]:
            g["packup"]=True
            g["ptasks"]=["Pack up the goals","Pack up the corner poles","Return any borrowed kit to the ref room"]
            if g["age"] in ("U12","U13"): g["ptasks"].append("Return linesman flags to the ref / marshall room")
snr=[g for g in games if g["band"]=="SNR" and g["elig"]]
byp={}
for g in snr: byp.setdefault((g["ground"],g["iso"],g["pitch"]),[]).append(g)
for grp in byp.values():
    grp.sort(key=lambda x:x["start"]); grp[0]["poles_out"]=True; grp[-1]["poles_away"]=True
byg={}
for g in snr: byg.setdefault((g["ground"],g["iso"]),[]).append(g)
for grp in byg.values():
    grp.sort(key=lambda x:x["start"]); grp[0]["stretch_out"]=True; grp[-1]["stretch_away"]=True
for g in snr:
    st=[]; pk=[]
    if g["stretch_out"]: st.append("Bring out the stretcher")
    if g["poles_out"]: st.append("Bring out the corner poles")
    if g["poles_away"]: pk.append("Pack up the corner poles")
    if g["stretch_away"]: pk.append("Put the stretcher away")
    if pk: pk.append("Return any borrowed kit to the ref room")
    if st: g["setup"]=True; g["stasks"]=st
    if pk: g["packup"]=True; g["ptasks"]=pk
# ---- change-room allocation (SNR + U13 home games) ----
def _crdur(g):
    a=g["age"]
    if a in ("Seniors","Reserves","U20","U21","U23"): return 90
    if a in ("U15","U16","U17","U18","U17/18"): return 70
    if a in ("U12","U13","U14"): return 60
    return 40
def _crprio(g):
    c=g["comp"]
    if "Victorian Youth Premier League" in c: return 0
    if "VPL Men" in c or "Men's Metropolitan" in c: return 1
    if "State League Women" in c or "Women's Metro" in c or c=="VPL Women": return 2
    if g["age"]=="U13": return 3
    return 4
def _pn(p):
    m=re.search(r'Pitch\s*(\d)',p); return int(m.group(1)) if m else 0
def _ov(a1,a2,b1,b2): return a1<b2 and b1<a2
for g in games: g["home_cr"]=0; g["away_cr"]=0; g["cr_clash"]=False
elig=[g for g in games if g["home_mufc"] and (g["band"]=="SNR" or g["age"]=="U13")]
for g in elig: g["_cre"]=g["start"]+_crdur(g)
# Pettys: 2 home rooms, CR2->away CR3 (primary) then CR1->away CR4, filled by priority
_pd={}
for g in elig:
    if g["ground"]=="Pettys Reserve": _pd.setdefault(g["iso"],[]).append(g)
for day in _pd.values():
    day.sort(key=lambda g:(_crprio(g),g["start"]))
    used={2:[],1:[]}
    for g in day:
        placed=0
        for cr in (2,1):
            if all(not _ov(g["start"],g["_cre"],s,e) for s,e in used[cr]):
                used[cr].append((g["start"],g["_cre"])); placed=cr; break
        if placed==2: g["home_cr"],g["away_cr"]=2,3
        elif placed==1: g["home_cr"],g["away_cr"]=1,4
        else: g["cr_clash"]=True
# Powerful Owl: by pitch  P1->home5/away6, P2->1/2, P3->3/4
_POW={1:(5,6),2:(1,2),3:(3,4)}
_pw={}
for g in elig:
    if g["ground"]=="Powerful Owl Park":
        pn=_pn(g["pitch"])
        if pn in _POW:
            g["home_cr"],g["away_cr"]=_POW[pn]
            _pw.setdefault((g["iso"],pn),[]).append(g)
for grp in _pw.values():
    grp.sort(key=lambda g:g["start"])
    for i,g in enumerate(grp):
        if any(_ov(g["start"],g["_cre"],h["start"],h["_cre"]) for h in grp[:i]): g["cr_clash"]=True
# For every overridden game, add a "ghost" of the ORIGINAL booking so the old pitch still shows it
# struck through (mirrors the clash page). Added AFTER all duty / change-room logic so ghosts never
# influence who sets up or which change room is allocated.
for g in [x for x in games if x.get("override")]:
    gh=dict(g)
    gh["ground"]=g["moved_from"]["ground"]; gh["pitch"]=g["moved_from"]["pitch"]
    gh["gord"]=GORD.get(gh["ground"],g["gord"])
    gh["ghost"]=True; gh["moved_to"]={"ground":g["ground"],"pitch":g["pitch"]}
    gh["setup"]=False; gh["packup"]=False; gh["stasks"]=[]; gh["ptasks"]=[]
    gh["home_cr"]=0; gh["away_cr"]=0; gh["cr_clash"]=False
    gh.pop("override",None); gh.pop("moved_from",None)
    games.append(gh)
games.sort(key=lambda g:(g["date"],g["gord"],g["pitch"],g["start"]))
rows=[dict({k:g[k] for k in ("iso","datedisp","ground","pitch","time","age","band","team","home","away","mufc","home_mufc","setup","packup","stasks","ptasks","rnd","comp","home_cr","away_cr","cr_clash","manual")},
           **({"override":True,"moved_from":g["moved_from"]} if g.get("override") else {}),
           **({"ghost":True,"moved_to":g["moved_to"]} if g.get("ghost") else {})) for g in games]
DATA=json.dumps(rows)
_mt=max(os.path.getmtime(p) for p in files.values() if os.path.exists(p))
UPD=dt.date.fromtimestamp(_mt).strftime("%d %b %Y").lstrip("0")
open(os.path.join(OUTDIR,"duties_data.js"),"w",encoding="utf-8").write('var DATA_UPDATED="'+UPD+'";var DATA='+DATA+";")
print("duties:",len(games),"games, updated",UPD,"-> duties_data.js")
