from pathlib import Path
import numpy as np,json
from PIL import Image
U=Path.cwd();rects=[(220,282,56,27),(220,329,56,27),(220,376,56,27),(142,430,49,27),(142,478,49,27),(142,523,49,27),(496,432,49,27),(496,478,49,27),(496,522,49,27)];out=[]
for st in ['off','on','push']:
 a=np.asarray(Image.open(U/f'source/decoded/config_{st}.rct.png').convert('RGB'));template=a[287:304,225:269];matches=[]
 for x,y,w,h in rects:
  choices=[]
  for dy in range(h-16):
   for dx in range(w-43):
    q=a[y+dy:y+dy+17,x+dx:x+dx+44];delta=q[1:16,5:39].astype('int16')-template[1:16,5:39].astype('int16');choices.append((int(np.square(delta.astype('int32')).sum()),int(np.any(delta,2).sum()),x+dx,y+dy))
  choices.sort();matches.append(choices[0])
 rows=[]
 for yy in range(17):
  q=template[yy,10:33];same=np.array_equal(template[yy,10],template[yy,32]);diff=np.any(q!=q[0],1);rows.append({'y':yy,'refs_match':bool(same),'left':q[0].tolist(),'right':q[-1].tolist(),'diff_x':(np.flatnonzero(diff)+10).tolist()})
 rec={'state':st,'aligned_buttons':matches,'rows':rows};out.append(rec)
(U/'reports/config-audio-plate-study.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(out,ensure_ascii=False))
