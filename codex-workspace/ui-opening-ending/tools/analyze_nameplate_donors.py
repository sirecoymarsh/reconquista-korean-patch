from pathlib import Path
import sys,json,cv2,numpy as np
sys.path.insert(0,str(Path(__file__).parent));from decode_ui import ROOT,SRC,decode,sha
names=[p.name for p in SRC.glob('名前プレート_*.rct') if '？？？' not in p.name];data={n:np.asarray(decode(n)[0]) for n in names};masks={}
for n,a in data.items():
 mask=np.zeros(a.shape[:2],np.uint8);mask[6:37,8:123]=np.all(a[6:37,8:123]>70,axis=2);masks[n]=cv2.dilate(mask,np.ones((7,7),np.uint8)).astype(bool)
results=[]
for name in names:
 a=data[name];mask=masks[name];inner=np.zeros((43,131),bool);inner[7:36,10:121]=True;known=inner&~mask;best=[];fills={};conflict=0
 for donor in names:
  if donor==name:continue
  b=data[donor];bm=masks[donor];choice=None
  for dy in range(-5,6):
   for dx in range(-8,9):
    x=max(10,-dx);X=min(121,131-dx);y=max(7,-dy);Y=min(36,43-dy);valid=known[y:Y,x:X]&~bm[y+dy:Y+dy,x+dx:X+dx];count=int(valid.sum())
    if count<700:continue
    eq=np.all(a[y:Y,x:X]==b[y+dy:Y+dy,x+dx:X+dx],axis=2);score=float(eq[valid].mean())
    if choice is None or (score,count)>(choice['score'],choice['known_pixels']):choice={'donor':donor,'dx':dx,'dy':dy,'score':score,'known_pixels':count}
  if choice:best.append(choice)
  if choice and choice['score']==1:
   dx=choice['dx'];dy=choice['dy']
   for yy,xx in zip(*np.nonzero(mask&inner)):
    sy=yy+dy;sx=xx+dx
    if 0<=sy<43 and 0<=sx<131 and not bm[sy,sx]:
     key=(int(yy),int(xx));v=tuple(map(int,b[sy,sx]));conflict+=int(key in fills and fills[key]!=v);fills[key]=v
 results.append({'entry':name,'mask_pixels':int((mask&inner).sum()),'exact_restorable_pixels':len(fills),'remaining_mask_pixels':int((mask&inner).sum())-len(fills),'conflicts':conflict,'matches':sorted(best,key=lambda x:(x['score'],x['known_pixels']),reverse=True)[:5]})
(ROOT/'reports/nameplate-alignment-study.json').write_text(json.dumps({'method':'Pairwise integer shifts, masks from bright core + 7x7 dilation; exact RGB known-pixel agreement only','results':results},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps([{'entry':r['entry'],'remaining':r['remaining_mask_pixels'],'conflicts':r['conflicts'],'best':r['matches'][0] if r['matches'] else None} for r in results],ensure_ascii=False))
