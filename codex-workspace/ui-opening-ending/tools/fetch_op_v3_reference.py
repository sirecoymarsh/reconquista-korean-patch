from pathlib import Path
import urllib.request,concurrent.futures,json,re
R=Path.cwd()/'research/op-all-japanese-v3/official-reference';R.mkdir(parents=True,exist_ok=True)
urls=[('getchu.html','https://www.getchu.com/soft.phtml?id=375925'),('archived-official.html','https://web.archive.org/web/20160716153107id_/http://cotton-soft.com/gameproducts/02_recon/index.htm'),('cover.webp','https://vnclub.org/img/cv/11/96111.webp?vn=v471&w=512'),('mahoko.html','https://vnclub.org/character/c31148/')]
def read(pair):
 fn,u=pair
 try:
  req=urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'});r=urllib.request.urlopen(req,timeout=18);b=r.read();(R/fn).write_bytes(b);print(fn,r.status,len(b),flush=True)
  if fn.endswith('.html'):
   s=b.decode('utf-8','replace')
   if fn=='getchu.html':s=b.decode('euc_jp','replace')
   print(fn,'IMAGES',re.findall(r'(?:src|href)=[\'\"]([^\'\"]+)',s)[:65],flush=True)
  return {'file':fn,'url':u,'status':r.status,'bytes':len(b)}
 except Exception as e:print(fn,str(e),flush=True);return {'file':fn,'url':u,'error':str(e)}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:rows=list(ex.map(read,urls))
(R/'requests.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8')