from pathlib import Path
import urllib.request,concurrent.futures,json,re
R=Path.cwd()/'research/op-all-japanese-v3/official-reference';base='https://web.archive.org/web/20160716153107id_/http://cotton-soft.com/gameproducts/02_recon/'
paths=['chara.htm','etc.htm','top/top_a.jpg','top/top_b.jpg']
def fetch(p):
 try:
  r=urllib.request.urlopen(base+p,timeout=18);b=r.read();fn=p.replace('/','__');(R/fn).write_bytes(b);print(p,len(b),r.url,flush=True)
  if p.endswith('htm'):
   s=b.decode('cp932','replace');links=re.findall(r'(?:src|href)=[\'\"]([^\'\"]+)',s);print('LINKS',p,links,flush=True)
  return {'path':p,'url':r.url,'bytes':len(b)}
 except Exception as e:print(p,str(e),flush=True);return {'path':p,'error':str(e)}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:rr=list(ex.map(fetch,paths))
(R/'official-inventory.json').write_text(json.dumps(rr,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')