"""Exact same-state console button donor search; no asset changes."""
from pathlib import Path
import sys,json
import numpy as np,cv2
from PIL import Image
R=Path(__file__).resolve().parents[1];U=R/'ui-opening-ending';sys.path.insert(0,str(R/'tools'));from inspect_majiro import dump
D=U/'source/decoded';a=np.asarray(Image.open(D/'console_off_m.rct.png').convert('RGB'));pos=[300,350,400,450,501,551,601,651];t=np.stack([a[565:583,x:x+51] for x in pos]).astype('int32');white=(t[:,:,:,1]>100)&((t[:,:,:,0]-t[:,:,:,2])<60);g=np.stack([cv2.dilate(m.astype('uint8'),np.ones((5,5),np.uint8))>0 for m in white]);lo=np.where(g[:,:,:,None],256,t).min(0);hi=np.where(g[:,:,:,None],-1,t).max(0);cnt=(~g).sum(0);scope=np.zeros((18,51),bool);scope[4:14,4:47]=True;known=(cnt>0)&np.all(lo==hi,2)&scope;anchors=[(8,12),(8,37),(11,34),(6,7),(7,45)];result=[];seen=0;first=anchors[0];value=lo[first]
for p in D.glob('*.rct.png'):
 im=np.asarray(Image.open(p).convert('RGB'));h,w=im.shape[:2]
 if h<18 or w<51:continue
 seen+=1;ys,xs=np.nonzero(np.all(im==value,2))
 for y,x in zip(ys-first[0],xs-first[1]):
  if x<0 or y<0 or x+51>w or y+18>h:continue
  if any(not np.array_equal(im[y+dy,x+dx],lo[dy,dx]) for dy,dx in anchors[1:]):continue
  tile=im[y:y+18,x:x+51];diff=int(np.any(tile[known]!=lo[known],1).sum())
  if diff==0:result.append({'file':p.name,'x':int(x),'y':int(y),'known_pixels_exact':int(known.sum()),'same_existing_tile':any(np.array_equal(tile,z) for z in t)})
dump(R/'reports/console-exact-blank-donor-search.json',{'source_state':'console_off_m.rct','anchor_count':len(anchors),'known_mask_pixels':int(known.sum()),'files_searched':seen,'matches':result,'new_nonidentical_matches':sum(not r['same_existing_tile'] for r in result),'assets_modified':False});print(json.dumps({'files':seen,'matches':result},ensure_ascii=False))