"""Shared Dribl fixture parser.
Anchors on a [date line][time line] pair, so it reads BOTH the cleaned 8-line
raw files AND a full get_page_text() dump from fv.dribl.com (boilerplate,
date headers and 'Match Centre' lines are ignored automatically).
Returns tuples: (date_s, time_s, home, away, comp, pitch, rnd)
"""
import re, os
DATE_RE=re.compile(r'^[A-Za-z]{3}\s+\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}$')
TIME_RE=re.compile(r'^\d{1,2}:\d{2}$')

def clean_team(name):
    """Strip Dribl's redundant grade-code suffix from a team display name."""
    name=name.strip()
    # MUFC teams append '... MUFC - <grade> (<coach>)'; keep the real name + any coach paren
    if ' MUFC - ' in name:
        base,suf=name.split(' MUFC - ',1)
        m=re.search(r'(\([^)]*\))\s*$',suf)
        return (base.strip()+' '+m.group(1)).strip() if m else base.strip()
    # dedupe an immediately-repeated club prefix e.g. 'Caboolture Sports FC Caboolture Sports FC Senior Men'
    w=name.split()
    for k in range(5,1,-1):
        if len(w)>=2*k and w[:k]==w[k:2*k]:
            return ' '.join(w[:k]+w[2*k:])
    return name

def read(path):
    if not os.path.exists(path): return []
    lines=[l.strip() for l in open(path,encoding="utf-8") if l.strip()!=""]
    out=[]; i=0; n=len(lines)
    while i < n-4:
        if DATE_RE.match(lines[i]) and TIME_RE.match(lines[i+1]) and lines[i+3]=="-":
            date_s,time_s,home=lines[i],lines[i+1],clean_team(lines[i+2])
            away=clean_team(lines[i+4])
            comp=lines[i+5] if i+5<n else ""
            pitch=lines[i+6] if i+6<n else ""
            rnd=""
            for k in range(i+7,min(i+10,n)):
                if lines[k].startswith("Round "): rnd=lines[k]; break
            out.append((date_s,time_s,home,away,comp,pitch,rnd))
            i+=7
        else:
            i+=1
    return out
