from pathlib import Path
import json,numpy as np
from PIL import Image
U=Path.cwd();D=U/'source/decoded';E=U/'evidence/config-button-study';E.mkdir(exist_ok=True);buttons=[(202,102),(288,102),(202,133),(288,133),(522,102),(522,133),(609,133)];out=[]
for st in ['off','on','push']:
 a=np.asarray(Image.open(D/('config_'+st+'.rct.png')).convert('RGB'));alpha=255-np.asarray(Image.open(D/('config_'+st+'_.rc8.png')).convert('L'));q=a[133:157,288:363].copy();r=q[6:20,16:59];bg=np.repeat(q[6:20,16:17],43,1);g=np.any(r!=bg,2);ys,xs=np.nonzero(g);same=np.array_equal(q[6:20,16],q[6:20,58]);record={'state':st,'reference_rows_match':same,'template_glyph_bbox':[int(xs.min())+16,int(ys.min())+6,int(xs.max())+17,int(ys.max())+7],'template_diff_pixels':int(g.sum()),'template_mask_touches_roi_edge':bool(g[0].any() or g[-1].any() or g[:,0].any() or g[:,-1].any()),'buttons':[]};q[6:20,16:59][g]=bg[g];Image.fromarray(q).save(E/(st+'-template.png'));strips=[]
 for x,y in buttons:
  s=a[y:y+24,x:x+75];diff=np.any(s[5:21,5:70]!=q[5:21,5:70],2);ys,xs=np.nonzero(diff);rec={'xy':[x,y],'difference_pixels':int(diff.sum()),'difference_bbox':[int(xs.min())+5,int(ys.min())+5,int(xs.max())+6,int(ys.max())+6],'perimeter_counts':[int(diff[0].sum()),int(diff[-1].sum()),int(diff[:,0].sum()),int(diff[:,-1].sum())],'alpha_unique':np.unique(alpha[y+5:y+21,x+5:x+70]).tolist()};record['buttons'].append(rec);strips.append(np.concatenate([s,q],1))
 Image.fromarray(np.concatenate(strips,0)).resize((750,840),Image.Resampling.NEAREST).save(E/(st+'-source-template-5x.png'));out.append(record)
(U/'reports/config-button-template-study.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(out,ensure_ascii=False))
