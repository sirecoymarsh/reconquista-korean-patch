from pathlib import Path
import urllib.request,re,json,concurrent.futures,hashlib
from PIL import Image,ImageDraw
R=Path('research/op-all-japanese-v3/official-reference');s=(R/'wallpaper-page.html').read_text(encoding='utf-8',errors='replace');urls=list(dict.fromkeys(re.findall(r'href=[\"\'](http[^\"\']+20130917[^\"\']+\.jpg)',s,re.I)))
def dl(u):
 p=R/Path(u).name
 try:
  if p.exists():b=p.read_bytes()
  else:
   req=urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0','Referer':'https://life1001.blog50.fc2.com/blog-entry-1049.html'})
   with urllib.request.urlopen(req,timeout=15) as r:b=r.read()
   p.write_bytes(b)
  return {'url':u,'path':str(p),'sha256':hashlib.sha256(b).hexdigest()}
 except Exception as e:return {'url':u,'error':str(e)}
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as e:rows=list(e.map(dl,urls))
im=Image.new('RGB',(1200,240*((len(rows)+2)//3)),(30,30,30));d=ImageDraw.Draw(im)
for i,r in enumerate(rows):
 if 'path' not in r:continue
 p=Image.open(r['path']);p.thumbnail((400,215));x=i%3*400;y=i//3*240;im.paste(p,(x,y));d.text((x+2,y+218),Path(r['path']).name,fill='white')
im.save(R/'wallpaper-contact.png');(R/'wallpaper-download.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows))