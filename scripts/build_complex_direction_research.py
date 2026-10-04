#!/usr/bin/env python3
"""Complex direction research v1.
Research-only. Rebuild logic is intentionally conservative: use only complex history
available by the prediction month; market forecast remains context-only until a
vintage-safe historical overlay is validated.
"""
import json, math
from pathlib import Path
from statistics import median
ROOT=Path(__file__).resolve().parents[1]
H=ROOT/"dist/kb_watchlist_history.json"; O=ROOT/"dist/complex_direction_research.json"
def pct(a,b): return None if a is None or b in (None,0) else (a/b-1)*100
def add(ym,n):
 y,m=int(ym[:4]),int(ym[4:])-1+n; y+=m//12; m%=12; return f"{y:04d}{m+1:02d}"
def feature_rows(data):
 sales={(i["name"],r["ym"]):r.get("sale") for i in data["items"] for r in i.get("series",[])}
 rows=[]
 for i in data["items"]:
  s=i.get("series",[])
  for k in range(6,len(s)):
   r,a,b,c=s[k],s[k-1],s[k-3],s[k-6]
   if any(x.get(z) is None for x,z in [(r,"sale"),(a,"sale"),(b,"sale"),(c,"sale"),(r,"rent"),(b,"rent"),(r,"rent_ratio"),(b,"rent_ratio")]): continue
   mx=max(x["sale"] for x in s[max(0,k-11):k+1] if x.get("sale") is not None)
   f=[pct(r["sale"],a["sale"]),pct(r["sale"],b["sale"]),pct(r["sale"],c["sale"]),pct(r["sale"],b["sale"])-pct(b["sale"],c["sale"]),pct(r["rent"],b["rent"]),r["rent_ratio"]-b["rent_ratio"],pct(r["sale"],mx)]
   rows.append({"name":i["name"],"ym":r["ym"],"sale":r["sale"],"rent":r["rent"],"rent_ratio":r["rent_ratio"],"f":f})
 for ym in sorted(set(r["ym"] for r in rows)):
  g=[r for r in rows if r["ym"]==ym]; m=median(r["f"][1] for r in g)
  for r in g:r["f"].append(r["f"][1]-m)
 for r in rows:
  for h in (3,6,12):r[f"y{h}"]=pct(sales.get((r["name"],add(r["ym"],h))),r["sale"])
 return rows
def predict(rows,t,h,loco=False,k=35):
 tr=[r for r in rows if r["ym"]<t["ym"] and add(r["ym"],h)<=t["ym"] and r.get(f"y{h}") is not None and (not loco or r["name"]!=t["name"])]
 if len(tr)<120:return None
 mu=[sum(r["f"][j] for r in tr)/len(tr) for j in range(8)]
 sd=[math.sqrt(sum((r["f"][j]-mu[j])**2 for r in tr)/max(1,len(tr)-1)) or 1 for j in range(8)]
 near=sorted(tr,key=lambda r:sum(((r["f"][j]-t["f"][j])/sd[j])**2 for j in range(8)))[:k]
 return median(r[f"y{h}"] for r in near)
if __name__=="__main__":
 rows=feature_rows(json.loads(H.read_text()))
 print(json.dumps({"status":"ok","feature_rows":len(rows),"complexes":len(set(r["name"] for r in rows)),"note":"Use committed validation artifact for certified metrics; this builder exposes the leakage-safe feature/prediction core."},ensure_ascii=False))
