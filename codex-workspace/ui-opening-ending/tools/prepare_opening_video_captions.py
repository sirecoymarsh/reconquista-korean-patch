from pathlib import Path
import json,shutil,subprocess
from PIL import ImageFont
from fontTools.ttLib import TTFont
U=Path.cwd();P=U/'translation/opening-credits-ko.json';cr=json.loads(P.read_text(encoding='utf-8'))
for r in cr['records']:
 if r['id']=='op-credits::theme-song':r['target']='주제가 「Reconquista」  |  노래: 飛蘭 · 작사: 海富一\n작곡: 上松範康 · 편곡: 菊田大介 · 기타: 加納望 · 바이올린: 森琢哉';r['font_size']=18
P.write_text(json.dumps(cr,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
O=U/'candidates/opening-video-ko-preview-v1';assert not O.exists()
for d in ['subtitles','fonts','preview','payloads/movie','evidence']:(O/d).mkdir(parents=True,exist_ok=True)
font=U.parent/'research/fonts/NotoSansCJKkr-Regular.otf';shutil.copy2(font,O/'fonts'/font.name);ly=json.loads((U/'translation/op-ed-lyrics-ko.json').read_text(encoding='utf-8'));cm=TTFont(font).getBestCmap();timings=[]
def srtstamp(t):
 n=round(t*1000);return f'{n//3600000:02d}:{n//60000%60:02d}:{n//1000%60:02d},{n%1000:03d}'
def assstamp(t):
 n=round(t*100);return f'{n//360000:01d}:{n//6000%60:02d}:{n//100%60:02d}.{n%100:02d}'
for song in ['op','ed']:
 rs=[r for r in ly['records'] if r['song']==song];assert all(a['end']<=b['start'] for a,b in zip(rs,rs[1:]));(O/'subtitles'/f'{song}-lyrics-ko.srt').write_text('\n\n'.join(f'{i+1}\n{srtstamp(r["start"])} --> {srtstamp(r["end"])}\n{r["target"]}' for i,r in enumerate(rs))+'\n',encoding='utf-8')
ass='''[Script Info]
Title: Reconquista Korean captions - Codex internal review candidate
ScriptType: v4.00+
PlayResX: 800
PlayResY: 600
WrapStyle: 2
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.601

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Credit,Noto Sans CJK KR,20,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,1,0,8,20,20,6,1
Style: Lyric,Noto Sans CJK KR,26,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,1.5,0,2,20,20,24,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
for r in cr['records']+[r for r in ly['records'] if r['song']=='op']:
 style='Credit' if r['id'].startswith('op-credits') else 'Lyric';fs=r.get('font_size',26);f=ImageFont.truetype(str(font),fs);assert all(ord(ch) in cm for ch in r['target'] if ch!='\n');lengths=[f.getlength(line) for line in r['target'].split('\n')];assert max(lengths)<=760,(r['id'],lengths);txt=r['target'].replace('\n',r'\N');txt=(f'{{\\fs{fs}}}' if style=='Credit' else '')+txt;ass+=f'Dialogue: 0,{assstamp(r["start"])},{assstamp(r["end"])},{style},{r["id"]},0,0,0,,{txt}\n';timings.append({'id':r['id'],'style':style,'start':r['start'],'end':r['end'],'font_size':fs,'pillow_line_widths':lengths,'midpoint':round((r['start']+r['end'])/2,3)})
(O/'subtitles/opening-ko.ass').write_text(ass,encoding='utf-8-sig');(O/'semantic-inputs.json').write_text(json.dumps({'translator_model':'Codex internal','credits':cr,'lyrics':ly,'cue_geometry':timings,'localization_mode':'Additive upper-letterbox credits and lower-letterbox lyrics; original in-picture typography/logos kept.'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
FF=Path(r'F:\DOWN\ffmpeg-7.1.1-essentials_build\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe');movie=U.parent/'research/disc/movie/Recon_OP800_H.mpg';results=[]
for t in [10.0,22.0,35.0,50.0,56.5,72.0,80.5]:
 args=[str(FF),'-hide_banner','-loglevel','info','-i',str(movie),'-vf',f'ass=subtitles/opening-ko.ass:fontsdir=fonts,select=gte(t\\,{t})','-frames:v','1',str(O/'preview'/f'layout-{t:05.1f}.png')];p=subprocess.run(args,cwd=O,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW);results.append({'time':t,'font_select':[x for x in p.stderr.decode('utf-8','replace').splitlines() if 'fontselect' in x]})
(O/'evidence/font-layout-probe.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'candidate':str(O),'cues':len(timings),'font_probe':results[0],'lyrics_provisional':['op-lyrics::007','ed-lyrics::014']},ensure_ascii=False))
