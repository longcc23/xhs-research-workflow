"""Extract image text and video captions with explicit coverage; no LLM calls."""
import argparse,json,pathlib,subprocess,concurrent.futures,hashlib
from research import save

def download(url,path):
 if path.exists() and path.stat().st_size:return
 pending=path.with_suffix(path.suffix+'.part')
 try:
  subprocess.run(['curl','--fail','--silent','--show-error','--location','--max-time','45','--referer','https://www.xiaohongshu.com/',url.replace('http://','https://',1),'-o',str(pending)],check=True,capture_output=True)
  if not pending.stat().st_size:raise RuntimeError('Empty media response')
  pending.replace(path)
 finally:
  pending.unlink(missing_ok=True)

def cached_ocr(path,executable):
 # Reusing a successful extraction avoids reprocessing every image on a note retry.
 sidecar=path.with_suffix('.ocr.json')
 signature=hashlib.sha256(path.read_bytes()).hexdigest()+':'+str(pathlib.Path(executable).stat().st_mtime_ns)
 if sidecar.exists():
  try:
   cached=json.loads(sidecar.read_text())
   if cached.get('signature')==signature:return cached['data']
  except (ValueError,KeyError):pass
 result=subprocess.run([executable,str(path)],capture_output=True,text=True,timeout=60,check=True)
 data=json.loads(result.stdout)
 if 'lines' not in data:raise RuntimeError('OCR did not return lines')
 save(sidecar,{'signature':signature,'data':data})
 return data

def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',required=True);p.add_argument('--cache',required=True);p.add_argument('--ocr',required=True);a=p.parse_args()
 source=pathlib.Path(a.evidence);e=json.loads(source.read_text());cache=pathlib.Path(a.cache);cache.mkdir(parents=True,exist_ok=True)
 target=source.parent/'media.json'; state=json.loads(target.read_text()) if target.exists() else {}
 def read(pair):
  fid,d=pair;n=d['data']['note'];folder=cache/fid;folder.mkdir(exist_ok=True)
  record={'type':n['type'],'images':[],'subtitle':'','errors':[],'visual_coverage':'image_ocr' if n['type']!='video' else 'not_viewed'}
  if n['type']=='video':
   subs=n.get('video',{}).get('subtitles',{}); choices=subs.get('source',[])+subs.get('zh-CN',[])
   for sub in choices:
    try:
     f=folder/'captions.srt';download(sub['url'],f);record['subtitle']=f.read_text();break
    except Exception as ex:record['errors'].append('subtitle: '+str(ex))
   record['duration_seconds']=n.get('video',{}).get('capa',{}).get('duration')
   record['caption_coverage']='available_platform_subtitles' if record['subtitle'] else 'missing'
  else:
   for i,im in enumerate(n.get('imageList',[]),1):
    r={'index':i}
    try:
     f=folder/f'{i}.jpg';download(im['urlDefault'],f)
     data=cached_ocr(f,a.ocr);r['text']='\n'.join(data.get('lines',[]));r['path']=str(f);r['status']='ocr_extracted' if 'lines' in data else 'error'
    except Exception as ex:r['status']='error';r['error']=str(ex)
    record['images'].append(r)
  return fid,record
 missing=[(fid,d) for fid,d in e['details'].items() if fid not in state or state[fid].get('errors') or state[fid].get('caption_coverage')=='missing' or any(i.get('status')=='error' for i in state[fid].get('images',[]))]
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
  for fid,r in pool.map(read,missing):
   state[fid]=r;save(target,state);print(json.dumps({'id':fid,'images':len(r['images']),'subtitle_chars':len(r['subtitle']),'errors':len(r['errors'])}),flush=True)
if __name__=='__main__':main()
