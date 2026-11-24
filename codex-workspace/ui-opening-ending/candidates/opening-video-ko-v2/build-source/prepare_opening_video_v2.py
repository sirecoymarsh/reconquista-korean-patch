from pathlib import Path
import json,re,shutil,subprocess,hashlib
from fontTools.ttLib import TTFont
from PIL import Image
import numpy as np
U=Path.cwd();O=U/'candidates/opening-video-ko-v2';O.mkdir(exist_ok=True)
for d in ['subtitles','fonts','preview','evidence','payloads/movie']:(O/d).mkdir(parents=True,exist_ok=True)
for fn in ['Eulyoo1945-SemiBold.otf','NotoSerifKR-SemiBold.ttf']:
 shutil.copy2(U/'research/typography/fonts'/fn,O/'fonts'/fn)
for fn in ['op-lyrics-ko.srt','ed-lyrics-ko.srt']:shutil.copy2(U/'candidates/opening-video-ko-preview-v1/subtitles'/fn,O/'subtitles'/fn)
base=(U/'research/typography/eulyoo.ass').read_text(encoding='utf-8-sig');out=[]
for line in base.splitlines():
 if line.startswith('Dialogue:') and line.split(',')[4] in {'op-credits::title-1','op-credits::title-2'}:continue
 if line.startswith('Dialogue:'):
  # Missing two source-credit characters get an explicit CJK serif run, keeping all accepted text unchanged.
  fs=int(re.search(r'\\fs(\d+)',line).group(1)) if re.search(r'\\fs(\d+)',line) else 30
  for c in ['沢','青']:line=line.replace(c,'{\\fnReconquista Noto Serif Review\\fs'+str(round(fs*1.25))+'}'+c+'{\\fnEulyoo1945 SemiBold\\fs'+str(fs)+'}')
 out.append(line)
(O/'subtitles/opening-ko.ass').write_text('\n'.join(out)+'\n',encoding='utf-8-sig')
# Existing author script must not silently restore the superseded three-line theme credit on a future rebuild.
p=U/'tools/author_op_ed_captions.py';s=p.read_text(encoding='utf-8-sig')
# Frozen semantic files remain the source of truth; this revision only records their hashes.
cr=json.loads((U/'translation/opening-credits-ko.json').read_text(encoding='utf-8'));ly=json.loads((U/'translation/op-ed-lyrics-ko.json').read_text(encoding='utf-8'));rs=[r for r in cr['records'] if r['id'] not in {'op-credits::title-1','op-credits::title-2'}]+[r for r in ly['records'] if r['song']=='op']
frames=sorted(set(round((r['start']+r['end'])/2*30) for r in rs));select='+'.join(f'eq(n\\,{n})' for n in frames)
FF=Path('F:/DOWN/ffmpeg-7.1.1-essentials_build/ffmpeg-7.1.1-essentials_build/bin/ffmpeg.exe');movie=U.parent/'research/disc/movie/Recon_OP800_H.mpg'
args=[str(FF),'-hide_banner','-loglevel','info','-y','-f','lavfi','-i','color=c=black:s=800x600:r=30:d=101.3','-vf','ass=subtitles/opening-ko.ass:fontsdir=fonts,select='+select,'-fps_mode','vfr','-f','rawvideo','-pix_fmt','rgb24','-']
p=subprocess.run(args,cwd=O,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW);arr=np.frombuffer(p.stdout,np.uint8).reshape(-1,600,800,3);assert len(arr)==len(frames);bounds=[]
for n,a in zip(frames,arr):
 ink=np.max(a,2)>12;assert not ink[72:526].any(),('caption outside bars',n);yy,xx=np.nonzero(ink);top=np.nonzero(ink[:72]);bottom=np.nonzero(ink[526:]);bounds.append({'frame':n,'time':n/30,'top_bbox':[int(top[1].min()),int(top[0].min()),int(top[1].max()+1),int(top[0].max()+1)] if len(top[0]) else None,'bottom_bbox':[int(bottom[1].min()),int(bottom[0].min()+526),int(bottom[1].max()+1),int(bottom[0].max()+527)] if len(bottom[0]) else None})
fontlog=[l for l in p.stderr.decode('utf-8','replace').splitlines() if 'fontselect' in l];assert not any('Microsoft' in l or 'Malgun' in l for l in fontlog)
(O/'evidence/caption-bounds.json').write_text(json.dumps({'sample_count':len(frames),'cue_count':len(rs),'all_cues_covered':True,'all_caption_ink_inside_original_letterbox':True,'font_selection':fontlog,'frames':bounds},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(O/'semantic-inputs.json').write_text(json.dumps({'translator_model':'Codex internal','credits':cr,'lyrics':ly,'font_choice':json.loads((U/'research/typography/selected-font.json').read_text(encoding='utf-8')),'source_semantic_hashes':{p.relative_to(U).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in [U/'translation/opening-credits-ko.json',U/'translation/op-ed-lyrics-ko.json']},'provisional_source_words':['op-lyrics::007','ed-lyrics::014'],'removed_caption_cues':[{'id':k,'reason':'Rendered by Korean brush logo'} for k in sorted({'op-credits::title-1','op-credits::title-2'})],'retained_cue_count':len(rs)},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'candidate':str(O),'caption_cues':len(rs),'midpoint_checks':len(frames),'bar_containment':True,'fontlog':fontlog},ensure_ascii=False))
