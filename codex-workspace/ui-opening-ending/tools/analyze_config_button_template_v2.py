from pathlib import Path
import json,numpy as np
from PIL import Image
U=Path.cwd();E=U/'evidence/config-button-template-v2';E.mkdir(exist_ok=True);xy=[(202,102),(288,102),(202,133),(522,102),(522,133),(609,133)];arrays={s:np.asarray(Image.open(U/f'source/decoded/config_{s}.rct.png').convert('RGB')) for s in ['off','on','push']};tiles={s:np.stack([a[y:y+24,x:x+75] for x,y in xy]) for s,a in arrays.items()};v=tiles['off'].astype('int32');glyph=(v[:,:,:,1]*100>v[:,:,:,0]*41);scope=np.zeros((24,75),bool);scope[4:20,3:72]=True;glyph &= scope
core=np.zeros((24,75),bool);core[7:17,11:65]=True;base_glyph=glyph[5].copy();base_scope=np.zeros((24,75),bool);base_scope[4:20,14:66]=True;base_glyph &= base_scope;out=[];sheets=[]
for s,t in tiles.items():
 if s != 'push': continue
 bg=np.where(glyph[:,:,:,None],256,t.astype('int32'));lo=bg.min(0);hi=np.where(glyph[:,:,:,None],-1,t.astype('int32')).max(0);count=(~glyph).sum(0);unknown=count==0;conflicts=np.any(lo!=hi,2)&~unknown;assert not np.any(unknown&base_glyph&~core);assert not np.any(conflicts&base_glyph)
 row_plateaus=[];fill=np.zeros_like(t[5])
 for yy in range(7,17):
  vals,counts=np.unique(lo[yy,11:65][count[yy,11:65]>0],axis=0,return_counts=True);base=vals[counts.argmax()];xs=np.flatnonzero(np.all(lo[yy]==base,1));left,right=int(xs.min()),int(xs.max());known=lo[yy,left:right+1][count[yy,left:right+1]>0];assert np.all(known==base);needed=np.flatnonzero((base_glyph&unknown)[yy]);assert all(left<=xx<=right for xx in needed);fill[yy,left:right+1]=base;row_plateaus.append({'y':yy,'x_bounds_inclusive':[left,right],'rgb':base.tolist(),'known_locations':int(len(known)),'filled_locations':needed.tolist()})
 clean=t[5].copy();clean[base_glyph&~unknown]=lo[base_glyph&~unknown].astype('uint8');clean[base_glyph&unknown]=fill[base_glyph&unknown];Image.fromarray(clean).save(E/f'{s}-canonical-clean.png');rec={'state':s,'row_plateaus':row_plateaus,'core_observed_pixels':int((~glyph[:,core]).sum()),'core_covered_locations':int((count[core]>0).sum()),'core_total_locations':int(core.sum()),'base_glyph_pixels':int(base_glyph.sum()),'base_missing_filled_from_proven_uniform_core':int((base_glyph&unknown).sum()),'base_glyph_perimeter':[int(base_glyph[4].sum()),int(base_glyph[19].sum()),int(base_glyph[:,14].sum()),int(base_glyph[:,65].sum())],'buttons':[]}
 rowimages=[]
 for i,(x,y) in enumerate(xy):
  d=np.any(t[i]!=clean,2)&scope;ys,xs=np.nonzero(d);delta=t[i].astype('int32')-clean.astype('int32');neg=np.any(delta<0,2)&d;rec['buttons'].append({'xy':[x,y],'diff_pixels':int(d.sum()),'bbox':[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)],'negative_rgb_pixels':int(neg.sum()),'perimeter':[int(d[4].sum()),int(d[19].sum()),int(d[:,3].sum()),int(d[:,71].sum())]});q=clean.copy();q[d&neg]=[0,255,0];rowimages.append(np.concatenate([t[i],q],1))
 Image.fromarray(np.concatenate(rowimages,0)).resize((750,720),Image.Resampling.NEAREST).save(E/f'{s}-comparison.png');out.append(rec)
(U/'reports/config-button-template-v2-push.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(out,ensure_ascii=False))
