#!/usr/bin/env python3
"""Copy ONLY the public program fields out of the source workbooks into the
middleware tables. This is the only code that reads the source workbooks.
Parses each weekly tab by label, never by fixed cell position. A tab or table
whose layout does not match is NOT copied; the previous middleware row stays
and the problem is reported."""
import sys, os, re, json, datetime, importlib.util
import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
import source_parser as gen

from clean_schema import SAC_COLUMNS,ACT_COLUMNS
MAX_LEN = 120
REQUIRED_LABELS = [r'^presiding$', r'^conducting', r'opening hymn', r'^invocation', r'sacrament hymn',
                   r'^speaker 1\s*:', r'closing hymn', r'^benediction']

def clip(v, problems, where):
    v = (v or '').strip()
    if len(v) > MAX_LEN:
        raise ValueError(f'{where}: value over {MAX_LEN} chars; retain last good row')
    return v

def sac_row(ws, problems):
    g = gen.Grid(ws)
    missing = [p for p in REQUIRED_LABELS if not g.find(p)]
    if missing:
        raise ValueError('layout mismatch, labels not found: ' + ', '.join(missing))
    p = gen.parse_program(ws)
    if not p: raise ValueError('no date found')
    w = ws.title
    sp = {x['n']: x['name'] for x in p.get('speakers', [])}
    def hy(k):
        h = p.get(k) or {}
        return h.get('number',''), h.get('title','')
    oh, sh, ih, ch = hy('opening_hymn'), hy('sacrament_hymn'), hy('intermediate_hymn'), hy('closing_hymn')
    mn = p.get('musical_number') or {}
    order = []
    for it in p.get('program_order', []):
        order.append({'speaker': f"S{it.get('n')}", 'hymn': 'IH', 'musical_number': 'MN'}[it['type']])
    row = {'Date': p['date'], 'Presiding': p.get('presiding',''), 'Conducting': p.get('conducting',''),
      'Organist': p.get('organist',''), 'Chorister': p.get('chorister',''),
      'Opening Hymn #': oh[0], 'Opening Hymn': oh[1], 'Invocation': p.get('invocation',''),
      'Sacrament Hymn #': sh[0], 'Sacrament Hymn': sh[1],
      'Speaker 1': sp.get(1,''), 'Speaker 2': sp.get(2,''), 'Speaker 3': sp.get(3,''), 'Speaker 4': sp.get(4,''),
      'Intermediate Hymn #': ih[0], 'Intermediate Hymn': ih[1],
      'Musical Number Song': mn.get('song',''), 'Musical Number Singers': mn.get('singers',''),
      'Musical Number Accompanist': mn.get('accompanied',''),
      'Closing Hymn #': ch[0], 'Closing Hymn': ch[1], 'Benediction': p.get('benediction',''),
      'Program Order': ','.join(order)}
    for k in SAC_COLUMNS:
        row[k] = clip(row[k], problems, f'{w} {k}')
    try:
        d = datetime.date.fromisoformat(row['Date'])
        if d.weekday() != 6: raise ValueError(f'{w}: date {d} is not a Sunday')
    except ValueError as exc:
        raise ValueError(str(exc))
    return row

def sac_rows(xlsx, since):
    wb = openpyxl.load_workbook(xlsx)
    rows, problems, skipped = {}, [], []
    for name in wb.sheetnames:
        if name in gen.SKIP_TABS: continue
        ws = wb[name]
        try:
            raw_date=gen.parse_program(ws)
            if raw_date and raw_date['date'] < since: continue
            if gen.parse_program.__name__ and not gen.Grid(ws).cells: continue
            pr = []
            r = sac_row(ws, pr)
            if r['Date'] < since: continue
            
            if r['Date'] in rows: raise ValueError('duplicate program date')
            problems += pr; rows[r['Date']] = r
        except Exception as e:
            skipped.append((name, str(e)))
    return rows, problems, skipped

# ---- activities ----
def act_rows(xlsx, year=2026):
    wb = openpyxl.load_workbook(xlsx)
    tab = f'{year} Activities'
    if tab not in wb.sheetnames: raise ValueError(f'tab {tab} not found')
    ws = wb[tab]
    hdr = None
    for r in range(1, 30):
        vals = {gen.s(ws.cell(row=r, column=c).value).lower(): c for c in range(1, 20)}
        if 'date' in vals and 'schedule' in vals and 'yw 12/13' in vals:
            hdr = (r, vals); break
    if not hdr: raise ValueError('header row (Date, Schedule, YW 12/13...) not found')
    hr, cols = hdr
    need = ['date','schedule','yw 12/13','yw 14/15','yw 16+','deacons','teachers','priests']
    miss = [n for n in need if n not in cols]
    if miss: raise ValueError('columns not found: ' + ', '.join(miss))
    notes_c = next((cols[k] for k in cols if 'notes' in k), None)
    ref_c = cols.get('reference')
    month, rows, problems = None, [], []
    for r in range(hr + 1, ws.max_row + 1):
        a = gen.s(ws.cell(row=r, column=1).value)
        if a:
            k = a.split('\n')[0].strip().rstrip('(').strip().lower()[:4]
            month = gen.MONTHS.get(k) or gen.MONTHS.get(k[:3]) or month
        try: day = int(float(ws.cell(row=r, column=cols['date']).value))
        except (TypeError, ValueError): continue
        if not month: continue
        try: d = datetime.date(year, month, day)
        except ValueError: problems.append(f'row {r}: bad date'); continue
        row = {'Date': d.isoformat(), 'Schedule': gen.s(ws.cell(row=r, column=cols['schedule']).value),
               'Notes': gen.s(ws.cell(row=r, column=notes_c).value) if notes_c else '',
               'Reference': gen.s(ws.cell(row=r, column=ref_c).value) if ref_c else ''}
        for gname in ['YW 12/13','YW 14/15','YW 16+','Deacons','Teachers','Priests']:
            row[gname] = gen.s(ws.cell(row=r, column=cols[gname.lower()]).value)
        for k in ACT_COLUMNS: row[k] = clip(row[k], problems, f'act {d}')
        rows.append(row)
    return rows, problems

if __name__ == '__main__':
    ag, act = sys.argv[1] if len(sys.argv) > 1 else '/tmp/ag.xlsx', sys.argv[2] if len(sys.argv) > 2 else '/tmp/act.xlsx'
    srows, sprob, sskip = sac_rows(ag, '0000-00-00')
    arows, aprob = act_rows(act)
    json.dump({'sacrament': [srows[k] for k in sorted(srows)], 'activities': arows}, open('/tmp/middleware_preview.json', 'w'), indent=1)
    print('sacrament rows', len(srows), 'problems', sprob, 'skipped', sskip)
    print('activity rows', len(arows), 'problems', aprob)
