from pathlib import Path
import json,cv2,numpy as np,time
from PIL import Image
U=Path.cwd();D=U/'source/decoded';cv2.setNumThreads(2);assert not Path('C:/Users/CadriacLord/Documents/Codex/INCLUDED_USAGE_STOP.json').exists();a=np.asarray(Image.open(D/'config_off.rct.png').convert('RGB'));t=a[20:40,615:735];known=~(cv2.dilate(((t[:,:,1]>70)&(t[:,:,0]>110)).astype('uint8'),np.ones((5,5),np.uint8))>0);m=known.astype('float32');n=int(known.sum());tg=t[:,:,0].astype('float64');tz=(tg-tg[known].mean())*known;tn=np.linalg.norm(tz);res=[];start=time.time()
for dn in ['選択肢台','askyesno_base','レイアウトサンプル']:
 path=D/(dn+'.rct.png')
 if not path.exists():continue
 orig=np.asarray(Image.open(path).convert('RGB'))
 for scale in [.25,1/3,.5,2/3,.75,1,1.25,1.5,2]:
  b=cv2.resize(orig,None,fx=scale,fy=scale,interpolation=cv2.INTER_AREA if scale<1 else cv2.INTER_LINEAR) if scale!=1 else orig
  if b.shape[0]<20 or b.shape[1]<120:continue
  g=b[:,:,0].astype('float32');sums=cv2.matchTemplate(g,m,cv2.TM_CCORR).astype('float64');sq=cv2.matchTemplate(g*g,m,cv2.TM_CCORR).astype('float64');var=sq-sums*sums/n;num=cv2.matchTemplate(g,tz.astype('float32'),cv2.TM_CCORR).astype('float64');score=np.full(var.shape,-1.);valid=var>n*.25;score[valid]=num[valid]/np.sqrt(var[valid])/tn;ids=np.argpartition(score.ravel(),-8)[-8:]
  for ind in ids:
   yy,xx=np.unravel_index(ind,score.shape);q=b[yy:yy+20,xx:xx+120];v=q[:,:,0][known].astype('float64');v-=v.mean();corr=float(np.dot(v,tz[known])/(np.linalg.norm(v)*tn));X=np.column_stack([q[known],np.ones(n)]);coef=np.linalg.lstsq(X,t[known],rcond=None)[0];pred=np.dstack([q,np.ones(q.shape[:2])])@coef;diff=pred[known]-t[known];res.append({'donor':dn,'scale':scale,'xy':[int(xx),int(yy)],'ncc':corr,'affine_rgb_rmse':float(np.sqrt((diff**2).mean()))})
res.sort(key=lambda r:-r['ncc']);out={'target':'config_off.rct top return button','roi':[615,20,120,20],'known_pixels':n,'method':'Discovery-only stable masked red-channel NCC across coherent uniformly resized original donors; fixed mask and minimum variance. RGB affine residual reported, no reconstruction accepted.','tested_positions_peaks':len(res),'elapsed_seconds':round(time.time()-start,2),'top':res[:15],'accepted_donor':None,'asset_modified':False};(U/'reports/navigation-scale-study.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'elapsed':out['elapsed_seconds'],'top':res[:8]},ensure_ascii=False))
