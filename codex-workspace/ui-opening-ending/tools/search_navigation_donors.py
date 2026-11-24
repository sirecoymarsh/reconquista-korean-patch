from pathlib import Path
import json,numpy as np,cv2
from PIL import Image
U=Path.cwd();D=U/'source/decoded';assert not Path('C:/Users/CadriacLord/Documents/Codex/INCLUDED_USAGE_STOP.json').exists();cv2.setNumThreads(2);out=[];E=U/'evidence/navigation-donor-study';E.mkdir(exist_ok=True)
for stem,roi in [('config_off',[615,20,120,20]),('config_on',[615,20,120,20]),('config_push',[615,20,120,20])]:
 a=np.asarray(Image.open(D/(stem+'.rct.png')).convert('RGB'));x,y,w,h=roi;t=a[y:y+h,x:x+w];glyph=(t[:,:,1]>70)&(t[:,:,0]>110);glyph=cv2.dilate(glyph.astype('uint8'),np.ones((5,5),np.uint8))>0;known=(~glyph).astype('uint8');cands=[]
 for donor in ['選択肢台','askyesno_base','subtitle']:
  path=D/(donor+'.rct.png')
  if not path.exists():continue
  b=np.asarray(Image.open(path).convert('RGB'));score=cv2.matchTemplate(b.astype('float32'),t.astype('float32'),cv2.TM_SQDIFF,mask=known);_,_,loc,_=cv2.minMaxLoc(score);xx,yy=loc;q=b[yy:yy+h,xx:xx+w];diff=np.any(q!=t,2)&(known>0);mse=float(np.mean((q[known>0].astype('float64')-t[known>0])**2));cands.append({'donor':donor,'position':[xx,yy],'known_pixels':int(known.sum()),'different_known_pixels':int(diff.sum()),'mse':mse});Image.fromarray(np.concatenate([t,q],1)).resize((960,80),Image.Resampling.NEAREST).save(E/(stem+'-'+donor+'-source-donor-4x.png'))
 out.append({'entry':stem,'roi':roi,'known_mask':'Exclude source bright glyphs with2px expansion; discovery only','results':cands})
(U/'reports/navigation-donor-study.json').write_text(json.dumps({'entries':out,'accepted_donor':None,'asset_modified':False},ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(out,ensure_ascii=False))
