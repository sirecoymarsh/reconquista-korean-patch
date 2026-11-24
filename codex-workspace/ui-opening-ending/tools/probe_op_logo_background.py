from pathlib import Path
import json,sys,struct,re
import numpy as np,cv2
from PIL import Image,ImageDraw
U=Path.cwd();O=U/'research/op-logo';rs=json.loads((O/'frames.json').read_text());r=next(r for r in rs if r['time']==27.0);src=np.array(Image.open(O/'bg_020c.png'));target=np.array(Image.open(r['path']));g=cv2.cvtColor(src,cv2.COLOR_RGB2GRAY);gt=cv2.cvtColor(target,cv2.COLOR_RGB2GRAY);sf=cv2.SIFT_create(nfeatures=6000);k,d=sf.detectAndCompute(g,None);mask=np.ones(gt.shape,np.uint8)*255;mask[:72]=0;mask[526:]=0;mask[((target[:,:,0].astype('int16')-target[:,:,1])>30)&(target[:,:,0]>80)]=0;kt,dt=sf.detectAndCompute(gt,mask);matches=cv2.BFMatcher().knnMatch(d,dt,k=2);good=[m for m,n in matches if m.distance<.7*n.distance];p=np.float32([k[m.queryIdx].pt for m in good]);q=np.float32([kt[m.trainIdx].pt for m in good]);H,inl=cv2.findHomography(p,q,cv2.RANSAC,1.8);pred=cv2.warpPerspective(src,H,(800,600));allowed=(mask>0)&(np.max(pred,2)>2);err=np.abs(target.astype('float32')-pred.astype('float32'));print(json.dumps({'matches':len(good),'inliers':int(inl.sum()),'H':H.tolist(),'clean_mean_abs_rgb_error':err[allowed].mean(axis=0).tolist()},indent=2));Image.fromarray(pred).save(O/'city-donor-registered.png');(O/'city-registration.json').write_text(json.dumps({'H':H.tolist(),'matches':len(good),'inliers':int(inl.sum())},indent=2))
sys.path.insert(0,str(U.parent/'tools'));from inspect_majiro import Arc
from raster_codec import raw_image
arc=Arc(U.parent/'research/disc/data.arc');es=[e for e in arc.entries if re.match(r'(c_|img|catch|last)',e['name']) and e['name'].endswith('.rct')];items=[]
with arc.path.open('rb') as f:
 for e in es:
  f.seek(e['offset']);b=f.read(e['size'])
  if b[4:8]!=b'TC00':continue
  a,_,_=raw_image(b);im=Image.fromarray(a);im.thumbnail((160,120));items.append((e['name'],im))
sheet=Image.new('RGB',(1280,138*((len(items)+7)//8)),(25,25,28));dd=ImageDraw.Draw(sheet)
for i,(name,im) in enumerate(items):x=i%8*160;y=i//8*138;sheet.paste(im,(x,y));dd.text((x+3,y+121),name,fill='white')
sheet.save(O/'additional-source-art.png')
