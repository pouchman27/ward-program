"""Drop announcements whose date has already passed (ward time, America/New_York)."""
import re, datetime
from zoneinfo import ZoneInfo
MONTHS = {'jan':1,'feb':2,'mar':3,'apr':4,'may':5,'jun':6,'jul':7,'aug':8,'sep':9,'oct':10,'nov':11,'dec':12}
MON = r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?'
TEXT_DATE = re.compile(r'\b' + MON + r'\s+(\d{1,2})(?:\s*(?:-|to)\s*(?:' + MON + r'\s+)?(\d{1,2}))?(?:st|nd|rd|th)?(?:,?\s+(20\d\d))?\b', re.I)
NUM_DATE = re.compile(r'(?<![\d/])(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?(?![\d/])')

def today():
    return datetime.datetime.now(ZoneInfo('America/New_York')).date()

def _resolve(m, d, y, now):
    try:
        if y:
            y = int(y); y = y + 2000 if y < 100 else y
            return datetime.date(y, m, d)
        c = datetime.date(now.year, m, d)
        if (now - c).days > 200: c = datetime.date(now.year + 1, m, d)
        return c
    except ValueError:
        return None

def item_dates(text, now):
    out = []
    for m in TEXT_DATE.finditer(text):
        mon = MONTHS[m.group(1).lower()[:3]]
        d1 = int(m.group(2)); out.append(_resolve(mon, d1, m.group(5), now))
        if m.group(4):
            mon2 = MONTHS[m.group(3).lower()[:3]] if m.group(3) else mon
            out.append(_resolve(mon2, int(m.group(4)), m.group(5), now))
    for m in NUM_DATE.finditer(text):
        if int(m.group(1)) <= 12: out.append(_resolve(int(m.group(1)), int(m.group(2)), m.group(3), now))
    return [x for x in out if x]

def is_stale(text, now=None):
    now = now or today()
    ds = item_dates(text, now)
    return bool(ds) and max(ds) < now

def prune(sections, now=None):
    now = now or today(); kept, dropped = [], []
    for s in sections:
        items = []
        for it in s['items']:
            (dropped if is_stale(it, now) else items).append(it if items is not dropped else it)
        if items: kept.append({'header': s['header'], 'items': items})
    return kept, dropped
