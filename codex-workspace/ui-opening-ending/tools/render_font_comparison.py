from pathlib import Path
import json,re,subprocess,shutil
from PIL import Image,ImageDraw,ImageFont
from fontTools.ttLib import TTFont
U=Path.cwd();R=U/'research/typography';O=R/'preview';O.mkdir(exist_ok=True)
FF=Path('F:/DOWN/ffmpeg-7.1.1-essentials_build/ffmpeg-7.1.1-essentials_build/bin/ffmpeg.exe');movie=U.parent/'research/disc/movie/Recon_OP800_H.mpg'
base=(U/'candidates/opening-video-ko-preview-v1/subtitles/opening-ko.ass').read_text(encoding='utf-8-sig')
cr=json.loads((U/'translation/opening-credits-ko.json').read_text(encoding='utf-8'));ly=json.loads((U/'translation/op-ed-lyrics-ko.json').read_text(encoding='utf-8'));texts=''.join(r['target'] for r in cr['records']+ly['records'])
options=[('eulyoo','Eulyoo1945 SemiBold','Eulyoo1945-SemiBold.otf',30,1.25),('maru','MaruBuri SemiBold','MaruBuri-SemiBold.ttf',30,1.25),('noto','Reconquista Noto Serif Review','NotoSerifKR-SemiBold.ttf',34,1.45)]
report=[]
for key,family,fn,lyricfs,scale in options:
 ass=base.replace('Noto Sans CJK KR',family)
 ass=ass.replace('Style: Lyric,'+family+',26,','Style: Lyric,'+family+f',{lyricfs},')
 ass=ass.replace(',1,1.5,0,2,20,20,24,1',',1,0.8,0.4,2,24,24,21,1')
 ass=ass.replace(',1,1,0,8,20,20,6,1',',1,0.6,0.3,8,22,22,7,1')
 ass=re.sub(r'\\fs(\d+)',lambda m:'\\fs'+str(round(int(m[1])*scale)),ass)
 (R/f'{key}.ass').write_text(ass,encoding='utf-8-sig')
 cm=TTFont(R/'fonts'/fn).getBestCmap();missing=sorted(set(c for c in texts if c not in '\n\r' and ord(c) not in cm));logs=[]
 for t in [10.0,56.5]:
  args=[str(FF),'-hide_banner','-loglevel','info','-y','-i',str(movie),'-vf',f'ass={key}.ass:fontsdir=fonts,select=gte(t\\,{t})','-frames:v','1',str(O/f'{key}-{t:05.1f}.png')]
  p=subprocess.run(args,cwd=R,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW);logs.extend(l for l in p.stderr.decode('utf-8','replace').splitlines() if 'fontselect' in l)
 report.append({'key':key,'family':family,'file':str(R/'fonts'/fn),'lyric_nominal_fs':lyricfs,'credit_scale':scale,'missing_codepoints':missing,'fontselect':sorted(set(logs))})
sheet=Image.new('RGB',(800,3*200),(15,15,18));d=ImageDraw.Draw(sheet);labelf=ImageFont.truetype(str(U.parent/'research/fonts/NotoSansCJKkr-Regular.otf'),18)
for i,(key,label) in enumerate([('eulyoo','을유1945 SemiBold'),('maru','마루 부리 SemiBold'),('noto','본명조 SemiBold')]):
 im=Image.open(O/f'{key}-010.0.png');y=i*200;d.text((20,y+5),label,font=labelf,fill=(210,154,166));sheet.paste(im.crop((0,0,800,72)),(0,y+35));sheet.paste(im.crop((0,526,800,600)),(0,y+111))
sheet.save(O/'font-comparison.png');(R/'font-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,ensure_ascii=False))
