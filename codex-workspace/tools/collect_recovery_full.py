"""Freeze all current approved body translations plus the bounded root recovery."""
from pathlib import Path
import json,hashlib,shutil,re,datetime
ROOT=Path(__file__).resolve().parents[1]
LABEL='recovery-full-20261023-v1'
def canonical_character_names(text):
    for old, new in {'가미조': '카미조', '다무라': '타무라', '가스가이': '카스가이', '게이고': '케이고', '도오루': '토오루', '도모코': '토모코', '가나야마': '카나야마'}.items():
        text=text.replace(old,new)
    return text

def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
 out=ROOT/'translation/integration'/LABEL;assert not out.exists()
 base=ROOT/'translation/integration/session1-04fc30b0-widthqa-v1/integrated-targets.json'
 bm=load(ROOT/'builds/integrated-session1-04fc30b0-widthqa-v1/manifest.json');assert sha(base)==bm['snapshot_sha256']
 d=load(base);records={r['id']:r for r in d['records']};inline={r['id']:r for r in d['inline_records']};accepted=[]
 def add(p,exclude=()):
  b=load(p);h=sha(p);lane=p.parent.parent;v=load(lane/'validation.json')['batches'];key=str(p.relative_to(lane));vr=v.get(key,v.get(key.replace('\\','/')))
  assert vr and vr['sha256']==h and vr['structural_pass'],p
  d['source_files'][b['source_script']]=b['source_sha256']
  count=0
  for u in b['records']:
   if u['unit'] in exclude:continue
   count+=1
   for f in u['fields']:
    if f['id'] in records:assert records[f['id']]['source']==f['source']
    records[f['id']]={**f,'unit':u['unit'],'context':u['context'],'source_sha256':b['source_sha256'],'translator_model':'Codex internal','origin':str(p.relative_to(ROOT)),'origin_sha256':h,'provenance':{'coordinator_thread_id':b.get('coordinator_thread_id'),'agent_id':b.get('agent_id')}}
  for f in b.get('inline_records',[]):
   if f.get('unit') in exclude:continue
   if f['id'] in inline:assert inline[f['id']]['source']==f['source']
   inline[f['id']]={**f,'opcode':'ldstr','index':int(f['id'].rsplit('::',1)[1]),'source_sha256':b['source_sha256'],'translator_model':'Codex internal','origin':str(p.relative_to(ROOT)),'origin_sha256':h}
  accepted.append({'path':str(p.relative_to(ROOT)),'sha256':h,'units':count,'excluded_units':list(exclude),'validation':str((lane/'validation.json').relative_to(ROOT)),'verification':'reuse exact current hash structural PASS and coordinator final handoff'})
  return count
 s2=ROOT/'body-parallel/session-2';review2=load(s2/'coordinator-review.json');assert not review2['pending_findings']
 n2=sum(add(p) for p in sorted(s2.glob('lane-*/batches/*.json')));assert n2==17420
 s3=ROOT/'body-parallel/session-3';handoff=load(s3/'review-handoff-manifest.json');n3=0
 for b in handoff['accepted_batches']:
  p=s3/b['path'];assert sha(p)==b['sha256'];c=add(p,b['excluded_unit_ids']);assert c==b['accepted_units'];n3+=c
 assert n3==11721
 # Remove a previously drafted but never semantically accepted unit, if an older base included it.
 records={k:v for k,v in records.items() if v['unit']!='st_gin.mjo::u0068'}
 recovery=ROOT/'translation/recovery-20261023/recovered-targets.json';r=load(recovery);d['source_files'].update(r['source_files'])
 for f in r['records']:assert f['id'] not in records;records[f['id']]={**f,'origin':str(recovery.relative_to(ROOT)),'origin_sha256':sha(recovery)}
 for f in r['inline_records']:assert f['id'] not in inline;inline[f['id']]={**f,'origin':str(recovery.relative_to(ROOT)),'origin_sha256':sha(recovery)}
 changes=[]
 def fix(f,target,reason):
  if f['target']==target:return
  changes.append({'id':f['id'],'before':f['target'],'after':target,'reason':reason});f['target']=target;f['integration_editor']='Codex internal /root';f['integration_review']=reason
 for f in [*records.values(),*inline.values()]:
  fix(f,canonical_character_names(f['target']).replace('미션 스쿨','미션스쿨'),'Existing central canonical surname and school term')
  if '反魂の法' in f['source'] or '反魂法' in f['source']:fix(f,f['target'].replace('반혼법','반혼술'),'Reuse canonical name of same resurrection rite; source-scoped')
 terms=load(s2/'term-reconciliation-kite-winder.json')
 for item in terms['items']:
  f=records.get(item['id']) or inline.get(item['id'])
  if f and '실감개' in f['target']:
   assert f['source']==item['source'];fix(f,f['target'].replace('실감개','얼레'),'Same kite-winder object, maho_sub2::000420 explicit definition; ordinary 失敗 excluded')
 for prior_edit in load(ROOT/'translation/integration/reviewed-001/integrated-targets.json')['root_review']['changes']:
  f=records.get(prior_edit['id']) or inline.get(prior_edit['id'])
  if f and f['target']==prior_edit['before']:fix(f,prior_edit['after'],'Reuse existing exact-field central correction: '+prior_edit['reason'])
 manual={'maho_15.mjo':[(3235,'　はんごん',3248),(7626,'あがな',7639)],'maho_16.mjo':[(2838,'たが',2851),(3262,'みの',3275)],'maho_18.mjo':[(960,'くら',973)],'maho_19.mjo':[(4359,'ひとしお',4372),(5298,'てい',5311),(6431,'か',6444),(6458,'くぐ',6471),(6904,'やから',6917),(7174,'とばり',7187)]}
 exceptions=list(r['whitespace_exceptions'])
 for script,rows in manual.items():
  for index,source,body in rows:
   f=records[f'{script}::{index:06d}'];assert f['source']==source;bf=records[f'{script}::{body:06d}']
   fix(f,' ','Audited phonetic-only manual ruby; exact reading suppressed, ctrl stream and base meaning retained')
   exceptions.append({'id':f['id'],'source_sha256':d['source_files'][script],'opcode':'text','source':source,'target':' ','body_id':bf['id'],'body_target':bf['target'],'reason':'Read-only independent direct-consumer audit: ctrl s/o/f12 then reading then ctrl r/s/f restore then base; redundant reading only'})
 for protected in ['maho_14.mjo::004449','maho_06.mjo::004621']:assert records[protected]['target'].strip()
 allrows=[*records.values(),*inline.values()];units={f['unit'] for f in records.values()};assert len(units)==46913,(len(units),len(records))
 assert len(records)==73314 and len(inline)==625,(len(records),len(inline))
 assert len({f['id'] for f in allrows})==len(allrows)
 # Verify only new recovery unit completeness; existing accepted batches reuse their exact-hash validators.
 packets=[load(p) for p in (ROOT/'body-parallel/source').glob('*.json')];pu={u['unit']:u for p in packets for u in p['units']}
 for u in r['units']:
  expected={f['id'] for f in pu[u['unit']]['fields'] if f['role']=='text'};assert expected==set(u['fields'])
 for name,h in d['source_files'].items():assert sha(ROOT/'research/extracted/scenario'/name)==h
 names={'もみじ':'모미지','槙野':'마키노','麻咲':'마사키','義父':'장인','信哉':'신야','おばさん':'아주머니','まほほ':'마호호','まほママ':'마호 엄마','真帆子':'마호코','詩菜':'시이나','汐見':'시오미','男':'남자','奈那子':'나나코','まほ':'마호','男１':'남자 1','男２':'남자 2','男３':'남자 3','前田':'마에다','担任':'담임','女子生徒Ａ':'여학생 A','男子生徒Ａ':'남학생 A','女子生徒Ｂ':'여학생 B','保健医':'보건의','女子生徒Ｃ':'여학생 C','女子生徒Ｄ':'여학생 D','八百屋':'채소 가게 주인','先生':'선생님','日直':'당번','暮葉':'쿠레하','男達':'남자들','槙野＆義父':'마키노＆장인','矢嶋':'야시마','紅葉':'모미지','運転手':'운전기사','覆面男':'복면 남자','店員':'점원','金山':'카나야마','女生徒１':'여학생 1','女生徒２':'여학생 2','麻咲母':'마사키 어머니','警察官':'경찰관','宅配便':'택배 기사','詩帆':'시호','少年':'소년','上条':'카미조','女生徒':'여학생','医者':'의사','朋子':'토모코','悠絵':'유에','消防署員':'소방관','アナウンス':'안내 방송','村人':'마을 사람','一ノ瀬':'이치노세','妹':'여동생','母':'어머니','父':'아버지','トオル':'토오루','村人達':'마을 사람들','村人１':'마을 사람 1','赤ん坊':'아기','汐見父':'시오미 아버지','看護婦':'간호사','コンビニ店員':'편의점 점원','女性':'여성','女の子':'여자아이','まほこ':'마호코','真帆ママ':'마호 엄마','首刈り女':'목 베는 여자','男子生徒Ｂ':'남학생 B','男子生徒Ｃ':'남학생 C','ヤシマ':'야시마','ヤスィマ':'야쓰마','覆面':'복면','警察':'경찰','真帆子パンツ':'마호코 팬티','お父さん':'아빠','男子生徒':'남학생','祖母':'할머니','父親':'아버지','母親':'어머니','引っ越し屋':'이삿짐센터 직원','槇野':'마키노','生徒達':'학생들','放送委員':'방송부원','ママ':'엄마','女生徒Ａ':'여학생 A','女生徒Ｂ':'여학생 B','女生徒Ｃ':'여학생 C','女子アナ':'여성 아나운서','麻＆も':'마사키＆모미지','さっちん':'삿친','ぽえみぃ':'포에미','工事関係者':'공사 관계자','一年女子':'1학년 여학생','救急隊員':'구급대원','天気予報':'일기 예보','汐見先生':'시오미 선생님','お母さん':'엄마','矢嶋ペキ':'야시마 페키','タクシー':'택시 기사','詩菜・信哉':'시이나·신야','信哉・詩菜':'신야·시이나','クレハ':'쿠레하','女子生徒':'여학생','詩菜・女の子':'시이나·여자아이','汐見・信哉':'시오미·신야','受付':'접수 직원','しーな':'시이나','あんころもち':'안코로모치','さかっきー':'사캇키','やなちぃ':'야나치','少女':'소녀','街頭演説':'거리 연설','兵士':'병사','伝道師':'전도사','女子':'여학생','教師':'교사'}
 observed={re.split('[＠（]',f['source'])[0] for p in packets for u in p['units'] for f in u['fields'] if f.get('role')=='speaker_token'};observed={x for x in observed if x.strip() and x not in ['＊＊＊','※※※']};assert observed==set(names),(observed-set(names),set(names)-observed)
 d.update(label=LABEL,records=list(records.values()),inline_records=list(inline.values()),units=len(units),text_fields=len(records),inline_fields=len(inline),runtime_verified=False,stage='all approved body batches + root recovery; build pending')
 d['coverage']={s:sorted(int(u.rsplit('u',1)[1]) for u in units if u.startswith(s+'::')) for s in d['source_files']}
 d['root_review']={'translator_model':'Codex internal','baseline':str(base.relative_to(ROOT)),'baseline_sha256':sha(base),'changes':changes,'name_map':names,'name_basis':['body-parallel/session-1/term-decisions.json','body-parallel/session-2/coordinator-review.json','body-parallel/session-3/terminology-decisions.json'],'name_limit':'Provisional source name readings retain existing author decisions; full spoken-name listening not complete','recovery':'translation/recovery-20261023/review.json','recovery_review_pass':'review_opening_early:20 units26 fields; review_opening_late:5 units19 ordinary9 inline','session2_review_scope':'Author contextual review all249 batches; coordinator targeted4974 units; not all independently reread','session2_stale_hashes':'2 metadata-only changes independently reconstructed to exact previous SHA; targets unchanged','accepted_batches':accepted,'exact_whitespace_exceptions':exceptions,'runtime_pending':True}
 d['pending_at_snapshot']={'body_units':38,'original_content_holds':37,'semantic_pending':['st_gin.mjo::u0068'],'ui_owned_units_separate':70,'full_route_runtime':True}
 out.mkdir(parents=True);prov=out/'provenance';prov.mkdir()
 for p in [recovery,recovery.parent/'review.json',s2/'coordinator-review.json',s2/'coordinator-progress.json',s2/'term-reconciliation-kite-winder.json',s3/'review-handoff-manifest.json',s3/'terminology-decisions.json']:
  shutil.copy2(p,prov/(p.parent.name+'-'+p.name))
 shutil.copy2(ROOT/'translation/hangul-cp932-map.json',out/'fontmap-seed.json')
 dump(out/'targets.json',d);dump(out/'integrated-targets.json',d);dump(out/'names.json',{'translator_model':'Codex internal','mapping':names,'count':len(names),'source_display_only':True})
 dump(out/'integration-report.json',{'status':'frozen_build_pending','label':LABEL,'translator_model':'Codex internal','created_at':datetime.datetime.now().astimezone().isoformat(),'units':len(units),'ordinary_fields':len(records),'inline_fields':len(inline),'new_recovery_units':25,'content_recovered':20,'technical_resolved':5,'extra_redundant_manual_ruby_fixed':11,'names':len(names),'canonical_edits':changes,'pending':d['pending_at_snapshot'],'reused_baseline_sha256':sha(base),'snapshot_sha256':sha(out/'integrated-targets.json')})
 print(json.dumps({'label':LABEL,'units':len(units),'fields':len(records),'inline':len(inline),'names':len(names),'canonical_changes':len(changes)},ensure_ascii=False))
if __name__=='__main__':main()
