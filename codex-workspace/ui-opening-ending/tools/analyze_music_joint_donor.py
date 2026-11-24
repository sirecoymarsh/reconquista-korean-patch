from pathlib import Path
import sys,json,collections,numpy as np,cv2
from PIL import Image
U=Path.cwd().resolve(); D=U/'source/decoded'
def rgba(stem):
 a=np.asarray(Image.open(D/(stem+'.rct.png')).convert('RGB'));m=D/(stem+'_.rc8.png');alpha=255-np.asarray(Image.open(m).convert('L')) if m.exists() else np.full(a.shape[:2],255,dtype='uint8');return np.dstack([a,alpha])
s=rgba('バックログ画面');c=rgba('chapter_off_1');t=rgba('サウンドモード_off');covered=((rgba('サウンドモード_on')[:,:,3]>0)|(rgba('サウンドモード_push')[:,:,3]>0)).astype('uint8');excluded=cv2.dilate(covered,np.ones((5,5),np.uint8))>0
results=[]
for label,roi,shift in [('logo',[35,460,485,40],[43,-436]),('quote',[35,500,485,68],[46,0])]:
 x,y,w,h=roi;dx,dy=shift;a=s[y:y+h,x:x+w];b=c[y+dy:y+dy+h,x+dx:x+dx+w];target=t[y-19:y-19+h,x+17:x+17+w];known=~excluded[y-19:y-19+h,x+17:x+17+w]
 modes={}
 for name,src in [('history',a),('chapter',b),('joint',np.concatenate([a,b],2))]:
  lut=collections.defaultdict(collections.Counter)
  for av,bv in zip(src[known],target[known]):lut[tuple(map(int,av))][tuple(map(int,bv))]+=1
  ambig={k:v for k,v in lut.items() if len(v)>1};missing={tuple(map(int,p)) for p in src.reshape(-1,src.shape[2])}-set(lut)
  modes[name]={'codes':len(lut),'ambiguous_codes':len(ambig),'minority_pixels':sum(sum(v.values())-max(v.values()) for v in ambig.values()),'missing_codes':list(missing)[:20],'missing_code_count':len(missing),'ambiguous_examples':[{'source':k,'targets':v.most_common(6)} for k,v in list(ambig.items())[:4]]}
 results.append({'part':label,'history_roi':roi,'chapter_shift':shift,'binary_support_diff':int(np.count_nonzero(np.any(a[:,:,:3]>0,2)!=np.any(b[:,:,:3]>0,2))),'modes':modes,'source_rgba_peaks':{'history':a.reshape(-1,4).max(0).tolist(),'chapter':b.reshape(-1,4).max(0).tolist()}})
out={'method':'Read-only exact-code analysis using original history and chapter templates at aligned logo/quote positions. Source song ink/glow excluded by original on/push alpha dilated2. No output assets authored.','parts':results,'accepted':all(not r['binary_support_diff'] and not r['modes']['joint']['ambiguous_codes'] and not r['modes']['joint']['missing_code_count'] for r in results)}
(U/'reports/music-joint-donor-calibration.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(out,ensure_ascii=False))
