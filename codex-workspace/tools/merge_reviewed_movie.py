"""Stage one reviewed OP movie in a fresh cumulative runtime; original hardlinked media stays intact."""
from pathlib import Path
import sys,json,os,shutil,argparse,datetime
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'tools'));from inspect_majiro import sha,dump
ap=argparse.ArgumentParser();ap.add_argument('--base',required=True);ap.add_argument('--label',required=True);ap.add_argument('--candidate',required=True);ap.add_argument('--proof',required=True);a=ap.parse_args()
A=R/'builds'/a.base;O=R/'builds'/a.label;C=R/'ui-opening-ending/candidates'/a.candidate;S=R/('runtime-'+a.base);T=R/('runtime-'+a.label);proof=json.loads((R/a.proof).read_text(encoding='utf-8'));cm_path=C/'manifest.json'
assert sha(cm_path.read_bytes())==proof['candidate_manifest_sha256'];assert proof['semantic_pass'] and proof['visual_pass'] and proof['technical_pass'];assert proof['audio_stream_identical'] and proof['codec_dimensions_fps_and_frame_count_preserved']
name=proof['relative_output'];assert name=='movie/Recon_OP800_H.mpg';source=C/'payloads'/name;assert source.is_file() and sha(source.read_bytes())==proof['output_sha256'];assert sha((S/name).read_bytes())==proof['source_sha256'];assert not O.exists() and not T.exists()
m=json.loads((A/'manifest.json').read_text(encoding='utf-8'));O.mkdir();T.mkdir()
for p in A.rglob('*'):
 rel=p.relative_to(A);q=O/rel
 if p.is_dir():q.mkdir(exist_ok=True)
 elif rel.as_posix() not in ['manifest.json','installation.json',name]:os.link(p,q)
(O/name).parent.mkdir(exist_ok=True);shutil.copy2(source,O/name);assert sha((O/name).read_bytes())==proof['output_sha256'];assert not os.path.samefile(O/name,S/name)
I=O/'delta-inputs'/a.candidate;I.mkdir(parents=True,exist_ok=False)
for n in ['manifest.json','semantic-inputs.json']:
 if (C/n).is_file():shutil.copy2(C/n,I/n)
for n in ['evidence','subtitles']:
 if (C/n).is_dir():shutil.copytree(C/n,I/n)
dump(I/'central-review.json',proof)
save_copy_hashes=[]
for p in S.rglob('*'):
 rel=p.relative_to(S);q=T/rel
 if p.is_dir():q.mkdir(exist_ok=True)
 elif rel.as_posix()!=name and p.name not in ['BUILD-IDENTITY.json','한국어화-상태.md']:
  if rel.parts[0]=='savedata':
   shutil.copy2(p,q);save_hash=sha(p.read_bytes());assert sha(q.read_bytes())==save_hash;save_copy_hashes.append({'file':rel.relative_to('savedata').as_posix(),'sha256':save_hash})
  else:os.link(p,q)
shutil.copy2(O/name,T/name);assert sha((T/name).read_bytes())==proof['output_sha256'];assert not os.path.samefile(T/name,S/name)
m.update(label=a.label,parent_build=str(A),parent_manifest_sha256=sha((A/'manifest.json').read_bytes()),installed_runtime=str(T),savedata_copied_from=str(S/'savedata'),save_copy_hashes=save_copy_hashes,installed_hash_verification_scope={'newly_verified':['movie copy hash','new savedata source/copy hashes'],'unchanged_payloads':'Previous build evidence reused; exact hardlinks preserved; launcher verifies all controlled outputs before execution'});m['outputs'][name]=proof['output_sha256'];m['op_ed_status'].update(opening_movie_localized=True,opening_lyric_lines=proof['opening_lyric_lines'],opening_credit_cues=proof['opening_credit_cues'],opening_logo_localized=proof['opening_logo_localized'],opening_audio_unchanged=True,actual_game_sync_verified=False);m.setdefault('brand_logo',{})['opening_logo_integrated']=proof['opening_logo_localized'];m['opening_movie_integration']={'candidate':str(C),'frozen_proof':'delta-inputs/'+a.candidate+'/central-review.json','source_sha256':proof['source_sha256'],'output_sha256':proof['output_sha256'],'runtime_verification':'user_pending'};m['source_unit_accounting']['op_ed_status']=m['op_ed_status'];dump(O/'manifest.json',m);dump(T/'BUILD-IDENTITY.json',m)
p=R/'Start-Korean.ps1';txt=p.read_text(encoding='utf-8-sig');assert a.base in txt;p.write_text(txt.replace(a.base,a.label),encoding='utf-8-sig')
p=R/'progress.json';g=json.loads(p.read_text(encoding='utf-8'));g.update(runtime=str(T),updated_at=datetime.datetime.now().astimezone().isoformat());g['body_ui_integration'].update(label=a.label,build=str(O),runtime=str(T),op_ed_status=m['op_ed_status'],brand_logo=m['brand_logo']);g['translation']['build']=str(O);g['next']='Reconcile remaining UI source/clean-plate blockers and finalize handoff. Actual native game verification remains user-owned.';dump(p,g);dump(R/'reports/combined-source-coverage.json',m['source_unit_accounting']);dump(R/'reports/latest-combined-build.json',{'path':str(O),'runtime':str(T),'manifest_sha256':sha((O/'manifest.json').read_bytes()),'label':a.label})
print(json.dumps({'build':a.label,'runtime':str(T),'movie':name,'movie_sha256':proof['output_sha256'],'all_archives_fonts_exe_preserved':True,'game_executed':False},ensure_ascii=False))