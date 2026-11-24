from pathlib import Path
import urllib.request,concurrent.futures,json,hashlib
R=Path.cwd()/'research/op-all-japanese-v3/official-reference';base='https://web.archive.org/web/20160716153107id_/http://cotton-soft.com/gameproducts/02_recon/';paths=['chara/mahoko.jpg','chara/kureha.jpg','chara/momiji.jpg','chara/shiina.jpg','chara/masaki.jpg','chara/mahomama.jpg']
def fetch(p):
 try:
  r=urllib.request.urlopen(base+p,timeout=20);b=r.read();fn=p.replace('/','__');(R/fn).write_bytes(b);print(fn,len(b),flush=True);return {'path':p,'url':r.url,'file':fn,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
 except Exception as e:print(p,str(e),flush=True);return {'path':p,'error':str(e)}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:rr=list(ex.map(fetch,paths))
(R/'character-art.json').write_text(json.dumps(rr,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')