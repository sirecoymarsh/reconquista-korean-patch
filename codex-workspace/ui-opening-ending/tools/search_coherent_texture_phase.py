"""Search single coherent blank texture patches; research only, never changes assets."""
from pathlib import Path
import cv2,numpy as np,json
from PIL import Image
U=Path(__file__).resolve().parents[1];D=U/'source/decoded';cv2.setNumThreads(2)
names=['選択肢台','askyesno_base','クロニクル枠_null','レイアウトサンプル','config_off','cgm_off','sl_save_n','サウンドモード_背景_off','submenu_off','console_off_m','console_off_h','console_off_s','console_off_e','console_off_t','console_off_k','kaisou_off','staffroom_off','バックログ画面','名前プレート_？？？','extra_off','extra2_off']
assets={n:np.asarray(Image.open(D/(n+'.rct.png')).convert('RGB')) for n in names};reports=[]
for name,roi in [('config_off',[102,99,100,29]),('名前プレート_まほこ',[12,8,107,27])]:
 arr=np.asarray(Image.open(D/(name+'.rct.png')).convert('RGB'));x,y,w,h=roi;q=arr[y:y+h,x:x+w];ink=cv2.dilate(np.all(q>70,2).astype('uint8'),np.ones((7,7),np.uint8)).astype(bool);known=~ink;mask=known.astype('float32');scores_out=[]
 # Raw-channel correlation retains low-contrast texture phase; Sobel previously hid it below glyph shadows.
 channel=int(np.argmax([q[:,:,c][known].std() for c in range(3)]));template=q[:,:,channel].astype('float32')
 for dn,d0 in assets.items():
  for scale in [.5,1,2]:
   d=cv2.resize(d0,None,fx=scale,fy=scale,interpolation=cv2.INTER_LINEAR) if scale!=1 else d0
   if d.shape[0]<h or d.shape[1]<w:continue
   corr=cv2.matchTemplate(d[:,:,channel].astype('float32'),template,cv2.TM_CCOEFF_NORMED,mask=mask);corr=np.nan_to_num(corr,nan=-2,posinf=-2,neginf=-2);best=min(100,corr.size);ids=np.argpartition(corr.ravel(),-best)[-best:]
   for ix in ids:
    py,px=np.unravel_index(ix,corr.shape);score=float(corr[py,px])
    if score<.7:continue
    patch=d[py:py+h,px:px+w]
    if np.any(np.all(patch>70,2)):continue
    yy,xx=np.indices((h,w));train=known&((xx+yy)%2==0);test=known&~train;pred=np.zeros_like(q,dtype='float64');coeff=[]
    for c in range(3):
     X=np.stack([patch[:,:,c],np.ones((h,w))],2).astype('float64');co=np.linalg.lstsq(X[train],q[:,:,c][train],rcond=None)[0];pred[:,:,c]=X@co;coeff.append(co.tolist())
    diff=pred[test]-q[test];scores_out.append({'donor':dn+'.rct','scale':scale,'xy':[int(px),int(py)],'masked_correlation':score,'heldout_rgb_rmse':float(np.sqrt(np.square(diff).mean())),'heldout_max_abs':float(np.abs(diff).max()),'coefficients':coeff})
 scores_out.sort(key=lambda r:(-r['masked_correlation'],r['heldout_rgb_rmse']));report={'target':name+'.rct','roi':roi,'channel':channel,'known_pixels':int(known.sum()),'source_background_std':q[known].std(0).tolist(),'top':scores_out[:12],'accepted_as_clean_plate':False};reports.append(report);print(json.dumps(report,ensure_ascii=False),flush=True)
(U/'reports/coherent-texture-phase-search.json').write_text(json.dumps({'research_only':True,'asset_edits':0,'targets':reports},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
