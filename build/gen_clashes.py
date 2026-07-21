import re, json, datetime as dt, os
from dribl_parse import read
HERE=os.path.dirname(os.path.abspath(__file__)); OUTDIR=os.path.dirname(HERE)
OUT=os.path.join(OUTDIR,"Manningham_schedule_clashes.html")
files={"Pettys Reserve":os.path.join(HERE,"raw_pettys.txt"),"Powerful Owl Park":os.path.join(HERE,"raw_powl.txt"),"Timber Ridge Reserve":os.path.join(HERE,"raw_timber.txt")}
MONTHS={m:i for i,m in enumerate(["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"],1)}
CUTOFF=dt.date(2026,7,17)
def parse_date(s):
    p=s.split(); return dt.date(int(p[3]),MONTHS[p[2][:3]],int(p[1]))
def duration(t,comp):
    # Clash window = match length + warm-up (a team warming up already occupies the pitch)
    if "All Abilities" in comp: return 40
    if "Seniors" in t or "Reserves" in t or re.search(r'U2[0123]\b',t): return 120
    if "17/18" in t: return 110
    if re.search(r'U18\b',t): return 110
    if re.search(r'U1[67]\b',t): return 100
    if re.search(r'U15\b',t): return 90
    if re.search(r'U1[234]\b',t): return 80
    if re.search(r'U1[01]\b',t): return 70
    if "MiniRoos" in t or re.search(r'U0[6-9]\b',t): return 50
    return 80
def age_token(t):
    if "17/18" in t: return "U17/18"
    m=re.search(r'(U\d{2}|Seniors|Reserves)',t); return m.group(1) if m else ""
def field_info(pitch,ground):
    p=pitch.replace(ground,"").strip()
    m=re.search(r'Pitch\s+(\d+)',p); return (m.group(1) if m else "?"),p
def fmt(m): return f"{m//60:02d}:{m%60:02d}"
def category(age,comp):
    if comp=="Girls Clinic": return "MID"
    if "All Abilities" in comp: return "AAL"
    if age in ("U06","U07"): return "TINY"
    if age in ("U08","U09"): return "SMALL"
    if age in ("U10","U11","U12","U13"): return "MID"
    return "BIG"
UNIT={"TINY":.25,"SMALL":.25,"AAL":.25,"MID":.5,"BIG":1.0}
CATLABEL={"TINY":"U6/7","SMALL":"U8/9","MID":"U10-13","BIG":"U14+","AAL":"All-Abilities"}
import manual_games
games=[]
for ground,path in files.items():
    _tuples=read(path)
    if ground=="Pettys Reserve": _tuples=list(_tuples)+manual_games.build(_tuples,parse_date)
    for date_s,time_s,home,away,comp,pitch,rnd in _tuples:
        d=parse_date(date_s)
        if d<CUTOFF: continue
        hh,mm=map(int,time_s.split(":")); start=hh*60+mm
        dur=(90 if "All Abilities" in comp else 60) if away==manual_games.MARK else duration(home+" "+away,comp); num,plabel=field_info(pitch,ground)
        age=age_token(home if "Manningham" in home else away+" "+home); cat=category(age,comp)
        cp=[x.strip() for x in comp.split("|")]
        games.append(dict(date=d,iso=d.isoformat(),datedisp=d.strftime("%a %d %b"),time=time_s,start=start,
            end=start+dur,endt=fmt(start+dur),ground=ground,field=num,pitch=plabel,age=age or ("AAL" if cat=="AAL" else ""),
            cat=cat,catlabel=CATLABEL[cat],unit=UNIT[cat],home=home,away=away,comp=cp[0],grade=cp[1] if len(cp)>1 else "",rnd=rnd.replace("Round ","R")))
issues=[]; buckets={}
for g in games: buckets.setdefault((g["ground"],g["iso"],g["field"]),[]).append(g)
def desc(g): return f'{g["time"]} {g["catlabel"]} {g["pitch"]} ({g["home"].replace("Manningham United Blues FC","MUFC")} v {g["away"]})'
# ---- clash-resolution: free-pitch alternatives + which game to move (priority) ----
def gsh_py(g): return "Pettys" if g=="Pettys Reserve" else ("Powerful Owl" if g=="Powerful Owl Park" else "Timber Ridge")
ALLFIELDS=[("Pettys Reserve","1"),("Pettys Reserve","2"),("Powerful Owl Park","1"),("Powerful Owl Park","2"),("Powerful Owl Park","3"),("Timber Ridge Reserve","1"),("Timber Ridge Reserve","2")]
def field_free(gr,fl,iso,s,e):
    return all(not (o["start"]<e and s<o["end"]) for o in buckets.get((gr,iso,fl),[]))
_SENIOR={"Seniors","Reserves","U20","U21","U23"}
def _bansmall(gr,fl): return gr=="Timber Ridge Reserve" or (gr=="Powerful Owl Park" and fl in ("2","3"))
def keep_priority(g):
    # lower tuple = higher priority = KEEP in place (the higher-priority game stays; the lower one moves)
    comp,age,home=g["comp"],g["age"],g["home"]
    clinic=0 if ("All Abilities" in comp or comp=="Girls Clinic") else 1   # clinics kept above all
    if age in _SENIOR: at=0                                                # seniors over juniors
    else:
        m=re.match(r'U0?(\d+)',age); n=int(m.group(1)) if m else 12
        at=1 if n>=12 else 2                                              # community juniors over miniroos
    md=re.search(r'-\s*([ABC])\b',home); div={"A":0,"B":1,"C":2}.get(md.group(1) if md else "",1)  # A over B/C
    return (clinic,at,div)
def field_has_room(g,gr,fl):
    """Can g be ADDED to field (gr,fl) without breaking the capacity rules?
    A pitch need not be empty — small games may share up to 1.0 (e.g. 0.5 + 0.25 + 0.25)."""
    over=[o for o in buckets.get((gr,g["iso"],fl),[]) if o["start"]<g["end"] and g["start"]<o["end"]]
    if not over: return True                                    # empty field
    if g["cat"]=="BIG" or any(o["cat"]=="BIG" for o in over): return False   # U14+ must be alone
    for t in sorted({g["start"]}|{o["start"] for o in over if g["start"]<=o["start"]<g["end"]}):
        if round(sum(o["unit"] for o in over if o["start"]<=t<o["end"])+g["unit"],3)>1.0: return False
    return True
def alternatives(g,need_empty=False):
    """Candidate destinations at the same time. need_empty=True demands a whole free pitch
    (used for 'U13 on their own pitch'); otherwise a pitch with spare capacity is fine."""
    sat=g["date"].weekday()==5    # Saturday: only Pettys + Timber Ridge available (no Powerful Owl)
    order=sorted(ALLFIELDS,key=lambda gf:0 if gf[0]==g["ground"] else 1)   # same ground first
    out=[]
    for gr,fl in order:
        if gr==g["ground"] and fl==g["field"]: continue
        if sat and gr=="Powerful Owl Park": continue                       # Saturday: Powerful Owl unavailable
        if g["cat"]=="SMALL" and _bansmall(gr,fl): continue                # respect U8/9 location ban
        empty=field_free(gr,fl,g["iso"],g["start"],g["end"])
        if empty or (not need_empty and field_has_room(g,gr,fl)): out.append((gr,fl,empty))
    return out
def opts_for(mv,need_empty=False):
    opts=[]
    for g in sorted(mv,key=keep_priority,reverse=True):                    # lowest priority first (most movable)
        team=g["home"].replace("Manningham United Blues FC","MUFC")
        for gr,fl,empty in alternatives(g,need_empty):
            note="" if empty else " (shares pitch, within capacity)"
            opts.append(dict(date=g["datedisp"],team=team,opp=g["away"],cat=g["catlabel"],comp=g["comp"],
                frm_g=gsh_py(g["ground"]),frm_p=g["pitch"],frm_t=g["time"],to_g=gsh_py(gr),to_p="Pitch "+fl,
                label="Move "+g["catlabel"]+" "+team+" v "+g["away"]+" → "+gsh_py(gr)+" Pitch "+fl+note))
    if opts: opts[0]["rec"]=True
    return opts
