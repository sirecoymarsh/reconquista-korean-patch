"""Correct only the observed canonical-term particle regression; bounded postreview delta."""
from pathlib import Path
import json,collections,shutil
import build_trial as b
from inspect_majiro import Arc,sha,dump
ROOT=b.ROOT;F=ROOT/'translation/integration/recovery-full-20261023-v2';B=ROOT/'builds/integrated-recovery-full-20261023-v2';O=ROOT/'runtime-recovery-full-20261023-v2'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def h(p):return sha(p.read_bytes())
d=load(F/'integrated-targets.json');m=load(B/'manifest.json');v=load(F/'verification.json');assert h(F/'integrated-targets.json')==m['snapshot_sha256']==v['snapshot_sha256'];assert h(B/'scenario.arc')==m['outputs']['scenario.arc']==h(O/'scenario.arc')
mp=load(B/'font-map.json')['mapping'];inv={v:k for k,v in mp.items()};changes=[];groups=collections.defaultdict(list)
for r in d['records']:
 if '반혼술으로' not in r['target']:continue
 old=r['target'];r['target']=old.replace('반혼술으로','반혼술로');change={'id':r['id'],'source':r['source'],'before':old,'after':r['target'],'reason':'Canonical 反魂の法 term ends with ㄹ: instrumental particle 로. Fix particle left behind by prior terminology replacement.','translator_model':'Codex internal'};changes.append(change);groups[r['id'].split('::')[0]].append(change);r['integration_editor']='Codex internal /root';r['integration_review']=change['reason']
assert len(changes)==25
old_snapshot=m['snapshot_sha256'];old_arc=m['outputs']['scenario.arc'];a=Arc(B/'scenario.arc');payloads={}
with a.path.open('rb') as f:
 for e in a.entries:f.seek(e['offset']);payloads[e['name']]=f.read(e['size'])
delta={}
for name,rows in groups.items():
 src,_=b.decode(payloads[name]);rep={}
 for c in rows:
  i=int(c['id'].split('::')[1]);x=src.instructions[i];assert x.opcode.mnemonic=='text';assert ''.join(inv.get(z,z) for z in x.string)==c['before'];rep[i]=b.string_ins('text',''.join(mp.get(z,z) for z in c['after']))
 payloads[name],delta[name]=b.rewrite(payloads[name],rep);after,_=b.decode(payloads[name])
 for c in rows:assert ''.join(inv.get(z,z) for z in after.instructions[int(c['id'].split('::')[1])].string)==c['after']
 m['script_validation'][name]['output_sha256']=sha(payloads[name]);m['script_validation'][name]['particle_delta']=delta[name]
(B/'scenario.arc').write_bytes(a.rebuild(payloads));ar=Arc(B/'scenario.arc')
with ar.path.open('rb') as f:
 for e in ar.entries:f.seek(e['offset']);assert f.read(e['size'])==payloads[e['name']]
d['root_review']['changes'].extend(changes)
for n in ['integrated-targets.json','targets.json']:dump(F/n,d)
m['snapshot_sha256']=h(F/'integrated-targets.json');m['outputs']['scenario.arc']=h(B/'scenario.arc');m['root_review']=d['root_review'];m['post_review_particle_delta']={'before_snapshot_sha256':old_snapshot,'before_scenario_sha256':old_arc,'fields':25,'changes':changes,'script_validation':delta,'scope':'Only instrumental particle 으로→로 after canonical 반혼술; targets shorten by one mapped character.'}
m['review2_delta']['recovered_scripts']=m['review2_delta']['changed_scripts'];m['review2_delta']['changed_scripts']=sorted(set(m['review2_delta']['changed_scripts'])|set(groups));m['review2_delta']['extra_particle_fields']=25
shutil.copy2(B/'scenario.arc',O/'scenario.arc');assert h(O/'scenario.arc')==m['outputs']['scenario.arc']
v.update(snapshot_sha256=m['snapshot_sha256'],scenario_sha256=m['outputs']['scenario.arc'],post_review_particle_fields=[x['id'] for x in changes],post_review_particle_validation='PASS: exact prior target→corrected target, control flow preserved, archive equality; all replacements shorten by one glyph.')
dump(F/'verification.json',v)
for p in [B/'manifest.json',O/'BUILD-IDENTITY.json']:dump(p,m)
dump(ROOT/'reports/latest-recovery-build.json',{'path':str(B),**m})
report=load(F/'integration-report.json');report.update(snapshot_sha256=m['snapshot_sha256'],extra_particle_corrections=25);dump(F/'integration-report.json',report)
latest=load(ROOT/'translation/integration/latest.json');latest['snapshot_sha256']=m['snapshot_sha256'];dump(ROOT/'translation/integration/latest.json',latest)
progress=load(ROOT/'progress.json');progress['recovery_review2_20261023'].update(snapshot_sha256=m['snapshot_sha256'],extra_particle_corrections=25);dump(ROOT/'progress.json',progress)
dump(F/'particle-corrections.json',m['post_review_particle_delta'])
print(json.dumps({'corrected_fields':25,'scripts':sorted(groups),'final_snapshot_sha256':m['snapshot_sha256'],'final_scenario_sha256':m['outputs']['scenario.arc']},ensure_ascii=False))
