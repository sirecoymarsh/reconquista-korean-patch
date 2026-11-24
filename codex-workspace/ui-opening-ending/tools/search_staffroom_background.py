from pathlib import Path
import sys,json,hashlib,struct,numpy as np,cv2,time
from PIL import Image,ImageDraw,ImageFont
U=Path.cwd().resolve();assert not Path('C:/Users/CadriacLord/Documents/Codex/INCLUDED_USAGE_STOP.json').exists();sys.path.insert(0,str(U/'tools'));sys.path.insert(0,str(U.parent/'tools'));from inspect_majiro import Arc
from raster_codec import raw_image
cv2.setNumThreads(2);source=np.asarray(Image.open(U/'source/decoded/staffroom_off.rct.png').convert('RGB'));roi=[690,180,90,210];x,y,w,h=roi;target=cv2.cvtColor(source[y:y+h,x:x+w],cv2.COLOR_RGB2GRAY).astype(np.float32);target-=target.mean();den=np.sqrt((target*target).sum());rows=[];best=[];skipped=[];start=time.time()
for fn in ['data.arc','data1.arc','data2.arc']:
 p=U.parent/'research/disc'/fn;a=Arc(p);entries=[e for e in a.entries if e['name'].endswith('.rct') and (e['name'].lower().startswith('bg') or fn=='data2.arc')];print(fn,'candidate backgrounds',len(entries),flush=True)
 with p.open('rb') as f:
  for i,e in enumerate(entries):
   if i%20==0 and Path('C:/Users/CadriacLord/Documents/Codex/INCLUDED_USAGE_STOP.json').exists():raise SystemExit('Shared usage stop before next background block')
   f.seek(e['offset']);b=f.read(e['size']);width,height=struct.unpack_from('<II',b,8)
   if b[4:8]!=b'TC00' or width!=800 or height!=600:skipped.append({'archive':fn,'name':e['name'],'size':[width,height],'signature':b[4:8].decode(errors='replace')});continue
   arr,_,_=raw_image(b);gray=cv2.cvtColor(arr[y:y+h,x:x+w],cv2.COLOR_RGB2GRAY).astype(np.float32);g=gray-gray.mean();d=np.sqrt((g*g).sum())*den;score=float((g*target).sum()/d) if d>1 else -1;r={'archive':fn,'name':e['name'],'sha256':hashlib.sha256(b).hexdigest(),'same_position_gray_corr':score};rows.append(r)
   if len(best)<5 or score>best[-1][0]:
    best.append((score,r,arr.copy()));best.sort(key=lambda v:v[0],reverse=True);best=best[:5]
   if (i+1)%30==0:print('decoded',len(rows),'elapsed',round(time.time()-start,1),'best',round(best[0][0],4),flush=True)
E=U/'evidence/background-donor-search';E.mkdir(exist_ok=True);sheet=Image.new('RGB',(800,6*170),(25,27,30));font=ImageFont.truetype(str(U.parent/'research/fonts/NotoSansCJKkr-Regular.otf'),16);draw=ImageDraw.Draw(sheet);im=Image.fromarray(source);im.thumbnail((400,150));sheet.paste(im,(0,20));draw.text((405,45),'Staffroom source; unedited',font=font,fill='white')
for j,(score,r,arr) in enumerate(best,1):
 im=Image.fromarray(arr);im.thumbnail((400,150));sheet.paste(im,(0,j*170+20));draw.text((405,j*170+45),r['archive']+' / '+r['name']+'\ncorr='+str(round(score,6)),font=font,fill='white')
sheet.save(E/'staffroom-bg-candidates.png');out={'method':'Read-only native800x600 TC00 game-background scan; grayscale normalized correlation at one untextured staffroom patch. No resampling/rotation/delta reconstruction performed. Correlation is discovery only, never clean-plate proof.','source':'source/decoded/staffroom_off.rct.png','source_roi':roi,'decoded_count':len(rows),'skipped_count':len(skipped),'elapsed_seconds':time.time()-start,'top_candidates':sorted(rows,key=lambda r:r['same_position_gray_corr'],reverse=True)[:20],'skipped':skipped,'accepted_donor':None,'assets_modified':False,'preview':'evidence/background-donor-search/staffroom-bg-candidates.png'};(U/'reports/staffroom-background-search.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'decoded':len(rows),'skipped':len(skipped),'top':out['top_candidates'][:3],'accepted_donor':None},ensure_ascii=False))
