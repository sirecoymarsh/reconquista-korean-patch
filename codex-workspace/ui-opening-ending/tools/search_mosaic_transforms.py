"""Research-only stable masked NCC over previously untested coherent transforms."""
from pathlib import Path
import sys,json,cv2,numpy as np,time
from PIL import Image
from decode_ui import ROOT,decode,sha
U=ROOT;marker=Path('C:/Users/CadriacLord/Documents/Codex/INCLUDED_USAGE_STOP.json');assert not marker.exists();cv2.setNumThreads(2)
name='名前プレート_まほこ.rct';x,y,w,h=12,8,107,27;src=np.asarray(decode(name)[0]);q=src[y:y+h,x:x+w];ink=cv2.dilate(np.all(q>70,2).astype('uint8'),np.ones((7,7),np.uint8)).astype(bool);known=~ink;mask=known.astype('float32');N=mask.sum();channel=int(np.argmax(q[known].std(0)));T=q[:,:,channel].astype('float32');mean=float(T[known].mean());C=(T-mean)*mask;energy=float(np.square(C).sum());assert N>100 and energy>100
choice=np.asarray(decode('選択肢台.rct')[0]);donors=[('choice-normal',[144,80,510,39],choice[80:119,144:654]),('choice-hover',[144,180,510,39],choice[180:219,144:654]),('choice-blue',[144,280,510,39],choice[280:319,144:654]),('gray-unknown-nameplate',[0,0,131,43],np.asarray(decode('名前プレート_？？？.rct')[0])),('verified-clean-config',[0,25,200,51],np.asarray(Image.open(U/'candidates/config-caption-raster-v1/clean/config_off.png').convert('RGB'))[25:76,:200])]
scales=[(1,1),(2,2),(3,3),(4,4),(.5,1),(1,.5),(.75,1),(1,.75),(1.25,1),(1,1.25),(1.5,1),(1,1.5),(1,2),(2,1),(1,3),(3,1),(1,4),(4,1)];results=[];trials=0;skipped=0;start=time.monotonic();stopped=False
for dn,rect,d0 in donors:
 for rot in [0,1,2,3]:
  for flip in [False,True]:
   oriented=np.rot90(d0,rot);oriented=oriented[:,::-1] if flip else oriented
   for sx,sy in scales:
    if marker.exists():stopped=True;break
    # Reuse previous unmirrored isotropic .5/1/2 studies rather than repeat them.
    if rot==0 and not flip and sx==sy and sx in [1,2]:skipped+=1;continue
    width=round(oriented.shape[1]*sx);height=round(oriented.shape[0]*sy)
    if width<w or height<h:continue
    d=cv2.resize(oriented,(width,height),interpolation=cv2.INTER_LINEAR) if (sx,sy)!=(1,1) else oriented;D=d[:,:,channel].astype('float32');s1=cv2.matchTemplate(D,mask,cv2.TM_CCORR);s2=cv2.matchTemplate(D*D,mask,cv2.TM_CCORR);cov=cv2.matchTemplate(D,C,cv2.TM_CCORR);variance=np.maximum(0,s2-s1*s1/N);valid=variance>N*4;corr=np.full(cov.shape,-2,dtype='float32');np.divide(cov,np.sqrt(variance*energy),out=corr,where=valid);corr[~np.isfinite(corr)]=-2;corr[(corr>1.00001)|(corr<-1.00001)]=-2;trials+=1
    for ix in np.argpartition(corr.ravel(),-min(8,corr.size))[-min(8,corr.size):]:
     py,px=np.unravel_index(ix,corr.shape);score=float(corr[py,px])
     if score<.55:continue
     patch=d[py:py+h,px:px+w]
     if np.any(np.all(patch>70,2)):continue
     yy,xx=np.indices((h,w));train=known&((xx+yy)%2==0);test=known&~train;prediction=np.zeros(q.shape,float);coeff=[]
     for c in range(3):
      X=np.stack([patch[:,:,c],np.ones((h,w))],2).astype(float);co=np.linalg.lstsq(X[train],q[:,:,c][train],rcond=None)[0];prediction[:,:,c]=X@co;coeff.append(co.tolist())
     delta=prediction[test]-q[test];results.append({'donor':dn,'original_donor_region':rect,'rotate90_steps':rot,'flip_horizontal_after_rotate':flip,'scale_xy':[sx,sy],'xy_in_transformed_donor':[int(px),int(py)],'stable_masked_ncc':score,'heldout_rgb_rmse':float(np.sqrt(np.square(delta).mean())),'heldout_max_abs':float(abs(delta).max()),'linear_color_coefficients':coeff})
   if stopped:break
  if stopped:break
 if stopped:break
 print(json.dumps({'donor_completed':dn,'trials':trials,'candidates':len(results),'elapsed_s':round(time.monotonic()-start,2)},ensure_ascii=False),flush=True)
results.sort(key=lambda r:-r['stable_masked_ncc']);report={'target':name,'roi':[x,y,w,h],'channel':channel,'known_pixels':int(N),'method':'Stable covariance/variance masked NCC, explicit variance floor, then held-out RGB affine fit. Previously tested identity isotropic1/2 skipped; new rotations/reflections/anisotropic scales and3/4 isotropic evaluated.','trials':trials,'reused_skipped_variants':skipped,'stopped_by_shared_marker':stopped,'top':results[:20],'asset_edits':0,'accepted_as_clean_plate':False,'elapsed_seconds':time.monotonic()-start};(U/'reports/mosaic-transform-search.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'trials':trials,'top':results[:3],'stopped':stopped},ensure_ascii=False))
