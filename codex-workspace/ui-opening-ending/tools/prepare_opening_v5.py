from pathlib import Path
import json,shutil,datetime,subprocess
from PIL import Image,ImageDraw
U=Path.cwd();V=U/'candidates/opening-video-ko-v4';O=U/'candidates/opening-video-ko-v5'
assert not (O/'manifest.json').exists()
for x in ['build-source','evidence','preview','subtitles','fonts','payloads/movie','viewing']:(O/x).mkdir(parents=True,exist_ok=True)
for p in (V/'fonts').iterdir():
 if not (O/'fonts'/p.name).exists():shutil.copy2(p,O/'fonts'/p.name)
for name in ['opening-ko.ass','opening-ko-4k.ass']:
 s=(V/'subtitles'/name).read_text(encoding='utf-8');s='\n'.join(x for x in s.splitlines() if not (x.startswith('Dialogue:') and ',Credit,' in x))+'\n'
 s=s.replace('그림자마저 얼어붙는 어둠 속','그림자마저 얼어붙어 in darkness');assert s.count('Dialogue:')==32 and s.count('in darkness')==2
 (O/'subtitles'/name).write_text(s,encoding='utf-8')
for name in ['lyrics-bilingual.json','opening-credits-ko.json','name-readings.json']:
 j=json.loads((V/name).read_text(encoding='utf-8'))
 if name=='lyrics-bilingual.json':
  for r in j['records']:
   if r['id']=='op-lyrics::004':r['previous_target']=r['target'];r['target']='그림자마저 얼어붙어 in darkness';r['revision_reason']='User: retain deliberate foreign language in original lyrics';r['preserved_foreign_span']='in darkness'
  j['layout']='Japanese above Korean; intentional foreign language preserved in both lines'
 if name=='opening-credits-ko.json':
  for r in j['records']:
   if 'title-quote' in r['id']:r['presentation']='Small paragraph below Roman brand; A+B together; no upper caption'
 (O/name).write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
policy={'translator_model':'Codex internal','task_id':'01a162df-720c-77d2-96ed-6429e90b3333','prior_frozen_candidate':'opening-video-ko-v4','requests':['Remove four upper logo quote cues; replace small English paragraph in place in both logo scenes','Retain deliberate foreign-language lyric spans, including source spelling in darkness','Keep translated small English text compact and sharp; independently render at 4K'],'unchanged':'Prior staff/role translation; 16 lyric pairs; original audio','quote_lines':['죽음과 무덤도 불못에 던져졌다.','이 불못이 곧 둘째 죽음이다.','생명책에 이름이 기록되지 않은 사람은','누구든 불못에 던져졌다.'],'runtime':'File-only background; no playback or focus takeover'}
(O/'revision-policy.json').write_text(json.dumps(policy,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
p=U/'progress.json';j=json.loads(p.read_text(encoding='utf-8'));j['usage_checkpoint']={'remaining_percent':99,'limit_id':'codex','stop_marker_present':False,'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()};j['active_user_revision']['op_quote_foreign_v5']={'state':'in progress','candidate':'candidates/opening-video-ko-v5','requests':policy['requests'],'next':'Prepare quote clean plates, render both versions, verify changed scenes','resumed_by':'Direct user: 재개'};p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
ns=[630,636,642,648,654,660,672,720,750,780,810,850,890,897,900,903,906,909,912,915,918,2760,2772,2784,2796,2808,2820,2850,2940,2960,2980,2990,3000]
dest=O/'build-source/quote-probes';dest.mkdir(exist_ok=True);expr='+'.join('eq(n,%d)'%n for n in ns);ff='F:/DOWN/ffmpeg-7.1.1-essentials_build/ffmpeg-7.1.1-essentials_build/bin/ffmpeg.exe';args=[ff,'-v','error','-y','-threads','3','-i',str(U/'candidates/opening-video-ko-v3/build-source/opening-clean-background.ffv1.mkv'),'-vf',"select='"+expr+"'",'-fps_mode','vfr','-start_number','0',str(dest/'%03d.png')];subprocess.run(args,check=True,creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS)
rows=[];im=Image.new('RGB',(1200,170*9),(20,20,20));d=ImageDraw.Draw(im)
for i,n in enumerate(ns):
 a=Image.open(dest/f'{i:03d}.png').convert('RGB');a.save(dest/f'n{n:04d}.png');x=i%4*300;y=i//4*170;im.paste(a.crop((240,365,450,435)).resize((294,98)),(x,y+28));d.text((x+4,y+4),f'n{n}  {n/30:.2f}s',fill='white');rows.append({'frame':n,'path':str(dest/f'n{n:04d}.png')})
im.save(O/'preview/quote-source-timeline.png');(O/'evidence/quote-probe-frames.json').write_text(json.dumps(rows,indent=2)+'\n');print('v5 prepared; quote timeline extracted')
