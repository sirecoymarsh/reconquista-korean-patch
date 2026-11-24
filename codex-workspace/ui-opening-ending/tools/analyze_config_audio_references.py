from pathlib import Path
import numpy as np,json
from PIL import Image
U=Path.cwd();xy=[(225,287),(225,334),(225,381),(144,435),(144,483),(144,527),(498,436),(498,483),(498,526)];out=[]
for st in ['off','on','push']:
 a=np.asarray(Image.open(U/f'source/decoded/config_{st}.rct.png').convert('RGB'));rec={'state':st,'buttons':[]}
 for x,y in xy:
  good=[]
  for left in range(8,13):
   for right in range(31,37):
    roi=a[y+1:y+15,x+left:x+right+1];ref=np.repeat(roi[:,:1],right-left+1,axis=1);g=np.any(roi!=ref,2)
    if np.array_equal(roi[:,0],roi[:,-1]) and not g[0].any() and not g[-1].any():
     yy,xx=np.nonzero(g);good.append({'bounds':[left,1,right-left+1,14],'glyph_pixels':int(g.sum()),'bbox':[int(xx.min()+left),int(yy.min()+1),int(xx.max()+left+1),int(yy.max()+2)]})
  rec['buttons'].append({'origin':[x,y],'candidates':good})
 out.append(rec)
(U/'reports/config-audio-blank-references.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(out,ensure_ascii=False))
