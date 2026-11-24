from pathlib import Path
import json,numpy as np
from PIL import Image,ImageFilter
U=Path.cwd();xy=[(202,102),(288,102),(202,133),(522,102),(522,133),(609,133)];out=[];masks=[]
for s in ['off','on','push']:
 a=np.asarray(Image.open(U/f'source/decoded/config_{s}.rct.png').convert('RGB'));t=np.asarray(Image.open(U/f'evidence/config-button-template-v2/{s}-canonical-clean.png'));ms=[];rec={'state':s,'buttons':[]}
 for x,y in xy:
  p=a[y:y+24,x:x+75];delta=p.astype('int16')-t.astype('int16');scope=np.zeros((24,75),bool);scope[4:20,3:72]=True;g=(delta[:,:,1]>4)&scope;d=np.any(delta,2)&scope;res=d&~g;ring=np.asarray(Image.fromarray((g*255).astype('uint8')).filter(ImageFilter.MaxFilter(3)))>0;yy,xx=np.nonzero(g);rec['buttons'].append({'xy':[x,y],'glyph_pixels':int(g.sum()),'bbox':[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)],'min_g_delta':int(delta[:,:,1][g].min()),'residual_pixels':int(res.sum()),'residual_max_channel_diff':int(abs(delta[res]).max(initial=0)),'residual_in_glyph_neighborhood':int((res&ring).sum()),'residual_coords':np.argwhere(res)[:,::-1].tolist()});ms.append(g)
 masks.append(np.stack(ms));q=a[133:157,288:363];roi=q[4:20,16:60];ref=np.repeat(q[4:20,16:17],44,1);g=np.any(roi!=ref,2);yy,xx=np.nonzero(g);rec['all_button']={'row_refs_match':bool(np.array_equal(q[4:20,16],q[4:20,59])),'glyph_pixels':int(g.sum()),'bbox':[int(xx.min()+16),int(yy.min()+4),int(xx.max()+17),int(yy.max()+5)],'perimeter':[int(g[0].sum()),int(g[-1].sum()),int(g[:,0].sum()),int(g[:,-1].sum())]};out.append(rec)
out.append({'glyph_support_cross_state_diff':[int((masks[0]!=x).sum()) for x in masks[1:]]});(U/'reports/config-button-exact-glyph-audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(out,ensure_ascii=False))
