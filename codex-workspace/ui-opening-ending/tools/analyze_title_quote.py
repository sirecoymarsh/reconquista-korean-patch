from pathlib import Path
import json,numpy as np
from PIL import Image,ImageFont
U=Path.cwd();D=U/'source/decoded';E=U/'evidence/title-quote-study';E.mkdir(exist_ok=True);out=[];masks=[]
for v,(x,y,base) in enumerate([(98,337,'title1_null2'),(98,337,'title2_null2'),(430,255,'title1_null2')],1):
 a=np.asarray(Image.open(D/f'title{v}_off.rct.png').convert('RGB'));b=np.asarray(Image.open(D/f'{base}.rct.png').convert('RGB'));q=a[y:y+33,x:x+179];blank=b[y:y+33,x:x+179];m=np.any(q!=blank,2);yy,xx=np.nonzero(m);rec={'variant':v,'rect':[x,y,179,33],'diff_pixels':int(m.sum()),'bbox':[int(xx.min()+x),int(yy.min()+y),int(xx.max()+x+1),int(yy.max()+y+1)],'perimeter':[int(m[0].sum()),int(m[-1].sum()),int(m[:,0].sum()),int(m[:,-1].sum())],'rows_with_difference':np.flatnonzero(m.any(1)).tolist(),'red_logo_pixels':int(((q[:,:,0]>120)&(q[:,:,0]>q[:,:,2].astype('uint16')*1.5)&m).sum())};out.append(rec);masks.append(m);Image.fromarray(np.concatenate([q,blank],1)).resize((1074,99),Image.Resampling.NEAREST).save(E/f'v{v}-source-background-3x.png')
text=['죽음과 무덤도 불못에 던져졌다.','이 불못이 곧 둘째 죽음이다.','생명책에 이름이 기록되지 않은 사람은','누구든 불못에 던져졌다.']
for size in [9,10]:
 f=ImageFont.truetype(str(U.parent/'research/fonts/NotoSansCJKkr-Regular.otf'),size);print('font',size,[f.getbbox(x) for x in text])
out.append({'variant_mask_differences_relative_to_first':[int((masks[0]!=m).sum()) for m in masks[1:]]});(U/'reports/title-quote-background-study.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(out,ensure_ascii=False))
