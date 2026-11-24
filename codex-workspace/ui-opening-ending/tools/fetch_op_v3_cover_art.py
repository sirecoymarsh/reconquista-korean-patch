from pathlib import Path
import urllib.request,concurrent.futures,json,re,hashlib
R=Path.cwd()/'research/op-all-japanese-v3/official-reference';base='https://web.archive.org/web/20160716153107id_/http://cotton-soft.com/gameproducts/02_recon/'
urls=[('spec.htm',base+'spec.htm'),('trial.htm',base+'trial.htm'),('cover-vndb.jpg','https://s.vndb.org/cv/11/96111.jpg'),('chara__masaki.jpg',base+'chara/masaki.jpg'),('chara__mahomama.jpg',base+'chara/mahomama.jpg')]
def fetch(pair):
 fn,u=pair
 try:
  r=urllib.request.urlopen(u,timeout=15);b=r.read();(R/fn).write_bytes(b);out={'file':fn,'url':r.url,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()};print(out,flush=True)
  if fn.endswith('.htm'):print('LINKS',fn,re.findall(r'(?:src|href)=[\'\"]([^\'\"]+)',b.decode('cp932','replace')),flush=True)
  return out
 except Exception as e:print(fn,str(e),flush=True);return {'file':fn,'error':str(e)}
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:rr=list(ex.map(fetch,urls))
(R/'additional-art-requests.json').write_text(json.dumps(rr,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')