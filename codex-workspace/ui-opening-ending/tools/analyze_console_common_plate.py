from pathlib import Path
import numpy as np,cv2,json
from PIL import Image
U=Path.cwd();D=U/'source/decoded';out=[];positions=[300,350,400,450,501,551,601,651]
for st in ['off','on','push']:
 a=np.asarray(Image.open(D/f'console_{st}_m.rct.png').convert('RGB'));ts=np.stack([a[565:583,x:x+51] for x in positions]);v=ts.astype('int16');base=(v[:,:,:,1]>100)&((v[:,:,:,0]-v[:,:,:,2])<60);records=[]
 for dilation in [0,1,2]:
  g=np.stack([cv2.dilate(m.astype('uint8'),np.ones((dilation*2+1,)*2,np.uint8))>0 for m in base]);bg=np.where(g[:,:,:,None],256,v);lo=bg.min(0);hi=np.where(g[:,:,:,None],-1,v).max(0);count=(~g).sum(0);scope=np.zeros((18,51),bool);scope[4:14,4:47]=True;conflict=np.any(lo!=hi,2)&(count>0)&scope;missing=(count==0)&scope;records.append({'dilation_radius':dilation,'known_conflicts':int(conflict.sum()),'missing_pixels':int(missing.sum()),'total_scope':int(scope.sum()),'source_glyph_pixels':[int((m&scope).sum()) for m in g]})
 out.append({'state':st,'result':records})
(U/'reports/console-common-plate-study.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(out,ensure_ascii=False))
