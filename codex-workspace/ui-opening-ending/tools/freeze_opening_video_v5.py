from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
U=Path.cwd();O=U/'candidates/opening-video-ko-v5';V=U/'candidates/opening-video-ko-v4';E=O/'evidence'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,j):p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
assert not (O/'manifest.json').exists()
n=read(E/'technical-validation.json');f=read(E/'4k-technical-validation.json');vis=read(E/'final-visual-review.json');s=read(E/'semantic-gate.json');viewer=read(E/'review-viewer-test.json');q=read(E/'quote-restoration.json');b=read(E/'build-4k.json')
assert n['status']==f['status']=='technical_pass' and vis['status']==s['status']==viewer['status']=='pass'
assert all(x['protected_pixel_diff']==0 for x in q['frames'])
now=datetime.now(timezone.utc).isoformat()
for name,h in [('encoded-review.json',n['output_sha256']),('4k-encoded-review.json',f['sha256'])]:
 j=read(E/name);j.update(status='visual_pass',reviewed_at_utc=now,video_sha256=h);write(E/name,j)
m=read(V/'manifest.json');m.update(candidate='opening-video-ko-v5',created_at_utc=now,prior_frozen_candidate='opening-video-ko-v4',caption_cues=32,retained_quotation_cues=0,in_picture_surfaces=20)
m['inherited_changes']=m['changes'];m['changes']=['All four upper logo quotation captions removed','Both small English logo paragraphs replaced in place with compact Korean; high-resolution 4K glyphs','Intentional in darkness span retained verbatim in both lyric lines']
m['payloads'][0].update(output_sha256=n['output_sha256'],output_bytes=(O/'payloads/movie/Recon_OP800_H.mpg').stat().st_size)
m['viewing_outputs'][0].update(sha256=f['sha256'],bytes=f['bytes'],audio='Verified v4 AAC packets unchanged')
m['restoration']={'quote_clean_frames':len(q['frames']),'protected_pixel_diff_count':0,'methods':['registered original city artwork with observed motion and photometric matching','surrounding same-frame dark backdrop color surface','transition donor gradients joined with Poisson boundary matching'],'transition_roman_brand':'Source glyph alpha retained and reprojected with original motion in 29.7..30.67s transition only','new_imagegen_assets':0,'hidden_original_rgb_identical':False,'inherited_cleaning':'Frozen v4 and v3 clean backgrounds and repairs reused'}
m['verification'].update(native_samples=vis['native_unique_samples'],four_k_samples=vis['four_k_unique_samples'],four_k_compressed_frames_reused=sum(x['frames'] for x in b['copy_spans']),four_k_audio_pcm_reuse='Previously verified AAC reused after matching compressed hash')
m['quote_layout']={'native_font_size':9,'line_step':10.0,'left':253,'top':393.3,'lines':read(O/'revision-policy.json')['quote_lines'],'four_k':'Separately rasterized at scale 4.8; no enlargement of game glyph bitmap'}
m['native_completion_manifest']='game-manifest.json'
m['four_k_rendering']={'method':b['memory_strategy'],'new_frames':937,'compressed_frames_reused':2100,'chunks':len(b['segments']),'equivalence_evidence':'evidence/4k-lowmem-equivalence.json'}
ci=read(U.parent/'candidates/ui-rest-v1/opening-v5-integration.json')
assert ci['pass'] and ci['output_sha256']==n['output_sha256']
m['central_integration']={'build':'body-ui-20261023-v16-ui-rest','report':'../../../candidates/ui-rest-v1/opening-v5-integration.json','evidence_reused':True,'actual_op_playback':'user_pending'}
m['integration']='Game MPEG already integrated into central v16, per central integration evidence. This OP production task performed no installation or game playback. 4K is a separate viewing output.'
m['foreign_language_policy']='Translate Japanese lyric content; preserve intentional foreign spans. Explicit staff/role and logo paragraph translation requests remain applied.'
paths=[*U.glob('tools/*v5*.py'),*U.glob('tools/*v5*.cjs')]+[O/x for x in ['opening-credits-ko.json','lyrics-bilingual.json','revision-policy.json','subtitles/opening-ko.ass','subtitles/opening-ko-4k.ass']]
write(E/'build-input-hashes.json',{str(p.relative_to(U)).replace('\\','/'):sha(p) for p in paths})
write(O/'manifest.json',m)
notes='''레콘키스타 오프닝 v5

로고 위 큰 인용 자막을 제거하고 로고 아래 작은 영어 문구를 제자리에서 네 줄 한국어로 교체했습니다. 앞뒤 두 로고 장면에 적용했습니다.
가사 속 in darkness는 일본어·한국어 양쪽 줄에 원문 그대로 유지합니다.
작은 글자는 게임용에서 별도 식자하고 4K판에서는 고해상도로 직접 렌더링했습니다.

payloads/movie/Recon_OP800_H.mpg — 게임용 800×600 MPEG1, 원본 MP2 그대로
viewing/Reconquista_OP_KO_4K.mp4 — 16:9 3840×2160 감상용, 검증된 AAC 그대로
preview/review.html — 변경된 저장본 프레임 비교, 일반 휠 확대·축소 지원

3037프레임·30fps 및 음원·시각 동기를 파일로 검증했습니다. 이 제작 세션에서 게임 실행·오디오 재생·설치는 하지 않았습니다. 게임용은 별도 중앙 v16에 통합됐습니다.
4K는 SD 원본을 복원·업스케일하고 글자와 로고를 고해상도로 합성한 영상입니다.
기존 가사 op-lyrics::007의 원문 청취 추정은 미확정 상태를 유지합니다.
fonts/build-source/evidence는 내부 제작용이며 최종 영상만 전달 대상입니다.
'''
(O/'안내.txt').write_text(notes,encoding='utf-8')
p=U/'progress.json';j=read(p);j['updated_local']=datetime.now().astimezone().isoformat();j['active_user_revision']['op_quote_foreign_v5'].update(state='completed and frozen; changed-output technical, semantic, visual and silent headless viewer checks passed',four_k_state='complete',remaining=[],manifest='candidates/opening-video-ko-v5/manifest.json',native_sha256=n['output_sha256'],four_k_sha256=f['sha256'],ready_for_integration=True,awaiting_central_integration=False,central_integration='body-ui-20261023-v16-ui-rest',central_integration_report='../candidates/ui-rest-v1/opening-v5-integration.json',next='User viewing; native already integrated into central v16. No task-local creation remains.');j.setdefault('completed',[]).append('OP v5: logo quote translated in place in both scenes, four upper cues removed, in darkness retained; native and 4K outputs verified and frozen.');write(p,j)
with (U/'HANDOFF.md').open('a',encoding='utf-8') as z:z.write(f'\n\n## {now[:10]} OP v5 최종본\n\n- candidates/opening-video-ko-v5/manifest.json — frozen, ready_for_integration.\n- 게임 MPEG: {n["output_sha256"]}\n- 4K MP4: {f["sha256"]}\n- 앞뒤 로고 위 인용 자막4개 제거, 로고 아래 작은 원문 영어문단을 한국어4줄로 교체. 일본어/한국어 가사16쌍과 in darkness 원문보존.\n- 변경 구간 실제저장본 게임{vis["native_unique_samples"]}장·4K{vis["four_k_unique_samples"]}장 검토. 원본MP2·기존AAC 보존과3037프레임 시각검증PASS. 변경없는v4 검증재사용.\n- 원본·v4 보존. 게임·오디오재생·Explorer·전경조작·설치없음. OP007의원문청취추정유지.\n')
print(json.dumps({'status':'frozen','native':n['output_sha256'],'four_k':f['sha256'],'manifest':str(O/'manifest.json')},ensure_ascii=False,indent=2))
