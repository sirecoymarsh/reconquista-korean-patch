from pathlib import Path
import sys,json,re,subprocess
import cv2,numpy as np
from PIL import Image,ImageDraw
U=Path.cwd();R=U/'research/op-all-japanese-v3';D=R/'sprite-donors';D.mkdir(exist_ok=True);sys.path.insert(0,str(U.parent/'tools'));from inspect_majiro import Arc
sys.path.insert(0,str(U/'tools'));from raster_codec import raw_image
cv2.setNumThreads(2);sift=cv2.SIFT_create(nfeatures=900);bf=cv2.BFMatcher()
targets={'maho':1134,'sina':1320,'masa':1500,'momi':1632,'kure':1902};tg={}
for k,n in targets.items():
 a=np.array(Image.open(R/'source-frames'/f'{n:04d}.png'));g=cv2.cvtColor(a,cv2.COLOR_RGB2GRAY);kp,ds=sift.detectAndCompute(g,None);tg[k]=(kp,ds,a)
arc=Arc(U.parent/'research/disc/slowdata.arc');rows=[]
with arc.path.open('rb') as fh:
 for e in arc.entries:
  mt=re.match(r'b_(maho|sina|masa|momi|kure)_.*\.rct$',e['name'])
  if not mt:continue
  fh.seek(e['offset']);header=fh.read(24)
  if header[4:8]!=b'TC00':continue
  fh.seek(e['offset']);b=fh.read(e['size']);arr,_,_=raw_image(b);small=cv2.resize(arr,(0,0),fx=.5,fy=.5);kp,ds=sift.detectAndCompute(cv2.cvtColor(small,cv2.COLOR_RGB2GRAY),None)
  if ds is None:continue
  kt,dt,_=tg[mt[1]];matches=bf.knnMatch(ds,dt,k=2);good=[a for a,b in matches if a.distance<.72*b.distance]
  count=0;H=None
  if len(good)>=5:
   aa=np.float32([kp[x.queryIdx].pt for x in good])*2;bb=np.float32([kt[x.trainIdx].pt for x in good]);H,inl=cv2.estimateAffinePartial2D(aa,bb,method=cv2.RANSAC,ransacReprojThreshold=3);count=int(inl.sum()) if inl is not None else 0
  rows.append({'name':e['name'],'character':mt[1],'size':[arr.shape[1],arr.shape[0]],'inliers':count,'matrix':None if H is None else H.tolist(),'offset':e['offset'],'bytes':e['size']})
  if len(rows)%30==0:print('sprites inspected',len(rows),flush=True)
for ch in targets:
 top=sorted([r for r in rows if r['character']==ch],key=lambda x:x['inliers'],reverse=True)[:5]
 with arc.path.open('rb') as fh:
  for r in top:
   fh.seek(r['offset']);arr,_,_=raw_image(fh.read(r['bytes']));Image.fromarray(arr).save(D/(r['name']+'.png'))
 im=Image.new('RGB',(1000,350),(25,25,25));dr=ImageDraw.Draw(im)
 for i,r in enumerate(top):
  a=Image.open(D/(r['name']+'.png'));a.thumbnail((200,310));im.paste(a,(i*200,0));dr.text((i*200+2,315),r['name'],fill='white');dr.text((i*200+2,331),str(r['inliers']),fill='white')
 im.save(R/f'sprite-top-{ch}.png');print(ch,[(r['name'],r['inliers']) for r in top],flush=True)
(R/'sprite-match.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')