seen=set()
for (ground,iso,field),gs in buckets.items():
    for t in sorted({g["start"] for g in gs}):
        active=[g for g in gs if g["start"]<=t<g["end"]]
        if len(active)<2: continue
        key=(ground,iso,field,tuple(sorted(id(x) for x in active)))
        if key in seen: continue
        nbig=sum(1 for g in active if g["cat"]=="BIG"); units=round(sum(g["unit"] for g in active),3)
        cnt={}
        for g in active: cnt[g["cat"]]=cnt.get(g["cat"],0)+1
        mix=", ".join(f'{cnt[c]}×{CATLABEL[c]}' for c in ["BIG","MID","SMALL","TINY","AAL"] if c in cnt)
        win_e=min(g["end"] for g in active); rule=None; detail=None
        if nbig>=1 and len(active)>1:
            rule="U14+ must have the pitch to itself"; detail=f'{mix} scheduled together on {ground} Pitch {field} ({fmt(t)}–{fmt(win_e)}).'
        elif units>1.0:
            rule="Pitch over capacity"; detail=f'{mix} = {units:g} pitches worth on one pitch ({fmt(t)}–{fmt(win_e)}); max is 1.0.'
        if rule:
            seen.add(key)
            issues.append(dict(date=gs[0]["date"],datedisp=gs[0]["date"].strftime("%a %d %b"),ground=ground,field=field,
                frm=fmt(t),until=fmt(win_e),rule=rule,detail=detail,games=[desc(g) for g in sorted(active,key=lambda x:x["start"])],
                moves=opts_for(active),sig="C|"+iso+"|"+ground+"|"+field+"|"+fmt(t)))
for g in games:
    if g["cat"]=="SMALL":
        bad=None
        if g["ground"]=="Timber Ridge Reserve": bad="Timber Ridge"
        elif g["ground"]=="Powerful Owl Park" and g["field"] in ("2","3"): bad=f"Powerful Owl Park pitch {g['field']}"
        if bad:
            issues.append(dict(date=g["date"],datedisp=g["date"].strftime("%a %d %b"),ground=g["ground"],field=g["field"],
                frm=g["time"],until=g["endt"],rule="U8/9 in a banned location",detail=f'U8/9 game scheduled at {bad} – U8/9 not permitted here.',games=[desc(g)],
                moves=opts_for([g]),sig="B|"+g["iso"]+"|"+g["ground"]+"|"+g["field"]+"|"+g["time"]))
# ---- U13 not on their own pitch (sharing a physical field) + free-pitch suggestions ----
u13iss=[]
for g in games:
    if g["age"]!="U13": continue
    others=[o for o in buckets.get((g["ground"],g["iso"],g["field"]),[]) if o is not g and o["start"]<g["end"] and g["start"]<o["end"]]
    if not others: continue
    free=[gsh_py(gr)+" Pitch "+fl for gr,fl in ALLFIELDS if not (gr==g["ground"] and fl==g["field"]) and field_free(gr,fl,g["iso"],g["start"],g["end"])]
    u13iss.append(dict(date=g["date"],datedisp=g["date"].strftime("%a %d %b"),ground=g["ground"],field=g["field"],frm=g["time"],until=g["endt"],game=desc(g),sharing=[desc(o) for o in others],free=free,
        moves=opts_for([g],need_empty=True),sig="U|"+g["iso"]+"|"+g["ground"]+"|"+g["field"]+"|"+g["time"]))
