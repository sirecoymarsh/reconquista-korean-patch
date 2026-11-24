from pathlib import Path
import sys,json,cv2,numpy as np
sys.path.insert(0,str(Path(__file__).parent));from decode_ui import ROOT,decode
blank=np.asarray(decode('選択肢台.rct')[0]);result=[]
for state in ['off','on','push']:
 name='submenu_'+state+'.rct';a=np.asarray(decode(name)[0]);mask=np.asarray(decode('submenu_'+state+'_.rc8')[0].convert('RGB')).astype('uint16');alpha=255-mask.sum(2)//3;active=(alpha[:,550:725]>128).sum(1)>120;edges=np.diff(np.r_[False,active,False].astype('int8'));starts=np.flatnonzero(edges==1);ends=np.flatnonzero(edges==-1);assert len(starts)==len(ends)==8,(starts,ends)
 for row,(Y0,Y1) in enumerate(zip(starts,ends)):
  x=550;y=int(Y0+5);w=175;h=int(Y1-Y0-9);q=a[y:y+h,x:x+w];core=cv2.dilate(np.all(q>70,axis=2).astype('uint8'),np.ones((7,7),np.uint8)).astype(bool);known=~core;score=cv2.matchTemplate(blank.astype('float32'),q.astype('float32'),cv2.TM_SQDIFF,mask=np.repeat(known[:,:,None],3,axis=2).astype('float32'));candidates=[]
  for idx in np.argpartition(score.ravel(),99)[:100]:
   yy,xx=np.unravel_index(idx,score.shape);p=blank[yy:yy+h,xx:xx+w]
   if np.any(np.all(p>70,axis=2)):continue
   v=(p.astype('int32')-q.astype('int32'))[known];candidates.append({'xy':[int(xx),int(yy)],'mse':float((v**2).mean()),'different_known_pixels':int(np.any(v!=0,axis=1).sum())})
  candidates.sort(key=lambda c:c['mse']);result.append({'entry':name,'row':row,'button_y':[int(Y0),int(Y1)],'region':[x,y,w,h],'known_pixels':int(known.sum()),'best':candidates[0] if candidates else None})
(ROOT/'reports/submenu-donor-study.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,ensure_ascii=False))
