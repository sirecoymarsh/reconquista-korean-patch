from pathlib import Path
import sys,json,numpy as np
from PIL import Image,ImageDraw,ImageFont
sys.path.insert(0,'tools');from decode_ui import ROOT,decode,sha
from raster_codec import raw_image,encode_array
U=ROOT;O=U/'candidates/music-tracks-a-v1';mpath=O/'manifest.json';m=json.loads(mpath.read_bytes());assert m['structural_pass'] and not m['visual_pass'];tp=U/'translation/music-tracks-a-ko.json';t=json.loads(tp.read_bytes());old='부디 좋은 꿈을';new='꿈만은 좋기를';track=next(v for v in t['tracks'] if v['track_id']==12);assert track['target']==old;track['target']=new
builder=U/'tools/build_music_tracks_a.py';s=builder.read_text(encoding='utf-8-sig');assert s.count(old)==1;builder.write_text(s.replace(old,new),encoding='utf-8');fp=U.parent/'research/fonts/NotoSerifCJKkr-Regular.otf';f=ImageFont.truetype(str(fp),track['font_size']);x,y,w,h=track['crop'];b=f.getbbox(new,stroke_width=2);pos=(track['left']-b[0],round(y+21.5-(b[1]+b[3])/2));proof=[]
for state in ['off','on','push']:
 stem='サウンドモード_'+state;n=stem+'.rct';mn=stem+'_.rc8';final=np.array(Image.open(O/'preview'/f'{stem}.png'));before=final.copy();clean=np.array(Image.open(O/'clean'/f'{stem}.png'));final[y:y+h,x:x+w]=clean[y:y+h,x:x+w];fragment=Image.new('RGBA',(800,600));d=ImageDraw.Draw(fragment);fill,edge,glow={'off':((255,238,221,255),(58,36,25,230),(58,36,25,80)),'on':((232,193,148,255),(79,51,31,255),(244,165,54,220)),'push':((218,168,113,255),(137,93,46,255),(244,165,54,240))}[state];d.text(pos,new,font=f,fill=fill,stroke_width=2,stroke_fill=glow);d.text(pos,new,font=f,fill=fill,stroke_width=1,stroke_fill=edge);final=np.asarray(Image.alpha_composite(Image.fromarray(final),fragment));changed=np.any(before!=final,2);assert not changed[:y].any() and not changed[y+h:].any() and not changed[y:y+h,:x].any() and not changed[y:y+h,x+w:].any();ink=np.asarray(fragment)[:,:,3]>0;yy,xx=np.nonzero(ink);ib=[int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1];assert x<ib[0] and ib[2]<x+w and y<ib[1] and ib[3]<y+h
 layer=Image.open(O/'layers'/f'{stem}.png').convert('RGBA');layer.paste((0,0,0,0),(x,y,x+w,y+h));layer=Image.alpha_composite(layer,fragment);layer.save(O/'layers'/f'{stem}.png');owned=np.array(Image.open(O/'masks'/f'{stem}.owned.png'))>0;glyph=np.array(Image.open(O/'masks'/f'{state}-track-12.source-local.png'))>0;owned[y:y+h,x:x+w]=glyph|ink[y:y+h,x:x+w];Image.fromarray((owned*255).astype('uint8')).save(O/'masks'/f'{stem}.owned.png');_,rp,rc=raw_image((O/'payloads'/n).read_bytes());ob=encode_array(final[:,:,:3],rp,rc);(O/'payloads'/n).write_bytes(ob);q,_,_=raw_image(ob);assert np.array_equal(q,final[:,:,:3]);m['output_hashes'][n]=sha(ob);mi,ap,ac=raw_image((O/'payloads'/mn).read_bytes());pal=np.frombuffer(ap[20:788],np.uint8).reshape(256,3);lookup={int(v):i for i,v in enumerate(pal[:,0])};idx=np.array([lookup[int(v)] for v in (255-final[:,:,3]).ravel()],dtype='uint8').reshape(mi.shape);ob=encode_array(idx,ap,ac);(O/'payloads'/mn).write_bytes(ob);q,_,_=raw_image(ob);assert np.array_equal(255-pal[q,0],final[:,:,3]);m['output_hashes'][mn]=sha(ob);Image.fromarray(final).save(O/'preview'/f'{stem}.png')
 rec=next(e for e in m['entries'] if e['entry']==n);label=next(v for v in rec['strings'] if v['track_id']==12);label.update(target=new,target_ink_bounds=ib)
 for v in t['records']:
  if v['id']==label['id']:v.update(target=new,target_ink_bounds=ib)
 proof.append({'state':state,'only_changed_crop':track['crop'],'changed_pixel_count':int(changed.sum()),'target_ink_bounds':ib})
m['targeted_semantic_correction']={'track_id':12,'source':'せめて良い夢を','target':new,'reason':'Preserve せめて: wishing that at least dreams may be good. Prior unapproved wording omitted this nuance.','proof':proof,'other_17_tracks_reused':True};mpath.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');tp.write_text(json.dumps(t,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
# Refresh only preview composites whose changed pixels depend on track12.
finals={st:Image.open(O/'preview'/f'サウンドモード_{st}.png').convert('RGBA') for st in ['off','on','push']};bg=Image.fromarray(np.asarray(decode('サウンドモード_背景_off.rct')[0])).convert('RGBA');base=Image.alpha_composite(bg,finals['off']);base.convert('RGB').save(O/'preview/music-native-normal.png');sheet=Image.new('RGB',(2400,600));sheet.paste(base.convert('RGB'),(0,0));check=Image.new('RGB',(151*3,46*9))
for col,st in enumerate(['off','on','push']):
 comp=base.copy()
 if st!='off':
  for v in t['tracks']:
   xx,yy,ww,hh=v['crop'];comp.alpha_composite(finals[st].crop((xx,yy,xx+ww,yy+hh)),(xx,yy))
  comp.convert('RGB').save(O/'preview'/f'music-native-{st}.png');sheet.paste(comp.convert('RGB'),(col*800,0))
 check.paste(comp.crop((x,y,x+w,y+h)).resize((w*3,h*3),Image.Resampling.NEAREST).convert('RGB'),(0,col*h*3))
sheet.save(O/'preview/music-three-states.png');check.save(O/'preview/track12-corrected-three-states-3x.png')
# Prior source/clean/final sheets are superseded for track12; update only their final panels.
for st in ['off','on','push']:
 path=O/'preview'/f'{st}-source-clean-final-2x.png';im=Image.open(path).convert('RGBA');q=finals[st].crop((45,185,503,418)).resize((916,466),Image.Resampling.NEAREST);im.paste(q,(1832,0));im.save(path)
print(json.dumps({'changed_track':12,'target':new,'affected_states':3,'other_tracks_unchanged':17},ensure_ascii=False))
