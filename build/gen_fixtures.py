import re, json, datetime as dt, os
from itertools import combinations
from dribl_parse import read
HERE=os.path.dirname(os.path.abspath(__file__)); OUTDIR=os.path.dirname(HERE)
OUT=os.path.join(OUTDIR,"Manningham_fixtures.html")
files={"Pettys Reserve":os.path.join(HERE,"raw_pettys.txt"),"Powerful Owl Park":os.path.join(HERE,"raw_powl.txt"),"Timber Ridge Reserve":os.path.join(HERE,"raw_timber.txt")}
MONTHS={m:i for i,m in enumerate(["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"],1)}
def parse_date(s):
    p=s.split(); return dt.date(int(p[3]),MONTHS[p[2][:3]],int(p[1]))
def duration(t,comp):
    if "All Abilities" in comp: return 25
    if "MiniRoos" in t or re.search(r'U0[6-9]\b',t) or "U10" in t or "U11" in t: return 40
    if "Seniors" in t or "Reserves" in t: return 90
    if re.search(r'U2[013]\b',t): return 90
    if re.search(r'U1[78]\b',t) or "17/18" in t: return 70
    if re.search(r'U1[56]\b',t): return 70
    if re.search(r'U1[234]\b',t): return 60
    return 60
def age_token(t):
    if "17/18" in t: return "U17/18"
    m=re.search(r'(U\d{2}|Seniors|Reserves)',t); return m.group(1) if m else ""
def field_info(pitch,ground):
    p=pitch.replace(ground,"").strip()
    m=re.search(r'Pitch\s+(\d+)',p); num=m.group(1) if m else "?"
    after=p[m.end():].lstrip() if m else ""
    letter=after[0] if after and after[0].isalpha() and not after.startswith("(") else ""
    return num,("Sub" if (letter or "Midi" in p) else "Full"),p
def fmt(m): return f"{m//60:02d}:{m%60:02d}"
games=[]
for ground,path in files.items():
    for date_s,time_s,home,away,comp,pitch,rnd in read(path):
        d=parse_date(date_s); hh,mm=map(int,time_s.split(":")); start=hh*60+mm
        dur=duration(home+" "+away,comp); num,ftype,plabel=field_info(pitch,ground)
        games.append(dict(date=d,iso=d.isoformat(),datedisp=d.strftime("%a %d %b"),day=date_s.split()[0],time=time_s,start=start,
            end=start+dur,endt=fmt(start+dur),ground=ground,field=num,ftype=ftype,pitch=plabel,
            age=age_token(home if "Manningham" in home else away+" "+home),home=home,away=away,comp=comp.split("|")[0].strip(),
            grade=comp.split("|")[1].strip() if "|" in comp else "",rnd=rnd.replace("Round ","R"),clash=False))
buckets={}
for g in games: buckets.setdefault((g["ground"],g["iso"],g["field"]),[]).append(g)
for gs in buckets.values():
    for a,b in combinations(gs,2):
        if a["start"]<b["end"] and b["start"]<a["end"]:
            if a["ftype"]=="Sub" and b["ftype"]=="Sub" and a["pitch"]!=b["pitch"]: continue
            a["clash"]=b["clash"]=True
peak={}; dd={}
for g in games: dd.setdefault((g["ground"],g["iso"]),[]).append(g)
for (gr,iso),gs in dd.items():
    evs=[]
    for g in gs: evs+=[(g["start"],1,g),(g["end"],-1,g)]
    evs.sort(key=lambda e:(e[0],e[1])); cur=0; act=[]
    for t,typ,g in evs:
        if typ==1:
            cur+=1; act.append(g)
            if gr not in peak or cur>peak[gr]["n"]:
                peak[gr]=dict(n=cur,date=gs[0]["date"].strftime("%a %d %b %Y"),frm=fmt(t),until=fmt(min(x["end"] for x in act)),pitches=sorted({x["pitch"] for x in act}))
        else:
            cur-=1; act=[x for x in act if x is not g]
games.sort(key=lambda g:(g["date"],g["start"],g["ground"]))
gsummary=[]
for gr in ["Pettys Reserve","Powerful Owl Park","Timber Ridge Reserve"]:
    gg=[g for g in games if g["ground"]==gr]
    gsummary.append(dict(ground=gr,n=len(gg),
        rng=f'{min(x["date"] for x in gg).strftime("%d %b")} – {max(x["date"] for x in gg).strftime("%d %b")}' if gg else "–",peak=peak.get(gr)))
