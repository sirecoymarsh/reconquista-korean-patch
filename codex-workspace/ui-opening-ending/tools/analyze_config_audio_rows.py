from pathlib import Path
import numpy as np,json
from PIL import Image
U=Path.cwd();xy=[(225,287),(225,334),(225,381),(144,435),(144,483),(144,527),(498,436),(498,483),(498,526)];out=[];E=U/'evidence/config-audio-study'
for st in ['off','on','push']:
 a=np.asarray(Image.open(U/f'source/decoded/config_{st}.rct.png').convert('RGB'));rec={'state':st,'buttons':[]};strips=[]
 for x,y in xy:
  q=a[y-2:y+19,x+10:x+35];ref=np.repeat(q[:,:1],25,1);g=np.any(q!=ref,2);same=np.all(q[:,0]==q[:,-1],1);yy,xx=np.nonzero(g);rec['buttons'].append({'origin':[x,y],'reference_mismatch_rows':(np.flatnonzero(~same)-2).tolist(),'difference_rows':(np.flatnonzero(g.any(1))-2).tolist(),'diff_pixels':int(g.sum()),'perimeter':[int(g[0].sum()),int(g[-1].sum()),int(g[:,0].sum()),int(g[:,-1].sum())],'bbox':[int(xx.min()+10),int(yy.min()-2),int(xx.max()+11),int(yy.max()-1)]});r=a[y-3:y+20,x-2:x+46].copy();p=r.copy();area=p[1:22,12:37];area[g&same[:,None]]=ref[g&same[:,None]];strips.append(np.concatenate([r,p],1))
 Image.fromarray(np.concatenate(strips,0)).resize((576,1242),Image.Resampling.NEAREST).save(E/f'{st}-rows-clean-study.png');out.append(rec)
(U/'reports/config-audio-row-study.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(out,ensure_ascii=False))
