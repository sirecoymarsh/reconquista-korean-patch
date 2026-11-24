from pathlib import Path
from PIL import Image
import numpy as np,json
U=Path.cwd();out=U/'research/op-ed';ev=U/'evidence/op-ed-source';ps=sorted((U/'source/decoded').glob('staffrollb_*.rct.png'));a=np.stack([np.asarray(Image.open(p)) for p in ps]);cc=np.stack([np.all(a==a[i],3).sum(0) for i in range(len(a))]);ix=cc.argmax(0);base=np.take_along_axis(a,ix[None,:,:,None],axis=0)[0];equal=np.all(a==base,3);counts=equal.sum(0);nonnegative=np.all(a.astype('int16')-base.astype('int16')>=0,3);Image.fromarray(base).save(ev/'staffrollb-majority-clean-study.png');assert np.array_equal(np.asarray(Image.open(ev/'staffrollb-majority-clean-study.png')),base)
rows=[]
for i,p in enumerate(ps):
 diff=~equal[i];yy,xx=np.nonzero(diff);ys=np.where(diff.any(1))[0];groups=[]
 for y in ys:
  if not groups or y>groups[-1][-1]+1:groups.append([int(y)])
  else:groups[-1].append(int(y))
 rows.append({'file':p.name,'diff_pixels':int(diff.sum()),'bbox':[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)],'min_blank_donor_count_in_diff':int(counts[diff].min()),'horizontal_bands':[[g[0],g[-1]+1,int(np.where(diff[g[0]:g[-1]+1].any(0))[0].min()),int(np.where(diff[g[0]:g[-1]+1].any(0))[0].max()+1)] for g in groups]})
Image.fromarray((counts*23).astype('uint8')).save(ev/'staffrollb-observed-majority-donor-count.png');r={'method':'Most frequent exact whole RGB triplet among11 originals at identical coordinates. No synthesized colors. Candidate blank needs visual review and majority gate before use.','pixel_donor_count_distribution':{str(v):int((counts==v).sum()) for v in np.unique(counts)},'negative_delta_pixels':[int((~nonnegative[i]).sum()) for i in range(len(a))],'assets':rows};(out/'staffrollb-majority-plate-study.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
a=np.asarray(Image.open(U/'source/decoded/staffrolla.rct.png'));mask=np.asarray(Image.open(U/'source/decoded/staffrolla_.rc8.png').convert('L'));points=[[0,0],[190,142],[200,155],[409,155],[200,200],[409,191],[799,4663]]
print(json.dumps({'b_donors':r['pixel_donor_count_distribution'],'b_rows':rows,'a_points':[{'xy':[x,y],'rgb':a[y,x].tolist(),'alpha':int(255-mask[y,x])} for x,y in points]},ensure_ascii=False))
