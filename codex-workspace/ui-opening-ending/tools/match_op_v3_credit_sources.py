from pathlib import Path
import sys,json,re,cv2,numpy as np
from PIL import Image
U=Path.cwd();R=U/'research/op-all-japanese-v3';sys.path.insert(0,str(U/'tools'));from op_v3_source_art import SourceArt
cv2.setNumThreads(2);S=SourceArt();si=cv2.SIFT_create(nfeatures=1600,contrastThreshold=.014);bf=cv2.BFMatcher();targets=[1680,2010,2058,2076,2124,2142,2196,2250,2370,2430];T={}
for n in targets:
 a=np.array(Image.open(R/'dense-frames'/f'{n:04d}.png'));kp,ds=si.detectAndCompute(cv2.cvtColor(a,cv2.COLOR_RGB2GRAY),None);T[n]=(kp,ds)
choices={1680:['bg_010_04.rct','last1.rct'],2010:['bg_340a.rct','bg_341a.rct'],2058:['bg_260c.rct','bg_260a.rct'],2076:['last1.rct','last2.rct','last3.rct'],2124:[n for n in S.idx if re.match('bg[_.].*rct$',n)],2142:['last1.rct','last2.rct','last3.rct'],2196:[n for n in S.idx if n.startswith(('ev301','ev_309','ev_303','ev_312')) and n.endswith('.rct')],2250:[n for n in S.idx if re.match(r'(b_)?yue_.*\.rct$',n) and n.endswith('_01.rct')],2370:[n for n in S.idx if n.startswith('ev301') and n.endswith('.rct')],2430:[n for n in S.idx if n.startswith('ev106') and n.endswith('.rct')]}
rows={};cache={}
for n,names in choices.items():
 out=[];kt,dt=T[n]
 for name in names:
  if name not in S.idx:continue
  if name not in cache:
   a=S.decode(name);sz=min(1,800/max(a.shape[:2]));sm=cv2.resize(a,None,fx=sz,fy=sz);kp,ds=si.detectAndCompute(cv2.cvtColor(sm,cv2.COLOR_RGB2GRAY),None);cache[name]=(kp,ds,sz);S.cache.clear()
  kp,ds,sz=cache[name]
  if ds is None:continue
  g=[a for a,b in bf.knnMatch(ds,dt,k=2) if a.distance<.76*b.distance]
  if len(g)<5:continue
  H,inl=cv2.estimateAffinePartial2D(np.float32([kp[q.queryIdx].pt for q in g])/sz,np.float32([kt[q.trainIdx].pt for q in g]),method=cv2.RANSAC,ransacReprojThreshold=2.5)
  if H is None:continue
  out.append({'name':name,'inliers':int(inl.sum()),'matrix':H.tolist()})
 out.sort(key=lambda x:x['inliers'],reverse=True);rows[n]=out[:5];print(n,out[:2],flush=True)
 for rr in out[:1]:Image.fromarray(S.decode(rr['name'])).save(R/'extra-source-art'/(rr['name']+'.png'))
 S.cache.clear()
(R/'source-matching.json').write_text(json.dumps(rows,indent=2))