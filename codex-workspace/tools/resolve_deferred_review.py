"""Root-authored recovery, exact whitespace exceptions, and audited technical display literals."""
from pathlib import Path
import json,hashlib,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from build_trial import decode
from inspect_majiro import dump,sha
THREAD='01a16283-b393-7dc0-8c83-d3e23a2a2f41'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
translations={
'masa_10.mjo::u0169':['「마사키 언니, 이번엔 모미지가 등을 씻어 줄게.」'],
'masa_10.mjo::u0170':['「정말? 그럼 부탁할까?」'],
'masa_10.mjo::u0171':['「쓱싹쓱싹, 쓱싹쓱싹…」'],
'masa_10.mjo::u0172':['「아하하핫. 아, 정말, 간지러워어.」'],
'masa_10.mjo::u0175':['「………」'],
'masa_10.mjo::u0177':['하지만 생각해 보면,','모미지는 여자와 함께 목욕한 경험이 거의 없었다.'],
'masa_10.mjo::u0179':['「（…아니, 난 지금 무슨 생각을 하는 거야!）」'],
'masa_10.mjo::u0180':['「（아니, 애초에 난','　왜 귀를 기울이고 있는 거야!）」'],
'masa_10.mjo::u0181':['에휴… 이래서야 변태나 다름없잖아.'],
'masa_10.mjo::u0189':['「…TV에 집중이 안 돼…」'],
'masa_10.mjo::u0192':['대조적인 두 사람의 모습에 쓴웃음을 지으며,','몸이 식기 전에 모미지를 침대에 눕혀 재운다…'],
'masa_15.mjo::u0124':['「빤히~…」'],
'masa_15.mjo::u0125':['「응? 왜 그래, 모미지야?」'],
'masa_15.mjo::u0126':['「좋겠다, 마사키 언니는. 가슴이 있어서.」'],
'masa_15.mjo::u0127':['「그런가? 그냥 보통 정도인 것 같은데.」'],
'masa_15.mjo::u0128':['「그런데 모미지 건 납작하잖아?」'],
'masa_15.mjo::u0129':['「그야 모미지는 아직 어리잖아.','　크면 가슴도 자랄 거야.」'],
'masa_15.mjo::u0130':['「흐음… 그렇구나.」'],
'masa_15.mjo::u0131':['응, 응, 하고 깊이 고개를 끄덕이면서도','내 가슴을 빤히 바라보는 모미지.'],
'masa_15.mjo::u0154':['「서두르지 않아도 괜찮아.','　때가 되면 싫어도 커질 테니까.」'],
}
assert len(translations)==20
tech={
'sina_19_2.mjo::u0181':['　'],
'last_kako12.mjo::u0115':['「건강할 때나 병들 때나,','　기쁠 때나 슬플 때나…','　','　부유할 때나 가난할 때나,','　서로 사랑하고 존중하며, 위로하고 도우며――」'],
'last_gendai05.mjo::u0149':['「그 밖의 일들은','　제게는 ',' ','먼지나 다를 바 없으니까요… 크크크」'],
'kosihata.mjo::u0025':['『도망쳐도망쳐','도망쳐도망쳐도망쳐도망쳐도망쳐도망쳐','　도망쳐','도망쳐도망쳐도망쳐도망쳐도망쳐도망쳐도망쳐','　','도망쳐도망쳐도망쳐도망쳐도망쳐――!』'],
'st_pika.mjo::u0010':['　','미국의 핫도그 많이 먹기 대회에서 최다 섭취 기록이','경신됐다는 뉴스가 나왔던 모양입니다.'],
}
exceptions={
'sina_19_2.mjo::002198':('34820d62b45f38b7781ad1acbe0e956340dca23db049209496a445557b37a43d','　','　','Original U+3000 independent black-screen page; proc/p/w/wait_skip1500 preserved'),
'last_kako12.mjo::001793':('a3093e064afb783a9806afeb23ecccbc878b817fa93e3b27535c1bc3575d2e75','　','　','Original U+3000 blank line within vow and voice transition; proc/n preserved'),
'last_gendai05.mjo::001496':('9e5f8bfd3a885fdb298039123c95c604a19bc669315986a1a52ac5517704b34d','ちりあくた',' ','Manual phonetic ruby; 12px size/negative y offset and ctrl r restore preserved; base meaning in001509'),
'kosihata.mjo::000376':('e4421e0fde3d02fe1964809b5e85ac3fe5c16c0579ddb773168c0ceea64195c1','　','　','Original U+3000 indentation before three ruby outputs'),
'st_pika.mjo::000070':('7271c0d5eb542c8ebaf3c58c4a55bafa687cb6dd375a904e3433a38da39d5fa9','　','　','Original U+3000 leading blank line; proc/n preserved'),
}
o=load(ROOT/'body-parallel/ownership.json');sources={};units={}
for row in o['files']:
 if row['script'] in {u.split('::')[0] for u in [*translations,*tech]}:
  packet=load(ROOT/'body-parallel'/row['packet']);sources[row['script']]=row['source_sha256']
  assert sha((ROOT/'research/extracted/scenario'/row['script']).read_bytes())==row['source_sha256']
  units.update({u['unit']:u for u in packet['units']})
