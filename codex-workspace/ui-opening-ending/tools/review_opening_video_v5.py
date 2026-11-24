"""Review only changed v5 scenes and their immediate joins; reuse v4 coverage elsewhere."""
from pathlib import Path
import json,sys,subprocess
from PIL import Image,ImageDraw
U=Path.cwd();O=U/'candidates/opening-video-ko-v5';four='--4k' in sys.argv
ns=[549,550,603,606,636,638,642,660,690,720,750,780,810,850,890,897,903,909,915,920,921,969,970,1046,1047,1080,1125,1159,1160,1209,1210,2699,2700,2744,2745,2760,2772,2796,2850,2920,2960,2980,2998,3000]
dest=O/'preview'/('encoded4k' if four else 'encoded');dest.mkdir(exist_ok=True)
video=O/('viewing/Reconquista_OP_KO_4K.mp4' if four else 'payloads/movie/Recon_OP800_H.mpg')
ff='F:/DOWN/ffmpeg-7.1.1-essentials_build/ffmpeg-7.1.1-essentials_build/bin/ffmpeg.exe';expr='+'.join(f'eq(n,{n})' for n in ns)
p=subprocess.run([ff,'-v','error','-xerror','-threads','4','-i',str(video),'-vf',"select='"+expr+"'",'-fps_mode','vfr','-start_number','0',str(dest/'%03d.png')],stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS)
assert p.returncode==0,p.stderr.decode(errors='replace')
rows=[]
for i,n in enumerate(ns):
 path=dest/f'{i:03d}.png';assert path.exists();rows.append(dict(index=i,frame=n,time=n/30,path=str(path)))
for lo in range(0,len(rows),12):
 sub=rows[lo:lo+12];h=225 if four else 300;im=Image.new('RGB',(1600,(h+24)*((len(sub)+3)//4)),(22,22,22));d=ImageDraw.Draw(im)
 for i,r in enumerate(sub):
  a=Image.open(r['path']).convert('RGB');assert a.size==((3840,2160) if four else (800,600));x=i%4*400;y=i//4*(h+24);im.paste(a.resize((400,h)),(x,y+24));d.text((x+3,y+3),f"n{r['frame']} | {r['time']:.2f}s",fill='white')
 im.save(dest/f'contact-{lo//12+1}.jpg',quality=94)
selected=[690,810,897,909,2850,2920,2980];crop=Image.new('RGB',(1200,200*len(selected)),(22,22,22));d=ImageDraw.Draw(crop)
for i,n in enumerate(selected):
 r=next(x for x in rows if x['frame']==n);a=Image.open(r['path'])
 box=(round(235*4.8),round((367-75)*4.8),round(450*4.8),round((440-75)*4.8)) if four else (235,367,450,440)
 part=a.crop(box);part.thumbnail((1120,170));crop.paste(part,(70,i*200+24));d.text((6,i*200+6),f'n{n}',fill='white')
crop.save(dest/'quote-details.png')
report={'status':'visual_review_pending','video':str(video),'frames':rows,'scope':'Changed quote scenes, foreign lyric span, and GOP/cue joins only','reused_evidence':'opening-video-ko-v4/evidence/final-visual-review.json','audio_playback':False}
(O/'evidence'/('4k-encoded-review.json' if four else 'encoded-review.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('4K' if four else 'native','encoded samples',len(rows),flush=True)
