#!/usr/bin/env python3
import json, os, sys
from google.oauth2 import service_account
from googleapiclient.discovery import build
DOC_ID='1N4tTesYjhAsQ3uJ1p_nqKVXNWBQzdVtPfdTD6Xdp4VM'; OUT='/tmp/announcement_sections.json'
raw=os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON','')
if not raw: raise SystemExit('GOOGLE_SERVICE_ACCOUNT_JSON is required')
creds=service_account.Credentials.from_service_account_info(json.loads(raw),scopes=['https://www.googleapis.com/auth/documents.readonly'])
d=build('docs','v1',credentials=creds,cache_discovery=False).documents().get(documentId=DOC_ID,includeTabsContent=True).execute()
def bodies(x):
 if 'body' in x: yield x['body']
 for tab in x.get('tabs',[]):
  dt=tab.get('documentTab',{})
  if 'body' in dt: yield dt['body']
def text(p): return ''.join(e.get('textRun',{}).get('content','') for e in p.get('elements',[])).strip()
sections=[]; cur=None
for body in bodies(d):
 for el in body.get('content',[]):
  p=el.get('paragraph')
  if not p: continue
  t=text(p); style=p.get('paragraphStyle',{}).get('namedStyleType','')
  if style=='HEADING_1' and t: cur={'header':t,'items':[]}; sections.append(cur)
  elif cur and t: cur['items'].append(t)
json.dump(sections,open(OUT,'w'))
print(f'announcements: {len(sections)} sections')