records=[];unit_records=[]
for uid,targets in {**translations,**tech}.items():
 u=units[uid];fields=[f for f in u['fields'] if f['role']=='text'];assert len(fields)==len(targets),(uid,len(fields),len(targets))
 if uid in translations:
  category='nonsexual_general_dialogue_restored'
  if uid.startswith('masa_10'):
   reason='Independent washing/care, background, silence, self-reflection or mundane reaction; original scene u0155-u0198 checked; sexualized contact/erotic framing excluded separately'
   narrator='마키노';phase='마사키 루트 10, 일상 목욕 돌봄과 거실 시점'
  else:
   reason='Nonsexual developmental curiosity/dialogue before intimate contact, or general growth reassurance; u0115-u0161 checked; contact proposal/action/reactions excluded separately'
   narrator='마사키';phase='마사키 루트 15, 비성적 신체 발달 문답'
  speaker={'もみじ':'모미지','麻咲':'마사키','槙野':'마키노'}.get(u.get('speaker'),narrator+'(서술)')
  addressees=['마사키'] if speaker=='모미지' else ['모미지'] if speaker=='마사키' else ['자기 자신'] if u.get('speaker') else []
  context={'speaker_identity':speaker,'addressees':addressees,'story_phase':phase,'voice':'기존 가족/친근한 반말 관계 또는 해당 서술자의 1인칭','review_reason':reason}
 else:
  category='technical_exception_resolved';context={'speaker_identity':u.get('speaker') or 'source narrator/test fixture','addressees':[],'story_phase':u['phase'],'review_reason':'Exact hash-bound whitespace/manual-ruby exception; complete neighboring meaning and original controls preserved'}
 rr=[]
 for f,t in zip(fields,targets):
  if not t.strip():
   h,s,v,reason=exceptions[f['id']];assert h==sources[uid.split('::')[0]] and s==f['source'] and t==v
  assert t and '\0' not in t
  rec={'id':f['id'],'unit':uid,'source':f['source'],'target':t,'source_sha256':sources[uid.split('::')[0]],'context':context,'translator_model':'Codex internal','provenance':{'root_thread':THREAD,'date':'2026-10-23','author':'primary model; technical existing Codex drafts checked and adopted/edited'},'status':'root_context_reviewed_static_pending_runtime_pending','recovery_category':category}
  records.append(rec);rr.append(rec)
 unit_records.append({'unit':uid,'category':category,'fields':[r['id'] for r in rr],'context':context})
