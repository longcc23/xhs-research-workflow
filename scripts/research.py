"""Resumable, read-only Xiaohongshu collection. Raw evidence stays on disk."""
import argparse, json, os, pathlib, time, urllib.request, urllib.parse
MCP_URL=os.environ.get('XHS_MCP_URL','http://127.0.0.1:18060/mcp')
SHARED_CATALOG=os.environ.get('XHS_READER_CATALOG')

def save(path, value):
    tmp=path.with_suffix('.tmp'); tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)); tmp.replace(path)

def call(name,args):
    token_file=os.environ.get('XHS_MCP_TOKEN_FILE')
    token=pathlib.Path(token_file).expanduser().read_text().strip() if token_file else ''
    body={'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':name,'arguments':args}}
    headers={'Content-Type':'application/json','Accept':'application/json'}
    if token: headers['Authorization']='Bearer '+token
    req=urllib.request.Request(MCP_URL,data=json.dumps(body).encode(),headers=headers)
    with urllib.request.urlopen(req,timeout=180) as r: data=json.load(r)
    if 'error' in data: raise RuntimeError(str(data['error']))
    result=data['result']; txt='\n'.join(x.get('text','') for x in result.get('content',[]))
    if result.get('isError'): raise RuntimeError(txt)
    try: return json.loads(txt)
    except json.JSONDecodeError: return {'message':txt}

def main():
    p=argparse.ArgumentParser(); p.add_argument('--query',action='append',required=True); p.add_argument('--limit',type=int,default=30); p.add_argument('--details',type=int,default=0,help='0 = all notes; positive = explicit partial detail cap'); p.add_argument('--out',required=True); p.add_argument('--retry-partial',action='store_true')
    a=p.parse_args()
    if a.limit<1 or a.details<0: p.error('limit must be positive; details nonnegative')
    out=pathlib.Path(a.out); out.mkdir(parents=True,exist_ok=True)
    statefile=out/'evidence.json'
    config={'queries':a.query,'limit_per_query':a.limit,'details':a.details}
    state=json.loads(statefile.read_text()) if statefile.exists() else {'config':config,'batches':[],'notes':{},'details':{},'events':[]}
    if state['config']!=config: p.error('Use a new output directory for a different brief')
    def event(kind,**kw):
        state['events'].append({'time':time.strftime('%Y-%m-%dT%H:%M:%S%z'),'kind':kind,**kw});save(statefile,state); print(json.dumps({'kind':kind,**kw},ensure_ascii=False),flush=True)
    login=call('check_login_status',{})
    if '已登录' not in login.get('message',''): raise RuntimeError('Shared session requires login')
    for q in a.query:
        prior=[b for b in state['batches'] if b['query']==q and b.get('status')=='ok']
        if prior and (not a.retry_partial or prior[-1].get('stop_reason')=='target_reached'):continue
        st=time.monotonic()
        try:
            data=call('search_feeds',{'keyword':q,'limit':a.limit}); feeds=data.get('feeds',[])
            for rank,f in enumerate(feeds,1):
                fid=f['id']; n=state['notes'].setdefault(fid,{'feed':f,'appearances':[]}); n['feed']=f
                n['appearances'].append({'query':q,'rank':rank})
            state['batches'].append({'query':q,'status':'ok','count':len(feeds),'stop_reason':data.get('stop_reason'),'batches':data.get('batches'),'seconds':round(time.monotonic()-st,2)})
            event('search_complete',query=q,count=len(feeds),unique_total=len(state['notes']),stop_reason=data.get('stop_reason'))
        except Exception as e:
            state['batches'].append({'query':q,'status':'error','error':str(e)})
            event('search_error',query=q,error=str(e))
            break
    # Preserve search order. Never privilege an earlier case's topic.
    ordered=list(state['notes'])
    for fid in (ordered if a.details == 0 else ordered[:a.details]):
        if fid in state['details']:continue
        f=state['notes'][fid]['feed']
        try:
            data=call('get_feed_detail',{'feed_id':fid,'xsec_token':f['xsecToken']})
            if not data.get('data',{}).get('note'):raise RuntimeError('No note in response')
            state['details'][fid]=data
            event('detail_complete',id=fid,comments=len(data['data'].get('comments',{}).get('list',[])))
        except Exception as e:event('detail_error',id=fid,error=str(e))
    comments=sum(len(d['data'].get('comments',{}).get('list',[])) for d in state['details'].values())
    ok_queries={b['query'] for b in state['batches'] if b.get('status')=='ok'}
    reached={b['query'] for b in state['batches'] if b.get('status')=='ok' and b.get('stop_reason')=='target_reached'}
    status='complete' if len(reached)==len(set(a.query)) and state['notes'] and len(state['details'])==len(state['notes']) else ('partial' if state['details'] else 'failed')
    summary={'status':status,'unique_notes':len(state['notes']),'details_success':len(state['details']),'first_level_comments':comments,'batches':state['batches'],'video_coverage':'metadata_only','image_coverage':'not_read'}
    save(out/'summary.json',summary)
    catalog={'notes':[{'rank':i,'title':n['feed']['noteCard']['displayTitle'],'author':n['feed']['noteCard']['user'].get('nickname',''),'url':'https://www.xiaohongshu.com/explore/'+fid+'?'+urllib.parse.urlencode({'xsec_token':n['feed']['xsecToken'],'xsec_source':'pc_search'})} for i,(fid,n) in enumerate(state['notes'].items(),1)]}
    save(out/'reader-catalog.json',catalog)
    # Shared-reader updates are opt-in; research output stays local by default.
    if SHARED_CATALOG:
        shared=pathlib.Path(SHARED_CATALOG).expanduser()
        shared.parent.mkdir(parents=True,exist_ok=True)
        previous=json.loads(shared.read_text()) if shared.exists() else {'notes':[]}
        merged={urllib.parse.urlparse(n['url']).path:n for n in previous['notes']}
        merged.update({urllib.parse.urlparse(n['url']).path:n for n in catalog['notes']})
        save(shared,{'notes':list(merged.values())})
    event('finished',**{k:v for k,v in summary.items() if k!='batches'})
    if status=='failed': raise SystemExit(1)

if __name__=='__main__': main()
