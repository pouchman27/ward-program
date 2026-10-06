"""Move past-dated announcement bullets from the leaders' Doc into a graveyard section at the bottom.
Only bullets under a normal heading are touched. The graveyard is never shown on the site."""
import datetime
from zoneinfo import ZoneInfo
from prune import is_stale
GRAVE_TITLE = 'Graveyard of old announcements (not shown on the site)'

def is_grave(t): return t.lower().startswith('graveyard')

def ptext(p): return ''.join(e.get('textRun', {}).get('content', '') for e in p.get('elements', [])).strip()

def clean_doc(docs, doc_id, d, extra_entries=None):
    reqs, moved = [], list(extra_entries or [])
    tab = (d.get('tabs') or [None])[0]
    if not tab: return []
    tid = tab['tabProperties']['tabId']
    els = tab['documentTab']['body']['content']
    last = els[-1]['endIndex']; cur = None; grave = False
    tail_empty = not ptext(els[-1].get('paragraph', {}))
    dels = []
    for el in els:
        p = el.get('paragraph')
        if not p: continue
        t = ptext(p)
        if p.get('paragraphStyle', {}).get('namedStyleType') == 'HEADING_1' and t:
            if is_grave(t): grave = True; cur = None; continue
            cur = t; continue
        if grave or not (cur and t): continue
        if is_stale(t):
            dels.append(el); moved.append((cur, t))
    if not moved: return []
    today = datetime.datetime.now(ZoneInfo('America/New_York')).strftime('%b %-d')
    def rng(s, e): return {'startIndex': s, 'endIndex': e, 'tabId': tid}
    idx = last - 1
    lines = [f'{h}: {t}  (moved {today})' for h, t in moved]
    head = '' if grave else GRAVE_TITLE + '\n'
    body = '\n'.join(lines) + '\n'
    prefix = '' if tail_empty else '\n'
    text = prefix + head + body
    reqs.append({'insertText': {'location': {'index': idx, 'tabId': tid}, 'text': text}})
    s0 = idx + len(prefix)
    if head:
        reqs.append({'updateParagraphStyle': {'range': rng(s0, s0 + len(head)), 'fields': 'namedStyleType,borderTop',
            'paragraphStyle': {'namedStyleType': 'HEADING_1', 'borderTop': {'color': {'color': {'rgbColor': {'red': .3, 'green': .3, 'blue': .3}}}, 'width': {'magnitude': 1.5, 'unit': 'PT'}, 'padding': {'magnitude': 12, 'unit': 'PT'}, 'dashStyle': 'SOLID'}}}})
        s0 += len(head)
    reqs.append({'updateParagraphStyle': {'range': rng(s0, s0 + len(body)), 'fields': 'namedStyleType',
        'paragraphStyle': {'namedStyleType': 'NORMAL_TEXT'}}})
    for el in sorted(dels, key=lambda e: -e['startIndex']):
        reqs.append({'deleteContentRange': {'range': rng(el['startIndex'], min(el['endIndex'], last - 1))}})
    docs.batchUpdate(documentId=doc_id, body={'requests': reqs, 'writeControl': {'requiredRevisionId': d['revisionId']}}).execute()
    for h, t in moved: print('moved to Doc graveyard:', h, '|', t[:100])
    print(f'doc cleanup: {len(moved)} stale items moved to graveyard')
    return moved
