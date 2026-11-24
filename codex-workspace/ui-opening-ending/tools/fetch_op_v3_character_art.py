from pathlib import Path
import urllib.request,concurrent.futures,json,re
R=Path.cwd()/'research/op-all-japanese-v3/official-reference';base='https://web.archive.org/web/20160716153107id_/http://cotton-soft.com/gameproducts/02_recon/';paths=['mahoko.htm','kureha.htm','momizi.htm','siina.htm','masaki.htm','mahomama.htm']
def fetch(p):
 try:
  r=urllib.request.urlopen(base+p,timeout=18);b=r.read();(R/p).write_bytes(b);s=b.decode('cp932','replace');links=re.findall(r'(?:src|href)=[\'\"]([^\'\"]+)',s);print(p,links,flush=True);return {'path':p,'url':r.url,'bytes':len(b),'links':links}
 except Exception as e:print(p,str(e),flush=True);return {'path':p,'error':str(e)}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:rr=list(ex.map(fetch,paths))
(R/'character-pages.json').write_text(json.dumps(rr,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')