rows=[{k:g[k] for k in ("iso","datedisp","day","time","endt","ground","field","ftype","pitch","age","home","away","comp","grade","rnd","clash")} for g in games]
DATA=json.dumps(rows); SUM=json.dumps(gsummary)
TEMPLATE=r'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Manningham – Fixtures & Overlap Check</title>
<style>
:root{--navy:#1f3864;--blue:#2e5aac;--ink:#1a1a1a;--mut:#667;--line:#e3e7ee;--band:#f6f8fb;--green:#2e7d32;}
*{box-sizing:border-box}body{margin:0;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:var(--ink)}
header{background:linear-gradient(120deg,var(--navy),var(--blue));color:#fff;padding:26px 22px}
header h1{margin:0 0 4px;font-size:22px}header p{margin:0;opacity:.85;font-size:13px}
.wrap{max-width:1200px;margin:0 auto;padding:20px 22px 60px}
.cards{display:flex;flex-wrap:wrap;gap:14px;margin:18px 0}
.card{flex:1;min-width:170px;background:var(--band);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.card .n{font-size:26px;font-weight:700;color:var(--navy)}.card .l{font-size:12px;color:var(--mut);margin-top:2px}.card .s{font-size:12px;color:var(--mut);margin-top:6px}
h2{font-size:15px;color:var(--navy);margin:26px 0 10px;border-bottom:2px solid var(--line);padding-bottom:6px}
.ok{background:#eaf5ea;border:1px solid #cfe7cf;color:#1e5220;border-radius:10px;padding:12px 14px;font-size:13px}
.meth{color:var(--mut);font-size:12px;margin-top:8px;line-height:1.5}
.peak{width:100%;border-collapse:collapse;margin-top:8px;font-size:13px}
.peak th,.peak td{border:1px solid var(--line);padding:7px 9px;text-align:left}
.peak th{background:var(--navy);color:#fff;font-weight:600}.peak td.n{text-align:center;font-weight:700;color:var(--navy)}
.controls{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:6px 0 12px;position:sticky;top:0;background:#fff;padding:10px 0;z-index:5}
.chip{border:1px solid var(--line);background:#fff;border-radius:20px;padding:6px 14px;font-size:13px;cursor:pointer;color:var(--mut)}
.chip.active{background:var(--navy);color:#fff;border-color:var(--navy)}
input[type=search]{flex:1;min-width:180px;border:1px solid var(--line);border-radius:8px;padding:8px 12px;font-size:13px}
.count{font-size:12px;color:var(--mut)}
table.games{width:100%;border-collapse:collapse;font-size:12.5px}
table.games th{position:sticky;top:56px;background:var(--navy);color:#fff;padding:8px 8px;text-align:left;cursor:pointer;white-space:nowrap;font-weight:600}
table.games td{border-bottom:1px solid var(--line);padding:6px 8px;vertical-align:top}
table.games tr:nth-child(even) td{background:var(--band)}
.g-pettys{color:#1f6feb}.g-powl{color:#8a5cf6}.g-timber{color:#0f9d58}
.badge{display:inline-block;font-size:10px;padding:1px 6px;border-radius:6px;background:#eef2f8;color:var(--mut)}
.full{background:#e8f0ff;color:#2e5aac}
.tag-date{font-weight:600;white-space:nowrap}
.foot{color:var(--mut);font-size:11px;margin-top:22px}
</style></head><body>
<header><h1>Manningham United Blues &ndash; Fixtures &amp; Overlap Check</h1>
<p>Pettys Reserve &middot; Powerful Owl Park &middot; Timber Ridge Reserve &nbsp;|&nbsp; Source: fv.dribl.com (2026 season)</p></header>
<div class="wrap">
<div class="cards" id="cards"></div>
<h2>Overlap &amp; clash check</h2>
<div id="okbox"></div>
<div class="meth"><b>Clash logic:</b> two games on the same ground + field number whose times overlap, where at least one uses the full field or both use the exact same pitch (two different sub-pitches at once are not a clash). Durations estimated: MiniRoos 40m, All-Abilities 25m, U12&ndash;14 60m, U15&ndash;18 70m, Seniors/U20&ndash;23 90m.</div>
<h2>Peak simultaneous games per ground</h2>
<table class="peak"><thead><tr><th>Ground</th><th>Max at once</th><th>Date</th><th>From</th><th>Until</th><th>Pitches in use then</th></tr></thead><tbody id="peakbody"></tbody></table>
<h2>All fixtures</h2>
<div class="controls"><span id="chips"></span><input type="search" id="q" placeholder="Search team, competition, pitch, age…"><span class="count" id="count"></span></div>
<table class="games"><thead><tr>
<th data-k="iso">Date</th><th data-k="time">KO</th><th data-k="endt">End</th><th data-k="ground">Ground</th>
<th data-k="pitch">Pitch</th><th data-k="ftype">Type</th><th data-k="age">Age</th>
<th data-k="home">Home</th><th data-k="away">Away</th><th data-k="comp">Competition</th><th data-k="grade">Grade</th><th data-k="rnd">Rnd</th>
</tr></thead><tbody id="tb"></tbody></table>
<div class="foot">Click a column header to sort. Estimated match durations are used only for the overlap check.</div>
</div>
<script>
const DATA=__DATA__, SUM=__SUM__;
const gsh=g=>g==="Pettys Reserve"?"Pettys":g==="Powerful Owl Park"?"Powerful Owl":"Timber Ridge";
const gcl=g=>g==="Pettys Reserve"?"g-pettys":g==="Powerful Owl Park"?"g-powl":"g-timber";
const clashes=DATA.filter(g=>g.clash).length;
document.getElementById('cards').innerHTML=
 '<div class="card"><div class="n">'+DATA.length+'</div><div class="l">Total home fixtures</div></div>'+
 SUM.map(s=>'<div class="card"><div class="n">'+s.n+'</div><div class="l">'+s.ground+'</div><div class="s">'+s.rng+'</div></div>').join('')+
 '<div class="card"><div class="n" style="color:'+(clashes?'#c0392b':'#2e7d32')+'">'+clashes+'</div><div class="l">Field double-bookings</div></div>';
document.getElementById('okbox').innerHTML=clashes?
 '<div class="ok" style="background:#fdeceb;border-color:#f0c9c4;color:#8a2b22">'+clashes+' game(s) share a physical field at overlapping times – see highlighted rows.</div>':
 '<div class="ok">&#10003; <b>No physical double-bookings.</b> Concurrent games always sit on separate pitches / sub-pitches.</div>';
document.getElementById('peakbody').innerHTML=SUM.map(s=>s.peak?
 '<tr><td>'+s.ground+'</td><td class="n">'+s.peak.n+'</td><td>'+s.peak.date+'</td><td>'+s.peak.frm+'</td><td>'+s.peak.until+'</td><td>'+s.peak.pitches.join(', ')+'</td></tr>':'').join('');
let ground="All",q="",sortk="iso",asc=true;
const chips=["All","Pettys Reserve","Powerful Owl Park","Timber Ridge Reserve"];
document.getElementById('chips').innerHTML=chips.map(c=>'<span class="chip'+(c==='All'?' active':'')+'" data-g="'+c+'">'+(c==='All'?'All grounds':gsh(c))+'</span>').join('');
document.querySelectorAll('.chip').forEach(el=>el.onclick=()=>{ground=el.dataset.g;document.querySelectorAll('.chip').forEach(x=>x.classList.toggle('active',x===el));render();});
document.getElementById('q').oninput=e=>{q=e.target.value.toLowerCase();render();};
document.querySelectorAll('table.games th').forEach(th=>th.onclick=()=>{const k=th.dataset.k;asc=(sortk===k)?!asc:true;sortk=k;render();});
function render(){
 let r=DATA.filter(g=>(ground==="All"||g.ground===ground));
 if(q)r=r.filter(g=>(g.home+' '+g.away+' '+g.comp+' '+g.pitch+' '+g.age+' '+g.datedisp).toLowerCase().includes(q));
 r=r.slice().sort((a,b)=>{let x=a[sortk],y=b[sortk];if(sortk==='iso'){x=a.iso+a.time;y=b.iso+b.time;}return (x>y?1:x<y?-1:0)*(asc?1:-1);});
 document.getElementById('count').textContent=r.length+' of '+DATA.length;
 document.getElementById('tb').innerHTML=r.map(g=>'<tr>'+
  '<td class="tag-date">'+g.datedisp+'</td><td>'+g.time+'</td><td>'+g.endt+'</td>'+
  '<td class="'+gcl(g.ground)+'">'+gsh(g.ground)+'</td>'+
  '<td>'+g.pitch+'</td><td><span class="badge '+(g.ftype==='Full'?'full':'')+'">'+g.ftype+'</span></td>'+
  '<td>'+g.age+'</td><td>'+g.home+'</td><td>'+g.away+'</td><td>'+g.comp+'</td><td>'+g.grade+'</td><td>'+g.rnd+'</td></tr>').join('');
}
render();
</script></body></html>'''
open(OUT,"w",encoding="utf-8").write(TEMPLATE.replace("__DATA__",DATA).replace("__SUM__",SUM))
print("fixtures:",len(games),"games ->",OUT)