inline=[];script='kosihata.mjo';s,_=decode((ROOT/'research/extracted/scenario'/script).read_bytes())
it={361:('げろげろげろげろ','게로게로게로게로','ruby_reading_nonstandard_phonetic_fixture'),362:('逃げろ','도망쳐','ruby_body'),370:('逃げろ','도망쳐','emphasis_body'),378:('ニゲロ',' ','ruby_reading_redundant'),379:('逃げろ','도망쳐','ruby_body'),381:('ニゲロ',' ','ruby_reading_redundant'),382:('逃げろ','도망쳐','ruby_body'),384:('ニゲロ',' ','ruby_reading_redundant'),385:('逃げろ','도망쳐','ruby_body')}
for idx,(source,target,role) in it.items():
 ins=s.instructions[idx];assert ins.opcode.mnemonic=='ldstr' and ins.string==source
 callidx=idx+1 if role in ['ruby_body','emphasis_body'] else idx+2
 expected=0x2f93f26a if role=='emphasis_body' else 0x3198fd01
 assert s.instructions[callidx].hash==expected
 inline.append({'id':f'{script}::{idx:06d}','unit':script+'::u0025','index':idx,'opcode':'ldstr','source':source,'target':target,'role':role,'source_sha256':sources[script],'consumer':f'yazlib ${expected:08x}','evidence':f'Original instruction {idx} follows source fixture; actual call at{callidx}; nonstandard reading361 retained as phonetic fixture, other redundant kana readings suppressed with one ASCII space','translator_model':'Codex internal','provenance':{'root_thread':THREAD,'date':'2026-10-23'},'status':'consumer_verified_runtime_pending'})
prior={}
for p in (ROOT/'body-parallel').glob('session-*/lane-*/batches/*.json'):
 for d in load(p).get('deferred',[]):prior[d['unit']]={'unit':d['unit'],'prior_reason':d['reason'],'source_artifact':str(p.relative_to(ROOT))}
assert len(prior)==62
boundary={'00_レコンキスタ_start_2.mjo::u1356','maho_14.mjo::u0229','maho_14.mjo::u0244','maho_14.mjo::u0247'}
decisions=[]
for uid,item in sorted(prior.items()):
 verdict='restore_general' if uid in translations else 'resolve_technical' if uid in tech else 'retain_boundary_action_review' if uid in boundary else 'retain_direct_sexual_context'
 reason='Ordinary independent nonsexual meaning verified by primary and independent reader' if verdict=='restore_general' else 'Exact source/target codepoint exception plus complete display consumer audit' if verdict=='resolve_technical' else 'Childhood clothing-lifting action is directly described; no body-detail/arousal claim added. Independent reviewer did not certify as ordinary content.' if uid in boundary else 'Source + neighboring context links this unit directly to sexualized child contact, erotic response/comparison, or viewing frame; no target created'
 decisions.append({**item,'decision':verdict,'root_reason':reason})
out=ROOT/'translation/recovery-20261023';out.mkdir(parents=True,exist_ok=True)
exc=[{'id':k,'source_sha256':h,'opcode':'text','source':s,'target':v,'source_codepoints':[f'U+{ord(c):04X}' for c in s],'target_codepoints':[f'U+{ord(c):04X}' for c in v],'reason':reason} for k,(h,s,v,reason) in exceptions.items()]
dump(out/'recovered-targets.json',{'translator_model':'Codex internal','root_thread':THREAD,'source_files':sources,'records':records,'inline_records':inline,'units':unit_records,'whitespace_exceptions':exc,'scope':'20 general nonsexual units restored +5 technical units completed; remaining37 not translated','runtime_verified':False})
dump(out/'review.json',{'translator_model':'Codex internal','requested_content_review':57,'restored_general_units':20,'technical_units_resolved':5,'technical_text_fields':sum(r['unit'] in tech for r in records),'new_technical_inline':len(inline),'retained_direct_context':33,'retained_boundary_action':4,'retained_total':37,'independent_review':'review_opening_early/late read-only source+consumer audit; primary authored and reviewed targets','decisions':decisions,'unit_records':unit_records,'runtime_pending':True})
print(json.dumps({'path':str(out),'restored_units':20,'technical_units':5,'text_fields':len(records),'inline':len(inline),'remaining_deferred':37},ensure_ascii=False))
