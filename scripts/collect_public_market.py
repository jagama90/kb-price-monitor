#!/usr/bin/env python3
import json,re,datetime,pathlib,time,argparse
from playwright.sync_api import sync_playwright

ROOT=pathlib.Path(__file__).resolve().parents[1]
MASTER=ROOT/'data/buy_watchlist_master.json'
TARGETS=ROOT/'data/buy_watchlist_targets.json'
OUT=ROOT/'data/buy_watchlist_market.json'
DIST=ROOT/'dist/buy_watchlist_market.json'

def money(s):
    s=str(s or '').replace(',','').strip()
    total=0.0
    m=re.search(r'(\d+(?:\.\d+)?)억',s)
    if m:
        total+=float(m.group(1))*10000
        tail=s[m.end():]
        m2=re.search(r'(\d+)\s*만?',tail)
        if m2: total+=float(m2.group(1))
    else:
        m3=re.search(r'(\d+)\s*만',s)
        if m3: total+=float(m3.group(1))
    return round(total) if total else None

def norm(s):
    return re.sub(r'\s+','',str(s or '')).replace('아파트','').replace('(','').replace(')','').replace('마천역','')

def target_for(x,targets):
    n=norm(x.get('user_name') or x.get('kb_name'))
    for t in targets:
        tn=norm(t.get('name'))
        if tn==n or tn in n or n in tn: return t
    return None

def target_types(x,t):
    ts=x.get('types') or []
    if not t or t.get('min_pyeong') is None: return ts
    lo,hi=float(t['min_pyeong']),float(t['max_pyeong'])
    out=[]
    for a in ts:
        m=re.search(r'\d+(?:\.\d+)?',str(a.get('type_label') or ''))
        if m and lo<=float(m.group())<=hi: out.append(a)
    return out

def body(page):
    return page.locator('body').inner_text()

def current_type_text(t):
    m=re.search(r'\b(\d+[A-Za-z]?)평/',t)
    return m.group(1) if m else None

def select_type(page,label):
    # KB public page groups API variants such as 24A/24B/24C under the visible "24평" tab.
    m=re.search(r'\\d+(?:\\.\\d+)?',str(label or ''))
    if not m: raise RuntimeError(f'invalid type label: {label}')
    wanted=m.group(0)+'평'
    page.wait_for_timeout(250)
    matches=page.get_by_text(wanted,exact=True)
    clicked=False
    for i in range(matches.count()-1,-1,-1):
        try:
            el=matches.nth(i)
            if el.is_visible():
                el.click(force=True,timeout=3000)
                clicked=True
                break
        except Exception:
            pass
    if not clicked:
        raise RuntimeError(f'visible type tab not found: {wanted}')
    page.wait_for_timeout(900)

