"""Rebuild site program/activities objects from middleware rows only."""
import json, os
HERE=os.path.dirname(os.path.abspath(__file__))
HYMN_URLS=json.load(open(os.path.join(HERE,'hymn_map.json')))
def hymn(num,title):
    if not (num or title): return None
    o={'number':num,'title':title}
    if num:
        if str(num) not in HYMN_URLS: raise ValueError(f'No official Church link mapped for hymn #{num}')
        o['url']=HYMN_URLS[str(num)]
    return o
def program(r):
    p={'date':r['Date'],'slug':r['Date']}
    for k,f in (('presiding','Presiding'),('conducting','Conducting'),('organist','Organist'),('chorister','Chorister'),('invocation','Invocation'),('benediction','Benediction')):
        if r[f]: p[k]=r[f]
    for k,f in (('opening_hymn','Opening Hymn'),('sacrament_hymn','Sacrament Hymn'),('closing_hymn','Closing Hymn')):
        h=hymn(r[f+' #'],r[f])
        if h: p[k]=h
    ih=hymn(r['Intermediate Hymn #'],r['Intermediate Hymn'])
    if ih: p['intermediate_hymn']=ih
    sp=[{'n':n,'name':r[f'Speaker {n}']} for n in (1,2,3,4) if r[f'Speaker {n}']]
    if sp: p['speakers']=sp
    mn={k:r[f] for k,f in (('song','Musical Number Song'),('singers','Musical Number Singers'),('accompanied','Musical Number Accompanist')) if r[f]}
    if mn: p['musical_number']=mn
    order=[]
    for t in filter(None,r['Program Order'].split(',')):
        if t.startswith('S') and t[1:] in ('1','2','3','4'): order.append({'type':'speaker','n':int(t[1:]),'name':r['Speaker '+t[1:]]})
        elif t=='IH': order.append({'type':'hymn','label':'Intermediate Hymn','hymn':ih})
        elif t=='MN': order.append({'type':'musical_number',**mn})
        else: raise ValueError('Invalid program order token')
    if order: p['program_order']=order
    return p
def activity(r):
    groups={g:r[g] for g in ['YW 12/13','YW 14/15','YW 16+','Deacons','Teachers','Priests'] if r[g]}
    return {'date':r['Date'],'schedule':r['Schedule'],'notes':r['Notes'],'reference':r['Reference'],'groups':groups}

def table_rows(values, columns):
    import datetime
    if not values or values[0] != columns: raise ValueError('Clean sheet header mismatch')
    rows=[]; seen=set()
    for cells in values[1:]:
        if not any(cells): continue
        if len(cells)>len(columns): raise ValueError('Unexpected sheet columns')
        r=dict(zip(columns,[str(v) for v in cells]+['']*(len(columns)-len(cells))))
        datetime.date.fromisoformat(r['Date'])
        if r['Date'] in seen: raise ValueError('Duplicate date')
        seen.add(r['Date']);rows.append(r)
    if not rows: raise ValueError('Clean sheet is empty')
    return rows

def load_clean():
    from clean_schema import SAC_ID,ACT_ID,SAC_COLUMNS,ACT_COLUMNS
    if os.environ.get('MIDDLEWARE_PREVIEW'):
        data=json.load(open(os.environ['MIDDLEWARE_PREVIEW']))
        sr=table_rows(data['sacrament'],SAC_COLUMNS);ar=table_rows(data['activities'],ACT_COLUMNS)
    else:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        creds=service_account.Credentials.from_service_account_info(json.loads(os.environ['GOOGLE_SERVICE_ACCOUNT_JSON']),scopes=['https://www.googleapis.com/auth/spreadsheets.readonly'])
        api=build('sheets','v4',credentials=creds,cache_discovery=False).spreadsheets().values()
        sr=table_rows(api.get(spreadsheetId=SAC_ID,range='Sacrament!A1:W1000',valueRenderOption='UNFORMATTED_VALUE').execute().get('values',[]),SAC_COLUMNS)
        ar=table_rows(api.get(spreadsheetId=ACT_ID,range='Activities!A1:J1000',valueRenderOption='UNFORMATTED_VALUE').execute().get('values',[]),ACT_COLUMNS)
    return sorted([program(r) for r in sr],key=lambda p:p['date'],reverse=True),{'rows':[activity(r) for r in ar]}
