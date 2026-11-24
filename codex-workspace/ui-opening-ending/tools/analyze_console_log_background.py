from pathlib import Path
import numpy as np,json
from PIL import Image
U=Path.cwd();D=U/'source/decoded';out=[]
for st in ['off','on','push']:
 a=np.asarray(Image.open(D/f'console_{st}_m.rct.png').convert('RGB'));q=a[565:583,601:652];good=[]
 for left in range(7,17):
  for right in range(34,44):
   for top in [2,3,4]:
    for bottom in [13,14,15,16]:
     r=q[top:bottom+1,left:right+1];bg=np.repeat(r[:,:1],right-left+1,1);g=np.any(r!=bg,2)
     if g.any() and np.array_equal(r[:,0],r[:,-1]) and not g[0].any() and not g[-1].any():
      yy,xx=np.nonzero(g);good.append({'roi':[left,top,right-left+1,bottom-top+1],'glyphs':int(g.sum()),'bbox':[int(xx.min()+left),int(yy.min()+top),int(xx.max()+left+1),int(yy.max()+top+1)]})
 out.append({'state':st,'valid_reference_regions':good[:12],'valid_regions_total':len(good)})
(U/'reports/console-log-background-study.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(out,ensure_ascii=False))
