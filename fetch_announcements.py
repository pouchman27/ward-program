#!/usr/bin/env python3
import json, os, sys
from google.oauth2 import service_account
from googleapiclient.discovery import build
DOC_ID='1N4tTesYjhAsQ3uJ1p_nqKVXNWBQzdVtPfdTD6Xdp4VM'; OUT='/tmp/announcement_sections.json'
raw=os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON','')
if not raw: raise SystemExit('GOOGLE_SERVICE_ACCOUNT_JSON is required')
creds=service_account.Credentials.from_service_account_info(json.loads(raw),scopes=['https://www.googleapis.com/auth/documents'])
docs=build('docs','v1',credentials=creds,cache_discovery=False).documents()
d=docs.get(documentId=DOC_ID,includeTabsContent=True).execute()
from prune import is_stale
def clean_doc(d):
 # delete only paragraphs under a heading whose dates are all past; nothing else is touched
 reqs=[]; names=[]
 for tab in d.get('tabs',[]):
  dt=tab.get('documentTab',{}); tid=tab['tabProperties']['tabId']; els=dt.get('body',{}).get('content',[])
  if not els: continue
  last=els[-1]['endIndex']; cur=None
  for el in els:
   p=el.get('paragraph')
   if not p: continue
   t=text(p)
   if p.get('paragraphStyle',{}).get('namedStyleType')=='HEADING_1' and t: cur=t; continue
   if cur and t and is_stale(t):
    e=min(el['endIndex'],last-1)
    reqs.append({'deleteContentRange':{'range':{'startIndex':el['startIndex'],'endIndex':e,'tabId':tid}}}); names.append((cur,t))
 if reqs:
  reqs.sort(key=lambda r:-r['deleteContentRange']['range']['startIndex'])
  docs.batchUpdate(documentId=DOC_ID,body={'requests':reqs,'writeControl':{'requiredRevisionId':d['revisionId']}}).execute()
  for h,t in names: print('removed from Doc:',h,'|',t[:100])
 print(f'doc cleanup: {len(names)} stale items removed')
 return bool(reqs)
def bodies(x):
 if 'body' in x: yield x['body']
 for tab in x.get('tabs',[]):
  dt=tab.get('documentTab',{})
  if 'body' in dt: yield dt['body']
def text(p): return ''.join(e.get('textRun',{}).get('content','') for e in p.get('elements',[])).strip()
try:
 if clean_doc(d):
  d=docs.get(documentId=DOC_ID,includeTabsContent=True).execute()
except Exception as ex: print('WARN doc cleanup skipped:',ex)
sections=[]; cur=None
for body in bodies(d):
 for el in body.get('content',[]):
  p=el.get('paragraph')
  if not p: continue
  t=text(p); style=p.get('paragraphStyle',{}).get('namedStyleType','')
  if style=='HEADING_1' and t: cur={'header':t,'items':[]}; sections.append(cur)
  elif cur and t: cur['items'].append(t)
from prune import prune
sections, dropped = prune(sections)
for t in dropped: print('pruned stale announcement:', t[:100])
json.dump(sections,open(OUT,'w'))
print(f'announcements: {len(sections)} sections, {len(dropped)} stale items pruned')