u13iss.sort(key=lambda x:(x["date"],x["ground"],x["field"],x["frm"]))
issues.sort(key=lambda x:(x["date"],x["ground"],x["field"],x["frm"]))
games.sort(key=lambda g:(g["date"],g["ground"],g["start"]))
rows=[{k:g[k] for k in ("iso","datedisp","ground","field","time","endt","pitch","catlabel","age","home","away","comp","grade","rnd")} for g in games]
iss=[{k:(v.isoformat() if k=="date" else v) for k,v in x.items()} for x in issues]
u13j=[{k:(v.isoformat() if k=="date" else v) for k,v in x.items()} for x in u13iss]
DATA=json.dumps(rows); ISS=json.dumps(iss); U13J=json.dumps(u13j)
TEMPLATE=r'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Manningham – Schedule & Pitch-Rule Clashes</title>
<style>
:root{--navy:#1f3864;--blue:#2e5aac;--ink:#1a1a1a;--mut:#667;--line:#e3e7ee;--band:#f6f8fb;--red:#c0392b;--redbg:#fdeceb;--amber:#b45309;--green:#2e7d32;}
*{box-sizing:border-box}body{margin:0;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:var(--ink)}
header{background:linear-gradient(120deg,var(--navy),var(--blue));color:#fff;padding:24px 22px}
header h1{margin:0 0 4px;font-size:21px}header p{margin:0;opacity:.85;font-size:13px}
.wrap{max-width:1180px;margin:0 auto;padding:20px 22px 60px}
.cards{display:flex;flex-wrap:wrap;gap:14px;margin:16px 0}
.card{flex:1;min-width:150px;background:var(--band);border:1px solid var(--line);border-radius:12px;padding:13px 15px}
.card .n{font-size:24px;font-weight:700;color:var(--navy)}.card .l{font-size:12px;color:var(--mut);margin-top:2px}
h2{font-size:15px;color:var(--navy);margin:26px 0 10px;border-bottom:2px solid var(--line);padding-bottom:6px}
.rules{background:var(--band);border:1px solid var(--line);border-radius:10px;padding:12px 16px;font-size:12.5px;line-height:1.6;color:#334}
.rules b{color:var(--navy)}
.issue{border:1px solid #f0c9c4;background:var(--redbg);border-radius:10px;padding:11px 14px;margin:9px 0}
.issue.loc{border-color:#f2d49b;background:#fdf6e8}
.issue .top{font-weight:700;color:var(--red);font-size:13px}
.issue.loc .top{color:var(--amber)}
.issue.u13{border-color:#bcd3f0;background:#eef4fc}.issue.u13 .top{color:#1f3864}
.issue .d{font-size:12.5px;color:#333;margin:3px 0 5px}
.issue ul{margin:4px 0 0 18px;padding:0;font-size:12px;color:#444}
.none{background:#eaf5ea;border:1px solid #cfe7cf;color:#1e5220;border-radius:10px;padding:12px 14px;font-size:13px}
.rec{font-size:12px;color:#1e5220;margin:7px 0 3px;font-weight:600}
.rec.norec{color:#8a6d3b}
.fixrow{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-top:3px}
.fixrow label{font-size:11.5px;color:var(--mut);font-weight:600}
select.fixsel{font-size:12px;border:1px solid var(--line);border-radius:6px;padding:5px 8px;background:#fff;max-width:100%;cursor:pointer}
#changes{background:var(--band);border:1px solid var(--line);border-radius:10px;padding:12px 15px}
#changes ol{margin:4px 0 0;padding-left:20px;font-size:12.5px;line-height:1.55}
.intros{margin:0 0 11px;padding-bottom:10px;border-bottom:1px solid var(--line)}
.introlbl{font-size:11.5px;font-weight:700;color:var(--mut);text-transform:uppercase;letter-spacing:.04em;margin-bottom:6px}
.intros label{display:block;font-size:12.5px;color:#334;margin:3px 0;cursor:pointer}
.intros input{margin-right:7px;vertical-align:middle}
#changes .empty{font-size:12.5px;color:var(--mut)}
.copybtn{margin-top:11px;border:1px solid var(--navy);background:var(--navy);color:#fff;border-radius:8px;padding:7px 15px;font-size:12.5px;font-weight:600;cursor:pointer}
.copybtn:hover{background:#16294a}
.controls{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:6px 0 12px;position:sticky;top:0;background:#fff;padding:10px 0;z-index:5}
.chip{border:1px solid var(--line);background:#fff;border-radius:20px;padding:6px 14px;font-size:13px;cursor:pointer;color:var(--mut)}
.chip.active{background:var(--navy);color:#fff;border-color:var(--navy)}
select#dsel{border:1px solid var(--line);border-radius:8px;padding:8px 12px;font-size:13px;background:#fff;color:var(--ink);cursor:pointer;max-width:180px}
input[type=search]{flex:1;min-width:170px;border:1px solid var(--line);border-radius:8px;padding:8px 12px;font-size:13px}
.count{font-size:12px;color:var(--mut)}
table.g{width:100%;border-collapse:collapse;font-size:12.5px}
table.g th{position:sticky;top:56px;background:var(--navy);color:#fff;padding:8px;text-align:left;cursor:pointer;white-space:nowrap}
table.g td{border-bottom:1px solid var(--line);padding:6px 8px}
tr.dhead td{background:#eef2f8;font-weight:700;color:var(--navy);position:sticky;top:56px}
.badge{display:inline-block;font-size:10px;padding:1px 6px;border-radius:6px;background:#eef2f8;color:var(--mut);white-space:nowrap}
.b-BIG{background:#e6eefc;color:#1f3864}.b-MID{background:#e9f7ef;color:#1e7d46}.b-SMALL{background:#fdf0e6;color:#a85b13}.b-TINY{background:#fceaf3;color:#a3316f}.b-AAL{background:#eee9fb;color:#5b3ea6}
.g-pettys{color:#1f6feb}.g-powl{color:#8a5cf6}.g-timber{color:#0f9d58}
.foot{color:var(--mut);font-size:11px;margin-top:22px}
tr.clashrow td{background:#fdeceb!important}
</style></head><body>
<header><h1>Manningham United Blues &ndash; Schedule &amp; Pitch-Rule Clash Check</h1>
<p>Pettys Reserve &middot; Powerful Owl Park &middot; Timber Ridge Reserve &nbsp;|&nbsp; 17 Jul &rarr; mid-Sep 2026 &middot; Source: fv.dribl.com</p><div style="margin-top:9px;font-size:12px"><a href="Manningham_setup_packup_plan.html" style="color:rgba(255,255,255,.55);text-decoration:underline;margin-right:14px">Setup &amp; pack-up</a><a href="Manningham_fixtures.html" style="color:rgba(255,255,255,.55);text-decoration:underline">Fixtures</a></div></header>
<div class="wrap">
<div class="cards" id="cards"></div>
<h2>Pitch capacity rules applied</h2>
<div class="rules">
A full pitch = <b>1.0</b>. &nbsp; <b>U14 &amp; older</b> = whole pitch (must be alone). &nbsp; <b>U10&ndash;U13</b> = &frac12; each (max 2). &nbsp;
<b>U8/9</b> = &frac14; each (max 4). &nbsp; <b>U6/7</b> = &frac14; each. &nbsp; All-Abilities treated as &frac14;.<br>
Allowed combos on one pitch at the same time: 2&times;U10-13 &nbsp;|&nbsp; 1&times;U10-13 + up to 2&times;U8/9 &nbsp;|&nbsp; up to 4&times;U8/9 &nbsp;|&nbsp; 2&times;U6/7 + 2&times;U8/9.<br>
<b>Location ban:</b> U8/9 may not play at Timber Ridge, or on Powerful Owl Park pitches 2 &amp; 3. &nbsp;
<span style="color:#667">(Overlap uses match + warm-up windows: All-Abilities 40m, U6&ndash;9 50m, U10&ndash;11 70m, U12&ndash;14 80m, U15 90m, U16&ndash;17 100m, U18 110m, Seniors/U20&ndash;23 120m. "Pitch" = physical field.)</span>
</div>
<h2 id="clashhead">Potential clashes</h2>
<div id="issues"></div>
<h2 id="u13head">U13 not on their own pitch</h2>
<div id="u13"></div>
<h2 id="chghead">Proposed changes &ndash; email to FV</h2>
<div id="changes"></div>
<h2>Full schedule &ndash; by date, ground &amp; time</h2>
<div class="controls"><span id="chips"></span>
<select id="dsel"><option value="">All dates</option></select>
<input type="search" id="q" placeholder="Search team, competition, pitch, age…"><span class="count" id="count"></span></div>
<table class="g"><thead><tr><th data-k="time">Time</th><th data-k="ground">Ground</th><th data-k="pitch">Pitch</th>
<th data-k="catlabel">Group</th><th data-k="home">Home</th><th data-k="away">Away</th><th data-k="comp">Competition</th><th data-k="rnd">Rnd</th></tr></thead>
<tbody id="tb"></tbody></table>
<div class="foot">Clashes are suggestions based on the rules above and estimated match lengths &ndash; verify against actual kickoff/finish times before acting. &middot; <a href="Manningham_fixtures.html" style="color:var(--mut)">full fixtures</a></div>
</div>
<script>
const DATA=__DATA__, ISS=__ISS__, U13=__U13__;
const gsh=g=>g==="Pettys Reserve"?"Pettys":g==="Powerful Owl Park"?"Powerful Owl":"Timber Ridge";
const gcl=g=>g==="Pettys Reserve"?"g-pettys":g==="Powerful Owl Park"?"g-powl":"g-timber";
const MOVEMAP={};
function optsHtml(i){
  MOVEMAP[i.sig]=i.moves||[];
  if(!i.moves||!i.moves.length) return '<div class="rec norec">No free pitch at this time &mdash; leave as-is.</div>';
  var m=i.moves[0];
  var rec='<div class="rec">&#9654; Recommended: move <b>'+m.cat+' '+m.team+' v '+m.opp+'</b> to <b>'+m.to_g+' '+m.to_p+'</b> (same time)</div>';
  var sel='<div class="fixrow"><label>Resolution:</label><select class="fixsel" data-sig="'+i.sig+'"><option value="">Leave as-is</option>'+
    i.moves.map(function(m,mi){return '<option value="'+mi+'">'+m.label+(m.rec?' ★':'')+'</option>';}).join('')+'</select></div>';
  return rec+sel;
}
const clashset=new Set();
ISS.forEach(i=>i.games.forEach(x=>clashset.add(x)));
const cnt=g=>DATA.filter(x=>x.ground===g).length;
document.getElementById('cards').innerHTML=
 '<div class="card"><div class="n">'+DATA.length+'</div><div class="l">Games (17 Jul → season end)</div></div>'+
 '<div class="card"><div class="n">'+cnt("Pettys Reserve")+'</div><div class="l">Pettys Reserve</div></div>'+
 '<div class="card"><div class="n">'+cnt("Powerful Owl Park")+'</div><div class="l">Powerful Owl Park</div></div>'+
 '<div class="card"><div class="n">'+cnt("Timber Ridge Reserve")+'</div><div class="l">Timber Ridge</div></div>'+
 '<div class="card"><div class="n" style="color:'+(ISS.length?'#c0392b':'#2e7d32')+'">'+ISS.length+'</div><div class="l">Potential clashes</div></div>';
const ib=document.getElementById('issues');
if(!ISS.length){ib.innerHTML='<div class="none">&#10003; No rule breaches found.</div>';}
else{ib.innerHTML=ISS.map(i=>'<div class="issue '+(i.rule.includes('location')?'loc':'')+'">'+
  '<div class="top">'+i.datedisp+' &middot; '+gsh(i.ground)+' Pitch '+i.field+' &middot; '+i.frm+'–'+i.until+' &mdash; '+i.rule+'</div>'+
  '<div class="d">'+i.detail+'</div><ul>'+i.games.map(x=>'<li>'+x+'</li>').join('')+'</ul>'+optsHtml(i)+'</div>').join('');}
document.getElementById('clashhead').textContent='Potential clashes ('+ISS.length+')';
const u13b=document.getElementById('u13');
if(!U13.length){u13b.innerHTML='<div class="none">&#10003; Every U13 game has its physical pitch to itself.</div>';}
else{u13b.innerHTML=U13.map(i=>'<div class="issue u13">'+
  '<div class="top">'+i.datedisp+' &middot; '+gsh(i.ground)+' Pitch '+i.field+' &middot; '+i.frm+'–'+i.until+'</div>'+
  '<div class="d"><b>'+i.game+'</b> is sharing Pitch '+i.field+' with:</div><ul>'+i.sharing.map(x=>'<li>'+x+'</li>').join('')+'</ul>'+
  '<div class="d" style="margin-top:6px">Free full pitches then: '+(i.free.length?'<b style="color:#1e7d46">'+i.free.join(' &middot; ')+'</b>':'<b style="color:#c0392b">none free</b>')+'</div>'+optsHtml(i)+'</div>').join('');}
document.getElementById('u13head').textContent='U13 not on their own pitch ('+U13.length+')';
const CHANGES={};
const INTROS=[
 {l:"Pitch quality / safety risk",t:"Dear Competitions,\n\nWe would like to request that the following fixtures be relocated to an alternative ground, as the current pitch quality is presenting a safety risk to the players. We would be very grateful for your assistance in moving the games listed below:"},
 {l:"Clash of times",t:"Dear Competitions,\n\nWe have identified a scheduling clash affecting the fixtures below, where more than one game is allocated to the same pitch at the same time. We would kindly ask that these games be moved to resolve the overlap:"},
 {l:"Lack of warm-up space & time",t:"Dear Competitions,\n\nDue to insufficient warm-up space and time between fixtures, we would like to request that the following games be moved to an alternative pitch so the teams are able to prepare safely:"},
 {l:"To allow box-to-box (full pitch)",t:"Dear Competitions,\n\nWe are writing to request that the following games be moved to an alternative pitch so that the teams can play box-to-box on a full-size field. We would appreciate your support with the changes set out below:"}
];
function _line(m){return m.date+' — '+m.cat+' '+m.team+' v '+m.opp+' ['+m.comp+']: move from '+m.frm_g+' '+m.frm_p+' ('+m.frm_t+') to '+m.to_g+' '+m.to_p+' — same time.';}
document.getElementById('changes').innerHTML='<div class="intros"><div class="introlbl">Email opening (choose the reason):</div>'+INTROS.map(function(x,i){return '<label><input type="radio" name="intro" value="'+i+'"'+(i===1?' checked':'')+'> '+x.l+'</label>';}).join('')+'</div><div id="chglist"></div>';
function selIntro(){var r=document.querySelector('input[name=intro]:checked');return INTROS[r?+r.value:1].t;}
function renderChanges(){
  var keys=Object.keys(CHANGES),el=document.getElementById('chglist');
  document.getElementById('chghead').textContent='Proposed changes – email to FV ('+keys.length+')';
  if(!keys.length){el.innerHTML='<div class="empty">No changes selected yet — pick a resolution on a clash above and it will be listed here, ready to email FV.</div>';return;}
  el.innerHTML='<ol><li>'+keys.map(function(k){return _line(CHANGES[k]);}).join('</li><li>')+'</li></ol><button class="copybtn" onclick="copyEmail()">Copy for email</button>';
}
function copyEmail(){
  var keys=Object.keys(CHANGES);
  var body=keys.map(function(k,i){return (i+1)+'. '+_line(CHANGES[k]);}).join('\n');
  var txt=selIntro()+'\n\n'+body+'\n\nKind regards,\nManningham United Blues FC';
  navigator.clipboard.writeText(txt).then(function(){var b=document.querySelector('.copybtn');if(b){b.textContent='Copied ✓';setTimeout(function(){b.textContent='Copy for email';},1500);}});
}
document.querySelectorAll('.fixsel').forEach(function(s){s.onchange=function(){var sig=s.getAttribute('data-sig'),v=s.value;if(v===''){delete CHANGES[sig];}else{CHANGES[sig]=MOVEMAP[sig][+v];}renderChanges();};});
renderChanges();
let ground="All",q="",date="",sortk="time",asc=true;
const chips=["All","Pettys Reserve","Powerful Owl Park","Timber Ridge Reserve"];
document.getElementById('chips').innerHTML=chips.map(c=>'<span class="chip'+(c==='All'?' active':'')+'" data-g="'+c+'">'+(c==='All'?'All grounds':gsh(c))+'</span>').join('');
document.querySelectorAll('.chip').forEach(el=>el.onclick=()=>{ground=el.dataset.g;document.querySelectorAll('.chip').forEach(x=>x.classList.toggle('active',x===el));render();});
const dseen=new Set(),dsel=document.getElementById('dsel');
DATA.slice().sort((a,b)=>a.iso<b.iso?-1:1).forEach(g=>{if(!dseen.has(g.iso)){dseen.add(g.iso);const o=document.createElement('option');o.value=g.iso;o.textContent=g.datedisp+' '+g.iso.slice(0,4);dsel.appendChild(o);}});
dsel.onchange=e=>{date=e.target.value;render();};
document.getElementById('q').oninput=e=>{q=e.target.value.toLowerCase();render();};
document.querySelectorAll('table.g th').forEach(th=>th.onclick=()=>{const k=th.dataset.k;asc=(sortk===k)?!asc:true;sortk=k;render();});
function catCode(l){return l==='U14+'?'BIG':l==='U10-13'?'MID':l==='U8/9'?'SMALL':l==='U6/7'?'TINY':'AAL';}
function render(){
 let r=DATA.filter(g=>(ground==="All"||g.ground===ground)&&(!date||g.iso===date));
 if(q)r=r.filter(g=>(g.home+' '+g.away+' '+g.comp+' '+g.pitch+' '+g.age+' '+g.catlabel+' '+g.datedisp).toLowerCase().includes(q));
 r=r.slice().sort((a,b)=>{let x=a[sortk],y=b[sortk];if(sortk==='time'){x=a.iso+a.time+a.ground;y=b.iso+b.time+b.ground;}return (x>y?1:x<y?-1:0)*(asc?1:-1);});
 document.getElementById('count').textContent=r.length+' games';
 let out='',lastd='';
 r.forEach(g=>{
   if(sortk==='time'&&g.datedisp!==lastd){lastd=g.datedisp;out+='<tr class="dhead"><td colspan="8">'+g.datedisp+' '+g.iso.slice(0,4)+'</td></tr>';}
   const cl=clashset.has(g.time+' '+g.catlabel+' '+g.pitch+' ('+g.home.replace('Manningham United Blues FC','MUFC')+' v '+g.away+')');
   out+='<tr class="'+(cl?'clashrow':'')+'"><td>'+g.time+'–'+g.endt+'</td><td class="'+gcl(g.ground)+'">'+gsh(g.ground)+'</td>'+
   '<td>'+g.pitch+'</td><td><span class="badge b-'+catCode(g.catlabel)+'">'+g.catlabel+'</span></td>'+
   '<td>'+g.home+'</td><td>'+g.away+'</td><td>'+g.comp+'</td><td>'+g.rnd+'</td></tr>';
 });
 document.getElementById('tb').innerHTML=out;
}
render();
</script></body></html>'''
open(OUT,"w",encoding="utf-8").write(TEMPLATE.replace("__DATA__",DATA).replace("__ISS__",ISS).replace("__U13__",U13J))
print("clashes:",len(games),"games,",len(issues),"issues ->",OUT)
