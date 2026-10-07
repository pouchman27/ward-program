#!/usr/bin/env python3
"""Separate extraction job. Never part of the site's read/publish path."""
import json,os,tempfile,datetime,urllib.request
from zoneinfo import ZoneInfo
from google.oauth2 import service_account
from googleapiclient.discovery import build
from clean_schema import SAC_ID,ACT_ID,SAC_COLUMNS,ACT_COLUMNS
from mw_reader import table_rows,program
from sync_middleware import sac_rows,act_rows
SOURCES={
 'sacrament':'https://docs.google.com/spreadsheets/d/1fvw_Kyhy44Er_al2Ammw07KbXA39iBporF3bOF_B1aw/export?format=xlsx',
 'activities':'https://docs.google.com/spreadsheets/d/1_6NKa_YWGWKSLCINSjZeAUrhwWAj4hBrWWF88O7Qj-I/export?format=xlsx'}
def merge(existing,incoming,cutoff):
    result={r['Date']:r for r in existing}
    for r in incoming:
        if r['Date']>=cutoff: result[r['Date']]=r
    return [result[d] for d in sorted(result)]
def cells(rows,columns): return [columns]+[[r[c] for c in columns] for r in rows]
def main():
    today=datetime.datetime.now(ZoneInfo('America/New_York')).date()
    cutoff=(today-datetime.timedelta(days=14)).isoformat()
    creds=service_account.Credentials.from_service_account_info(json.loads(os.environ['GOOGLE_SERVICE_ACCOUNT_JSON']),scopes=['https://www.googleapis.com/auth/spreadsheets'])
    api=build('sheets','v4',credentials=creds,cache_discovery=False).spreadsheets().values()
    errors=[]
    with tempfile.TemporaryDirectory() as td:
        paths={}
        for k,url in SOURCES.items():
            paths[k]=os.path.join(td,k+'.xlsx');urllib.request.urlretrieve(url,paths[k])
        sr,prob,skipped=sac_rows(paths['sacrament'],cutoff);errors+=prob+[f'{t}: {e}' for t,e in skipped]
        # Whole activities layout must validate before copying any activity cells.
        ar,prob=act_rows(paths['activities'],today.year);errors+=prob
        for ident,tab,cols,incoming in [(SAC_ID,'Sacrament',SAC_COLUMNS,list(sr.values())),(ACT_ID,'Activities',ACT_COLUMNS,ar)]:
            current=table_rows(api.get(spreadsheetId=ident,range=f'{tab}!A1:W1000',valueRenderOption='UNFORMATTED_VALUE').execute().get('values',[]),cols)
            merged=merge(current,incoming,cutoff)
            if tab=='Sacrament':
                for r in merged: program(r) # official hymn/order validation before write
            if merged!=current:
                api.update(spreadsheetId=ident,range=f'{tab}!A1',valueInputOption='RAW',body={'values':cells(merged,cols)}).execute()
                got=table_rows(api.get(spreadsheetId=ident,range=f'{tab}!A1:W1000',valueRenderOption='UNFORMATTED_VALUE').execute().get('values',[]),cols)
                if got!=merged: raise RuntimeError('Middleware readback mismatch')
            print(tab, len(merged), 'rows; frozen before',cutoff)
    summary='\n'.join(['## Middleware sync','Only allowlisted fields copied. Invalid tabs retain their last good row.']+['- '+e for e in errors])
    if os.environ.get('GITHUB_STEP_SUMMARY'): open(os.environ['GITHUB_STEP_SUMMARY'],'a').write(summary+'\n')
    for e in errors: print('::warning::'+e)
if __name__=='__main__': main()
