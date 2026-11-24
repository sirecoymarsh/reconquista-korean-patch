from pathlib import Path
import json,re,hashlib,subprocess,numpy as np
U=Path.cwd();O=U/'candidates/opening-video-ko-v2';title_ids={'op-credits::title-1','op-credits::title-2'}
p=U/'translation/opening-credits-ko.json';cr=json.loads(p.read_text(encoding='utf-8'));old=json.loads((U/'candidates/opening-video-ko-preview-v1/semantic-inputs.json').read_text(encoding='utf-8'));lookup={r['id']:r for r in old['credits']['records']};quotes=[]
for r in cr['records']:
 if r['id'] in title_ids:r['target']='레콘키스타'
 elif r['id'].startswith('op-credits::title-quote-'):r['target']=lookup[r['id']]['target'];quotes.append(r)
assert len(quotes)==4
p.write_text(json.dumps(cr,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
p=U/'tools/prepare_opening_video_v2.py';s=p.read_text(encoding='utf-8-sig');s=s.replace("if ',op-credits::title-' in line:continue", "if line.startswith('Dialogue:') and line.split(',')[4] in {'op-credits::title-1','op-credits::title-2'}:continue")
s=s.replace("rs=cr['records']+[r for r in ly['records'] if r['song']=='op']","rs=[r for r in cr['records'] if r['id'] not in {'op-credits::title-1','op-credits::title-2'}]+[r for r in ly['records'] if r['song']=='op']")
s=s.replace("'provisional_source_words':['op-lyrics::007','ed-lyrics::014']", "'provisional_source_words':['op-lyrics::007','ed-lyrics::014'],'removed_caption_cues':[{'id':k,'reason':'Rendered by Korean brush logo'} for k in sorted({'op-credits::title-1','op-credits::title-2'})],'retained_cue_count':len(rs)")
p.write_text(s,encoding='utf-8');base=(U/'research/typography/eulyoo.ass').read_text(encoding='utf-8-sig');out=[]
for line in base.splitlines():
 if line.startswith('Dialogue:'):
  if line.split(',')[4] in title_ids:continue
  fs=int(re.search(r'\\fs(\d+)',line).group(1)) if re.search(r'\\fs(\d+)',line) else 30
  for ch in ['沢','青']:line=line.replace(ch,'{\\fnReconquista Noto Serif Review\\fs'+str(round(fs*1.25))+'}'+ch+'{\\fnEulyoo1945 SemiBold\\fs'+str(fs)+'}')
 out.append(line)
ass='\n'.join(out)+'\n';(O/'subtitles/opening-ko.ass').write_text(ass,encoding='utf-8-sig');lines=[l for l in out if l.startswith('Dialogue:')];ids=[l.split(',')[4] for l in lines];assert len(ids)==len(set(ids))==37
for r in quotes:
 line=next(l for l in lines if l.split(',')[4]==r['id']);target=re.sub(r'\{[^}]*\}','',line.split(',',9)[9]).replace('\\N','\n');assert target==r['target']
p=O/'semantic-inputs.json';sem=json.loads(p.read_text(encoding='utf-8'));sem['credits']=cr;sem['removed_caption_cues']=[{'id':k,'reason':'Korean brush logo replaces duplicate plain title cue.'} for k in sorted(title_ids)];sem['retained_cue_count']=37;sem['source_semantic_hashes']['translation/opening-credits-ko.json']=hashlib.sha256((U/'translation/opening-credits-ko.json').read_bytes()).hexdigest();p.write_text(json.dumps(sem,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
frames=[round((r['start']+r['end'])/2*30) for r in quotes];sel='+'.join(f'eq(n\\,{n})' for n in frames);ff='F:/DOWN/ffmpeg-7.1.1-essentials_build/ffmpeg-7.1.1-essentials_build/bin/ffmpeg.exe';pr=subprocess.run([ff,'-hide_banner','-loglevel','error','-f','lavfi','-i','color=c=black:s=800x600:r=30:d=100','-vf','ass=subtitles/opening-ko.ass:fontsdir=fonts,select='+sel,'-fps_mode','vfr','-f','rawvideo','-pix_fmt','rgb24','-'],cwd=O,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,creationflags=subprocess.CREATE_NO_WINDOW);arr=np.frombuffer(pr.stdout,np.uint8).reshape(-1,600,800,3);checks=[]
for r,n,a in zip(quotes,frames,arr):
 ink=np.max(a,2)>12;assert ink[:72].any() and not ink[72:526].any();y,x=np.nonzero(ink[:72]);checks.append({'id':r['id'],'frame':n,'bbox':[int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)],'contained':True})
p=O/'evidence/caption-bounds.json';ev=json.loads(p.read_text(encoding='utf-8'));ev.update(cue_count=37,retained_cue_count=37,actual_ass_cue_count=37,actual_ass_cue_ids=ids,removed_cue_ids=sorted(title_ids),restored_quote_checks=checks,ass_sha256=hashlib.sha256((O/'subtitles/opening-ko.ass').read_bytes()).hexdigest(),reuse_note='Existing unchanged caption/font checks reused; four restored quotation cues newly rendered and checked. Only two exact title IDs omitted.');p.write_text(json.dumps(ev,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'retained':len(ids),'removed':sorted(title_ids),'restored':checks},ensure_ascii=False))
p=U/'HANDOFF.md';p.write_text(p.read_text(encoding='utf-8')+'\n\n- OP 자막 ID 수정 완료: 제거 집합은 정확히 title-1/title-2 두 개, 인용문4개 원래 승인 번역 복구. ASS 실제37개/메타데이터37개 일치, 복구4cue 새 렌더·검은 여백 경계 검증 PASS. 나머지 기존 글꼴 검증 재사용.\n',encoding='utf-8')
