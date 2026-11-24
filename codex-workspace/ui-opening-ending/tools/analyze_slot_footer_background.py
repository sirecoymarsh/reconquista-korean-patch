from pathlib import Path
import json,numpy as np
from PIL import Image
U=Path.cwd();D=U/'source/decoded';out=[]
for st in ['sl_save_n','sl_save_f','sl_load_n','sl_load_f']:
 rgb=np.asarray(Image.open(D/(st+'.rct.png')).convert('RGB'));alpha=255-np.asarray(Image.open(D/(st+'_.rc8.png')).convert('L'));a=np.dstack([rgb,alpha]);rec=[]
 for row,y0 in enumerate([87,249,411]):
  for col,x0 in enumerate([40,281,523]):
   x,y,w,h=x0+10,y0+124,218,32;q=a[y:y+h,x:x+w];mode=[]
   for line in q:
    vals,cnt=np.unique(line,axis=0,return_counts=True);mode.append(vals[cnt.argmax()])
   mode=np.array(mode);equal=np.all(q==mode[:,None],2);refs=np.flatnonzero(np.all(equal,0));mask=~equal;ys,xs=np.nonzero(mask);rec.append({'slot':row*3+col+1,'roi':[x,y,w,h],'reference_columns':(refs+x).tolist(),'diff_bbox':[int(xs.min()+x),int(ys.min()+y),int(xs.max()+x)+1,int(ys.max()+y)+1],'difference_pixels':int(mask.sum()),'perimeter_counts':[int(mask[0].sum()),int(mask[-1].sum()),int(mask[:,0].sum()),int(mask[:,-1].sum())],'background_rgba_rows':mode.tolist(),'min_background_pixel_count_per_row':int(equal.sum(1).min())})
 out.append({'entry':st,'slots':rec})
(U/'reports/slot-footer-background-study.json').write_text(json.dumps({'method':'Exploratory row modes and exact full-height blank reference columns. Not yet an accepted edit.','entries':out},ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps([{'entry':v['entry'],'slots':[{'slot':r['slot'],'refs':r['reference_columns'],'bbox':r['diff_bbox'],'perimeter':r['perimeter_counts']} for r in v['slots']]} for v in out],ensure_ascii=False))
