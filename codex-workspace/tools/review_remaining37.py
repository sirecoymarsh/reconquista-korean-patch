"""Second source/context review of the37 retained units; Codex-authored bounded recovery."""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def dump(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
T={
'masa_10.mjo::u0168':['하지만 이따금 욕실에서 들려오는 두 사람의 들뜬 목소리가','아까부터 자꾸 신경 쓰였다.'],
'masa_10.mjo::u0173':['「어라? 그럼 이쪽은 어때? 쓱싹쓱싹…」'],
'masa_10.mjo::u0174':['「…으응, 거긴 좀 다른… 데에.」'],
'masa_10.mjo::u0176':['즐거워 보인다고 해야 하나, 뭐라고 해야 하나…','도대체 뭘 하는 건지 궁금해서 견딜 수가 없다.'],
'masa_10.mjo::u0178':['이참에 요시모리와 함께 목욕하면서','여자의 몸이 어떻게 생겼는지도 찬찬히 배워 보고…'],
'masa_10.mjo::u0184':['「마사키 언니, 여기는? 여기도 간지러워?」'],
'masa_10.mjo::u0185':['「안 된다니까, 거, 거긴, 아하하하… 으앗.」'],
'masa_10.mjo::u0187':['「정말, 마사키 언니, 가만히 좀 있어어.','　이러면 제대로 못 씻겨 주잖아아.」'],
'masa_10.mjo::u0188':['「그, 그렇게 말해도…','　으으, 하아하아… 히, 힉.」'],
'masa_10.mjo::u0191':['기분 탓인지 모미지는 평소보다 더 생기가 돌고,','반대로 요시모리는 녹초가 된 것 같았다.'],
'00_レコンキスタ_start_2.mjo::u1356':['늘 그랬듯 마호의 치마를 들추자,','당황한 듯한 목소리와 함께,'],
'maho_14.mjo::u0229':['치마를 들추면 마호가 얼레를 떨어뜨리고,','나는 그걸 주워 든다.'],
'maho_14.mjo::u0244':['그렇게 생각한 나는 마호를 놀라게 하려고','치마를 들추기 시작했고…'],
'maho_14.mjo::u0247':['나는 오늘도 치마를 들추고,','마호는 늘 있는 일인데도 오늘 역시 놀라 준다.'],
'masa_15.mjo::u0143':['「아핫, 간지러워.」'],
'masa_15.mjo::u0147':['「좋겠다, 좋겠다. 모미지도 가슴이 있었으면 좋겠어~」'],
'masa_15.mjo::u0149':['「아, 미안해. 아팠어?」'],
'masa_15.mjo::u0150':['「아, 아프진 않은데 말이야… 아하하.」'],
'masa_15.mjo::u0152':['…아니, 또 마키노 선생님을 떠올리고 있잖아, 나.','내가 생각해도 꽤 중증이네.'],
'masa_15.mjo::u0153':['「가슴이 있다는 건 좋겠다.','　모미지도 빨리 커졌으면 좋겠어.」'],
'st_yana.mjo::u0022':['「목욕 장면에서 계속 안 넘어가면,','　더위 먹을 거야, 아빠. 데·헷☆」'],
'st_gin.mjo::u0068':['나? 나는 초야.','남동생은 Ｊ●에서 일하고 있어.'],
}
assert len(T)==22
C={
'masa_10.mjo::u0168':('욕실의 두 사람 목소리가 신경 쓰인다는 아버지 시점. 嬌声 하나만으로 성적 신음을 확정했던 판단을 철회. 명시 행동은 등 씻기와 간지러움.','u0167–0172'),
'masa_10.mjo::u0173':('등을 씻기다가 다른 쪽은 어떤지 묻는 대사. 특정 성적 부위나 행동이 명시되지 않음.','u0169–0174'),
'masa_10.mjo::u0174':('씻기는 위치에 대한 반응. 앞선 간지럼과 구별되는 성적 접촉이라고 단정할 근거가 부족함.','u0169–0173'),
'masa_10.mjo::u0176':('욕실 밖 화자의 궁금증. ナニ 강조의 익살을 유지하되 구체적 성행위를 새로 추론하지 않음.','u0173–0181'),
'masa_10.mjo::u0178':('딸이 성인 여성과 목욕하며 체형을 배운다는 생각. 아동 신체의 상세나 성행위 묘사가 없으며 이어서 화자가 자기 생각을 끊음.','u0177–0181'),
'masa_10.mjo::u0184':('다른 곳도 간지러운지 묻는 씻기 대사. 특정 성적 접촉은 명시되지 않음.','u0169–0173,u0185–0187'),
'masa_10.mjo::u0185':('간지럽냐는 질문에 웃으며 말리는 반응. 신체 부위나 성적 흥분은 확정하지 않음.','u0184,u0187'),
'masa_10.mjo::u0187':('洗えない가 행동을 씻기로 직접 특정. 가만히 있으라는 일상적인 돌봄 대사.','u0184–0188'),
'masa_10.mjo::u0188':('웃음·간지럼에 이어지는 항변과 호흡. 이를 성적 쾌감으로 단정할 근거가 부족함.','u0184–0187'),
'masa_10.mjo::u0191':('목욕 후 생기 있는 아이와 지친 성인을 대비. 성적 상태나 신체 부위 묘사가 없음.','u0190,u0192'),
'00_レコンキスタ_start_2.mjo::u1356':('놀라게 하는 장난→얼레를 떨어뜨림→실을 감는 흉내→손잡기의 연결 서술. 노출된 신체나 성적 흥분 묘사가 없음.','u1351–1367'),
'maho_14.mjo::u0229':('장난과 얼레 회수 뒤 손잡기로 이어지는 행동. 장면의 목적과 결과가 명시됨.','u0225–0239'),
'maho_14.mjo::u0244':('놀라게 하려는 이유가 손잡을 구실을 만들기 위해서라고 앞뒤에서 설명됨. 신체 상세나 성적 흥분 묘사가 없음.','u0237–0246'),
'maho_14.mjo::u0247':('앞서 설명한 손잡기 위한 반복 행동을 회고. 장난의 실제 행동을 삭제하거나 완곡하게 바꾸지 않음.','u0241–0248'),
'masa_15.mjo::u0143':('간지럽다는 반응만 명시. 직접 접촉 상세나 성적 흥분을 새로 추론하지 않음.','u0142–0144'),
'masa_15.mjo::u0147':('자신의 신체 발달을 바라는 대사. 자체 행동·흥분 묘사가 없고 앞뒤 성장 문답과 연결됨.','u0126–0129,u0153–0154'),
'masa_15.mjo::u0149':('사과하고 아팠는지 묻는 일반 대사. 접촉을 구체적으로 재현하지 않음.','u0148,u0150'),
'masa_15.mjo::u0150':('아프지 않다는 답변. 원문에 없는 쾌감 표현으로 판정하지 않음.','u0149,u0151'),
'masa_15.mjo::u0152':('마키노를 또 떠올린 자신에 대한 자조. 앞 문장의 구체적 행위를 이 문장이 되풀이하지 않음.','u0116,u0151–0153'),
'masa_15.mjo::u0153':('자신의 성장에 관한 소망. 다음 성장 관련 답변과 직접 문답을 이룸.','u0147,u0154–0155'),
'st_yana.mjo::u0022':('목욕 장면 진행을 권하고 오래 머물면 더위 먹겠다는 메타 농담. 이 문장에는 노출 감상 지시가 없음. 手・屁ッ는 의도적 표기 장난을 읽기인 데·헷으로 보존.','u0018–0020,u0023'),
}
H={
'masa_15.mjo::u0134':('연결 대사','아이에게 성인의 신체를 만져 보도록 제안하는 기능. 대상·실행이 앞뒤에서 특정되어 일반 제안으로 분리하기 어려움.','u0131,u0138'),
'masa_15.mjo::u0135':('연결 대사','앞선 접촉 제안의 허락을 확인하는 대사. 문장 자체에 직접 묘사는 없다는 점을 정정.','u0134–0136'),
'masa_15.mjo::u0136':('연결 대사','앞선 특정 접촉을 허락하며 다음 실행으로 연결됨. 자체 직접 묘사는 없음.','u0134–0138'),
'masa_15.mjo::u0137':('연결 대사','허락에 대한 기쁨·감사가 바로 다음 실행을 구성. 직접 신체 묘사라고 기록했던 범주는 정정.','u0136,u0138'),
'masa_15.mjo::u0138':('직접 묘사','아이가 성인 신체에 접촉하는 대상과 행동을 구체적으로 묘사함.','u0134–0137,u0139'),
'masa_15.mjo::u0139':('직접 묘사','직전 구체적 접촉을 표현하는 효과음. 일반 소리로 분리하면 의미가 달라짐.','u0138,u0140–0141'),
'masa_15.mjo::u0140':('연결 대사','진행 중인 특정 접촉의 느낌을 묻는 기능. 문장 자체에 직접 묘사는 없음.','u0138–0141'),
'masa_15.mjo::u0141':('직접 묘사','해당 접촉 대상의 촉감과 감각을 설명함.','u0138–0140'),
'masa_15.mjo::u0142':('직접 묘사','같은 접촉이 반복되는 효과음.','u0141,u0144–0145'),
'masa_15.mjo::u0144':('직접 묘사','같은 신체 대상의 촉감을 반복해 설명함.','u0138,u0142–0145'),
'masa_15.mjo::u0145':('직접 묘사','반복되는 구체적 접촉의 효과음.','u0144,u0146'),
'masa_15.mjo::u0146':('연결 대사','접촉 위치에 대한 반응으로 장면을 계속 구성. 위치 상세·흥분을 원문 이상으로 확정하지는 않음.','u0145,u0148,u0151'),
'masa_15.mjo::u0148':('연결 대사','진행 중인 접촉의 강도를 조절해 달라는 요청. 자체 새로운 신체 묘사는 없음.','u0145–0146,u0149'),
'masa_15.mjo::u0151':('직접 묘사','앞선 신체 접촉을 구체적으로 회고하고 성인 상대와 비교함.','u0138–0150'),
'masa_16.mjo::u0795':('성적 비교','현재 성인 장면의 접촉 선호를 앞선 아이의 행동과 연결해 부녀가 닮았다고 비교. 일반 외모·성격 유사성 문맥이 아님.','masa_16u0793–0798;masa_15u0138–0141'),
'st_yana.mjo::u0021':('노출 감상 메타 대사','분리된 인라인000265까지 합치면 노출 그림을 보려고 대화창을 계속 지우는 행동을 언급. 아이의 도입부 목욕 장면이 감상 대상으로 연결됨.','inline000265;u0022;startu0344–0415'),
}
assert len(C)==21 and len(H)==16
packets=[load(p) for p in (ROOT/'body-parallel/source').glob('*.json')];units={u['unit']:(p,u) for p in packets for u in p['units']}
records=[]
for uid,targets in T.items():
 p,u=units[uid];fs=[f for f in u['fields'] if f['role']=='text'];assert len(fs)==len(targets),(uid,len(fs),len(targets))
 for f,t in zip(fs,targets):records.append({'id':f['id'],'unit':uid,'source':f['source'],'target':t,'source_sha256':p['source_sha256'],'translator_model':'Codex internal','context':{'source_speaker':u.get('speaker'),'story_phase':u.get('phase'),'evidence':C[uid][1] if uid in C else 'st_gin u0065–0073: human-shaped entity asks interlocutor to give name first; given kana self-label retained phonetically without asserting butterfly species or expanding censored employer','review_reason':C[uid][0] if uid in C else '名前を名乗る response context; preserve ちょう as 초 and Ｊ● exactly. No confirmed parody attribution; none is necessary to retain the stated self-label.'},'provenance':{'root_thread':'01a16283-b393-7dc0-8c83-d3e23a2a2f41','date':'2026-10-23','semantic_author':'primary Codex internal'},'status':'primary_authored_independent_review_pass_with_referent_correction'})
prior=load(ROOT/'translation/recovery-20261023/review.json');retained={x['unit'] for x in prior['decisions'] if x['decision'].startswith('retain_')};assert retained==set(C)|set(H)
decisions=[]
for uid in sorted(retained):
 p,u=units[uid];reason,context=C[uid] if uid in C else (H[uid][1],H[uid][2]);decisions.append({'unit':uid,'decision':'restore_general' if uid in C else 'retain_original','category':'일반 대사·서술' if uid in C else H[uid][0],'reason_ko':reason,'context_ids':context,'source_sha256':p['source_sha256'],'source_field_ids':[f['id'] for f in u['fields'] if f['role']=='text'],'prior_reason_corrected':True})
out=ROOT/'translation/recovery-20261023-review2';out.mkdir(exist_ok=True)
dump(out/'recovered-targets.json',{'translator_model':'Codex internal','records':records,'inline_records':[],'units':list(T),'source_files':{units[k][0]['source_script']:units[k][0]['source_sha256'] for k in T},'restored_general':21,'semantic_resolved':1,'remaining':16,'runtime_verified':False})
dump(out/'review.json',{'translator_model':'Codex internal','reviewed':37,'restored':21,'remaining':16,'semantic_pending_resolved':{'unit':'st_gin.mjo::u0068','old_unaccepted_draft':'나? 나는 나비야','accepted_strategy':'이름을 대라는 앞 문답에 맞춰 음가 초를 보존. 나비라는 생물 종 추정 및 Ｊ● 회사명 확장 제거. 패러디의 외부 출처는 확정되지 않았음.'},'decisions':decisions,'independent_source_reviews':['review_opening_early','review_opening_late'],'native_game_visual_verified':False})
lines=['# 남은37구간 원문·문맥 재검토','', '기존 보류37개 중21개를 일반 대사·서술로 재분류했습니다. 남은16개도 직접 묘사7개, 연결 대사7개, 성적 비교1개, 노출 감상 메타 대사1개로 나누었습니다. 이전에 모두 직접 성적 내용으로 설명한 것은 부정확했습니다.','', '| 안정 ID | 결과 | 원문·앞뒤 문맥 근거 | 인접 구간 |','|---|---|---|---|']
for x in decisions:lines.append('| '+x['unit']+' | '+('복구' if x['decision']=='restore_general' else '원문 유지: '+x['category'])+' | '+x['reason_ko']+' | '+x['context_ids']+' |')
lines+=['','## 의미 미확정1구간','', '`st_gin.mjo::u0068`: `u0065–67`은 인간형 생물과 만나 이름을 먼저 밝히라는 문답입니다. `ちょう`는 명명된 자기 지칭의 소리를 **초**로 보존해 「나? 나는 초야. / 남동생은 Ｊ●에서 일하고 있어.」로 확정했습니다. 앞선 나비 해석은 채택하지 않았고, 가려진 회사명도 그대로 두었습니다. 패러디 출전까지 확인했다고 주장하지 않습니다.','', '구체적 접촉을 다루는 보류 원문은 여기 재인용하지 않았습니다. 각 안정 ID와 원본 해시가 원문 패킷의 위치를 가리킵니다.']
(out/'구간별-재검토.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps({'restored_general':21,'semantic_resolved':1,'fields':len(records),'remaining':16,'path':str(out)},ensure_ascii=False))
