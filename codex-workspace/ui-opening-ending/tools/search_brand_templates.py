"""Read-only logo template discovery with a stable local-variance denominator."""
from pathlib import Path
import json,time,cv2,numpy as np
from PIL import Image,ImageDraw,ImageFont
U=Path.cwd().resolve(); D=U/'source/decoded'; cv2.setNumThreads(2)
def effective(path):
 a=np.asarray(Image.open(path).convert('RGB'),dtype='float64');mp=path.with_name(path.name.replace('.rct.png','_.rc8.png'))
 if mp.exists():a*=((255-np.asarray(Image.open(mp).convert('L'),dtype='float64'))/255)[:,:,None]
 return a
def high(a):
 gray=cv2.cvtColor(a.astype('float32'),cv2.COLOR_RGB2GRAY).astype('float64')
 return gray-cv2.GaussianBlur(gray,(0,0),5)
src=np.asarray(Image.open(D/'バックログ画面.rct.png').convert('RGB'));ys,xs=np.nonzero(src[460:500,35:520].max(2)>0)
roi=[35+int(xs.min()),460+int(ys.min()),int(xs.max()-xs.min()+1),int(ys.max()-ys.min()+1)]
x,y,w,h=roi;t=high(effective(D/'バックログ画面.rct.png'))[y:y+h,x:x+w];t-=t.mean();tn=np.linalg.norm(t);n=w*h
assert tn>100
results=[];start=time.time()
for i,path in enumerate(sorted(D.glob('*.rct.png'))):
 if i%30==0 and Path('C:/Users/CadriacLord/Documents/Codex/INCLUDED_USAGE_STOP.json').exists():raise SystemExit('Shared usage stop')
 a=effective(path)
 if a.shape[0]<h or a.shape[1]<w:continue
 v=high(a);integ,integ2=cv2.integral2(v,sdepth=cv2.CV_64F,sqdepth=cv2.CV_64F)
 def window(ii):return ii[h:,w:]-ii[:-h,w:]-ii[h:,:-w]+ii[:-h,:-w]
 sums=window(integ);var=window(integ2)-sums*sums/n
 numerator=cv2.matchTemplate(v.astype('float32'),t.astype('float32'),cv2.TM_CCORR).astype('float64')
 score=np.full(var.shape,-1.,dtype='float64'); valid=var>=n*0.25
 score[valid]=numerator[valid]/(np.sqrt(var[valid])*tn)
 yy,xx=np.unravel_index(score.argmax(),score.shape);patch=v[yy:yy+h,xx:xx+w];pn=patch-patch.mean()
 exact=float(np.sum(pn*t)/(np.linalg.norm(pn)*tn)) if np.linalg.norm(pn)>0 else -1.
 results.append({'file':path.name,'score':exact,'position':[int(xx),int(yy)],'patch_std':float(patch.std()),'image_size':[a.shape[1],a.shape[0]],'valid_positions':int(valid.sum())})
results.sort(key=lambda r:r['score'],reverse=True)
out={'source_roi':roi,'method':'Discovery-only effective RGBA-on-black high-pass logo NCC. Float64 local variance with minimum std0.5; final candidate NCC recomputed directly in float64. Previous cv2 TM_CCOEFF_NORMED output was invalid in near-zero-variance windows and is superseded. No donor accepted by this search.','checked':len(results),'elapsed_seconds':round(time.time()-start,2),'candidates':results[:30],'accepted_donor':None}
(U/'reports/brand-template-inventory.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
E=U/'evidence/background-donor-search';E.mkdir(exist_ok=True);sheet=Image.new('RGB',(900,12*80),(25,27,30));d=ImageDraw.Draw(sheet);font=ImageFont.truetype(str(U.parent/'research/fonts/NotoSansCJKkr-Regular.otf'),16)
for i,r in enumerate(results[:12]):
 a=effective(D/r['file']).clip(0,255).astype('uint8');xx,yy=r['position'];im=Image.fromarray(a[yy:yy+h,xx:xx+w]);sheet.paste(im,(5,i*80+30));d.text((5,i*80+2),r['file']+' '+str(round(r['score'],5))+' '+str(r['position']),font=font,fill='white')
sheet.save(E/'brand-template-candidates.png');print(json.dumps({'checked':len(results),'top':results[:12]},ensure_ascii=False))
