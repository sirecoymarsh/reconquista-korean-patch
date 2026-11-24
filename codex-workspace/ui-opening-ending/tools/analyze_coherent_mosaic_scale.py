"""Research only: search coherent texture phase with scale and continuous color gradient."""
from pathlib import Path
import sys,json,cv2,numpy as np
from PIL import Image
from decode_ui import ROOT,decode
cv2.setNumThreads(2)
names=['選択肢台.rct','askyesno_base.rct','console_off_m.rct','名前プレート_？？？.rct','レイアウトサンプル.rct','config_off.rct','cgm_off.rct','sl_save_n.rct','サウンドモード_背景_off.rct','クロニクル枠_null.rct'];donors={n:np.asarray(decode(n)[0]) for n in names};out=[]
for name,(x,y,w,h) in [('config_off.rct',[102,99,100,29]),('名前プレート_まほこ.rct',[12,8,107,27])]:
 source=np.asarray(decode(name)[0]);q=source[y:y+h,x:x+w];ink=cv2.dilate(np.all(q>70,axis=2).astype('uint8'),np.ones((7,7),np.uint8)).astype(bool);known=~ink;mask=known.astype('float32');qg=cv2.Sobel(q[:,:,1].astype('float32'),cv2.CV_32F,1,0,ksize=3);results=[]
 yy,xx=np.indices((h,w));phase=((xx+yy)%2)==0;train=known&phase;test=known&~phase;Y=(yy/max(h-1,1)).astype('float64')
 for dn,d0 in donors.items():
  for scale in [.5,.75,1.0,1.25,1.5,2.0]:
   d=cv2.resize(d0,None,fx=scale,fy=scale,interpolation=cv2.INTER_LINEAR) if scale!=1 else d0
   if d.shape[0]<h or d.shape[1]<w:continue
   dg=cv2.Sobel(d[:,:,1].astype('float32'),cv2.CV_32F,1,0,ksize=3);scores=cv2.matchTemplate(dg,qg,cv2.TM_CCORR_NORMED,mask=mask);scores=np.nan_to_num(scores,nan=-1,posinf=-1,neginf=-1)
   top=min(24,scores.size);ids=np.argpartition(scores.ravel(),-top)[-top:]
   for idx in ids:
    py,px=np.unravel_index(idx,scores.shape);patch=d[py:py+h,px:px+w]
    if np.any(np.all(patch>70,axis=2)):continue
    fits=[];pred=np.zeros_like(q,dtype='float64')
    for c in range(3):
     D=patch[:,:,c].astype('float64');X=np.stack([D,D*Y,np.ones((h,w)),Y],axis=2);coef=np.linalg.lstsq(X[train],q[:,:,c][train],rcond=None)[0];pred[:,:,c]=X@coef;fits.append(coef.tolist())
    diff=pred[test]-q[test];results.append({'donor':dn,'scale':scale,'xy':[int(px),int(py)],'gradient_correlation':float(scores[py,px]),'heldout_rgb_rmse':float(np.sqrt((diff*diff).mean())),'heldout_max_abs':float(np.abs(diff).max()),'color_coefficients':fits})
 results.sort(key=lambda r:(r['heldout_rgb_rmse'],-r['gradient_correlation']));r={'target':name,'region':[x,y,w,h],'known_pixels':int(known.sum()),'top':results[:8],'accepted_as_clean_plate':False};out.append(r);print(json.dumps({'target':name,'top':r['top'][:3]},ensure_ascii=False))
(ROOT/'reports/coherent-mosaic-scale-study.json').write_text(json.dumps({'research_only':True,'method':'Single coherent donor, subregion scale, horizontal texture-gradient correlation, continuous y-affine color model trained and checked on disjoint known pixels; alpha and glyph-cleanliness not yet validated','targets':out},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
