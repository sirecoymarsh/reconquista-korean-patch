from pathlib import Path
import json,numpy as np
from PIL import Image
U=Path.cwd();E=U/'evidence/config-button-coherent-template';E.mkdir(exist_ok=True);xy=[(202,102),(288,102),(202,133),(522,102),(522,133),(609,133)];result=[];masks=[]
for state,threshold in [('off',41),('on',42),('push',36)]:
 a=np.asarray(Image.open(U/f'source/decoded/config_{state}.rct.png').convert('RGB'));tiles=np.stack([a[y+4:y+20,x+5:x+70] for x,y in xy]);v=tiles.astype('int32');glyph=(v[:,:,:,1]*100>v[:,:,:,0]*threshold);masks.append(glyph);bg=np.where(glyph[:,:,:,None],256,v);lo=bg.min(0);hi=np.where(glyph[:,:,:,None],-1,v).max(0);covered=(~glyph).sum(0);missing=covered==0;conflict=np.any(lo!=hi,2)&~missing;chosen=lo.clip(0,255).astype('uint8');row={'state':state,'template_region':[5,4,65,16],'unknown_pixels':int(missing.sum()),'different_background_values':int(conflict.sum()),'min_observations':int(covered.min()),'missing_xy':np.argwhere(missing)[:,::-1].tolist(),'conflict_xy':np.argwhere(conflict)[:,::-1].tolist(),'glyph_pixels':[int(x.sum()) for x in glyph],'glyph_edge_counts':[[int(x[0].sum()),int(x[-1].sum()),int(x[:,0].sum()),int(x[:,-1].sum())] for x in glyph]};result.append(row)
 sheet=[]
 for i,tile in enumerate(tiles):
  c=chosen.copy();c[missing]=[255,0,255];c[conflict]=[0,255,0];sheet.append(np.concatenate([tile,c],1))
 Image.fromarray(np.concatenate(sheet,0)).resize((650,480),Image.Resampling.NEAREST).save(E/f'{state}-source-template.png')
result.append({'cross_state_mask_differences':[int((masks[0]!=m).sum()) for m in masks[1:]]});(U/'reports/config-button-coherent-template.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,ensure_ascii=False))
