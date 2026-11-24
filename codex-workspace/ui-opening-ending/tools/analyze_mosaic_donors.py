from pathlib import Path
import sys,json,cv2,numpy as np,time
sys.path.insert(0,str(Path(__file__).parent));from decode_ui import ROOT,decode
specs=[('config_off.rct',[64,33,104,39]),('submenu_off.rct',[578,33,118,43]),('cgm_off.rct',[61,35,107,35]),('名前プレート_まほこ.rct',[12,8,107,27])]
donornames=['選択肢台.rct','askyesno_base.rct','console_off_m.rct','名前プレート_？？？.rct','レイアウトサンプル.rct','config_off.rct','cgm_off.rct','sl_save_n.rct','サウンドモード_背景_off.rct','クロニクル枠_null.rct'];donors={n:np.asarray(decode(n)[0]) for n in donornames};results=[]
for name,(x,y,w,h) in specs:
 src=np.asarray(decode(name)[0]);q=src[y:y+h,x:x+w];ink=cv2.dilate(np.all(q>70,axis=2).astype('uint8'),np.ones((7,7),np.uint8)).astype(bool);known=~ink;mask=np.repeat(known[:,:,None],3,axis=2).astype('float32');items=[]
 for dn,d in donors.items():
  if d.shape[0]<h or d.shape[1]<w:continue
  score=cv2.matchTemplate(d.astype('float32'),q.astype('float32'),cv2.TM_SQDIFF,mask=mask);score=np.nan_to_num(score,nan=1e30,posinf=1e30,neginf=1e30)
  for idx in np.argpartition(score.ravel(),min(99,score.size-1))[:min(100,score.size)]:
   yy,xx=np.unravel_index(idx,score.shape);patch=d[yy:yy+h,xx:xx+w]
   if dn!='名前プレート_？？？.rct' and np.any(np.all(patch>70,axis=2)):continue
   delta=(patch.astype('int32')-q.astype('int32'))[known];mse=float((delta**2).mean());items.append({'donor':dn,'xy':[int(xx),int(yy)],'mse':mse,'known_pixels':int(known.sum()),'different_known_pixels':int(np.any(delta!=0,axis=1).sum())})
 results.append({'entry':name,'region':[x,y,w,h],'source_mask_pixels':int(ink.sum()),'best_blank_donors':sorted(items,key=lambda r:r['mse'])[:5]})
(ROOT/'reports/mosaic-blank-donor-study.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(results,ensure_ascii=False))
