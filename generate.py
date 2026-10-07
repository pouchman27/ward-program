#!/usr/bin/env python3
"""Build the encrypted site only from the clean middleware and announcement input."""
import json, datetime, sys, os, glob, re
OUT=sys.argv[1] if len(sys.argv)>1 else os.path.join(os.path.dirname(__file__),'data.json')
SITE_PASSPHRASE=os.environ['WARD_SITE_PASSPHRASE']
YW_CLASS_NAMES = {'YW 12/13': 'Builders of Faith', 'YW 14/15': 'Messengers of Hope', 'YW 16+': 'Gatherers of Light'}
CAL_LOCATION = '1750 Windward Concourse, Alpharetta, GA'

def ics_escape(t):
    return t.replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,').replace('\n', '\\n')

def ics_fold(line):
    out = []
    while len(line.encode('utf-8')) > 74:
        cut = 74
        while cut > 0 and (line.encode('utf-8')[:cut+1].decode('utf-8', 'ignore') != line[:cut+1]):
            cut -= 1
        out.append(line[:cut])
        line = ' ' + line[cut:]
    out.append(line)
    return out

def parse_time_min(s):
    m = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)', s or '', re.I)
    if not m: return None
    hh = int(m.group(1)) % 12
    if m.group(3).lower().startswith('p'): hh += 12
    return hh * 60 + int(m.group(2) or 0)

def build_ics(programs, act):
    now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Milton Ward//Ward Program//EN',
             'CALSCALE:GREGORIAN', 'METHOD:PUBLISH', 'X-WR-CALNAME:Milton Ward',
             'X-WR-CALDESC:Sacrament meeting programs and youth activities for Milton Ward',
             'BEGIN:VTIMEZONE', 'TZID:America/New_York',
             'BEGIN:DAYLIGHT', 'TZOFFSETFROM:-0500', 'TZOFFSETTO:-0400', 'TZNAME:EDT',
             'DTSTART:19700308T020000', 'RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU', 'END:DAYLIGHT',
             'BEGIN:STANDARD', 'TZOFFSETFROM:-0400', 'TZOFFSETTO:-0500', 'TZNAME:EST',
             'DTSTART:19701101T020000', 'RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU', 'END:STANDARD',
             'END:VTIMEZONE']
    def ev(uid, date, start_min, end_min, summary, desc):
        d = date.replace('-', '')
        t = lambda m: f'{m//60:02d}{m%60:02d}00'
        lines.extend(['BEGIN:VEVENT', f'UID:{uid}', f'DTSTAMP:{now}',
                      f'DTSTART;TZID=America/New_York:{d}T{t(start_min)}',
                      f'DTEND;TZID=America/New_York:{d}T{t(end_min)}',
                      f'SUMMARY:{ics_escape(summary)}',
                      f'LOCATION:{ics_escape(CAL_LOCATION)}',
                      f'DESCRIPTION:{ics_escape(desc)}',
                      'END:VEVENT'])
    for p in programs:
        ev(f'sacrament-{p["date"]}@ward-program', p['date'], 9*60, 10*60+30,
           'Milton Ward Sacrament Meeting',
           'Sacrament meeting. Full program: https://pouchman27.github.io/ward-program/')
    if act and act.get('rows'):
        for r in act['rows']:
            st = parse_time_min(r.get('schedule'))
            start = st if st is not None else 19*60
            bits = [b for b in [r.get('schedule'), r.get('notes'), r.get('reference')] if b]
            grp = '; '.join(f'{YW_CLASS_NAMES.get(k, k)}: {v}' for k, v in (r.get('groups') or {}).items())
            desc = '\n'.join(bits + ([grp] if grp else []))
            ev(f'activity-{r["date"]}@ward-program', r['date'], start, start + 60,
               'Milton Ward Youth Activity', desc)
    out = []
    for ln in lines:
        out.extend(ics_fold(ln))
    out.append('END:VCALENDAR')
    return '\r\n'.join(out) + '\r\n'

def cal_event_manifest(programs, act):
    events = []
    for p in programs:
        events.append({'uid': f'sacrament-{p["date"]}', 'date': p['date'], 'start_min': 9*60, 'end_min': 10*60+30,
                       'summary': 'Milton Ward Sacrament Meeting',
                       'description': 'Sacrament meeting. Full program: https://pouchman27.github.io/ward-program/'})
    if act and act.get('rows'):
        for r in act['rows']:
            st = parse_time_min(r.get('schedule'))
            start = st if st is not None else 19*60
            bits = [b for b in [r.get('schedule'), r.get('notes'), r.get('reference')] if b]
            grp = '; '.join(f'{YW_CLASS_NAMES.get(k, k)}: {v}' for k, v in (r.get('groups') or {}).items())
            events.append({'uid': f'activity-{r["date"]}', 'date': r['date'], 'start_min': start, 'end_min': start+60,
                           'summary': 'Milton Ward Youth Activity',
                           'description': '\n'.join(bits + ([grp] if grp else []))})
    return events

def write_calendar(programs, act, data):
    base = os.path.dirname(os.path.abspath(__file__))
    token_path = os.path.join(base, '.cal-token')
    token = os.environ.get('WARD_CAL_TOKEN', '').strip()
    if not token:
        if os.path.exists(token_path):
            token = open(token_path).read().strip()
        else:
            token = os.urandom(32).hex()
            with open(token_path, 'w') as f:
                f.write(token)
            os.chmod(token_path, 0o600)
    cal_name = f'cal-{token}.ics'
    data['calendar_url'] = f'https://pouchman27.github.io/ward-program/{cal_name}'
    site_dir = base
    for old in glob.glob(os.path.join(site_dir, 'cal-*.ics')):
        if os.path.basename(old) != cal_name:
            os.remove(old)
    with open(os.path.join(site_dir, cal_name), 'w', newline='') as f:
        f.write(build_ics(programs, act))
    return cal_name

def main():
    from mw_reader import load_clean
    programs, act = load_clean()
    data = {
        'generated_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'ward_name': 'Milton Ward',
        'programs': programs,
        'activities': act,
    }
    ann_path = '/tmp/announcement_sections.json'
    if os.path.exists(ann_path):
        try: data['announcement_sections'] = json.load(open(ann_path))
        except Exception as e: print(f'WARN announcement sections: {e}', file=sys.stderr)
    cal_name = write_calendar(programs, act, data)
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cal_events.json'), 'w') as f:
        json.dump(cal_event_manifest(programs, act), f, indent=1)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    plaintext = json.dumps(data, indent=1).encode()
    # passphrase-gated payload: site/data.enc = salt16 + iv16 + AES-256-CBC(PBKDF2-HMAC-SHA256, 100k)
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes, padding
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    salt, iv = os.urandom(16), os.urandom(16)
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000)
    key = kdf.derive(SITE_PASSPHRASE.encode())
    padder = padding.PKCS7(128).padder()
    padded = padder.update(plaintext) + padder.finalize()
    ct = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
    enc = ct.update(padded) + ct.finalize()
    enc_path = os.path.join(os.path.dirname(OUT), 'data.enc')
    with open(enc_path, 'wb') as f:
        f.write(salt + iv + enc)
    if os.path.exists(OUT):  # never publish plaintext
        os.remove(OUT)
    assert 'advancements' not in data and 'sheet_url' not in data and 'sheet_url' not in (data.get('activities') or {})
    print(f'OK: {len(programs)} programs, encrypted payload at {enc_path}, calendar at site/{cal_name}')

if __name__ == '__main__':
    main()

