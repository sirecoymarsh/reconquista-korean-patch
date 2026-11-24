"""Primary-authored directed-voice context; display/internal tokens remain separate."""
def context(prefix,n,u):
 token=u['speaker'];source=''.join(f['source'] for f in u['fields'] if f['role']=='text')
 common={'story_phase':prefix,'source_display_token':token,'evidence':'source unit and adjacent scene, primary Codex review 2026-10-22'}
 if prefix=='opening':
  scenes=[(19,'prologue'),(169,'arrival_bus_and_crossing'),(194,'apartment_approach'),(283,'masaki_introduction'),(339,'new_home_and_photo'),(421,'father_daughter_bath'),(480,'grandfather_visit'),(518,'adult_conversation'),(575,'night_walk_and_novelist_past'),(619,'song_memory_and_black_clad_girl')]
  scene=next(label for last,label in scenes if n<=last)
  if n in [593,595,597]:return {**common,'scene':scene,'speaker_identity':'가창자 미표기','addressees':[],'text_function':'lyric','voice':'회상 장면의 가사; 원문에 화자가 명시되지 않아 특정하지 않음'}
  if not token:return {**common,'scene':scene,'speaker_identity':'마키노','addressees':[],'text_function':'narration','voice':'담백한 1인칭 서술'}
  if '暮葉' in token:sp='쿠레하'
  elif '麻咲' in token:sp='마사키'
  elif '紅葉' in token:sp='모미지(아내)'
  elif 'もみじ' in token:sp='모미지(딸)'
  elif token=='義父' or n==435:sp='장인'
  elif token=='槙野' or n>19:sp='마키노'
  else:sp='정체불명 상대'
  fn='dialogue';recipient=[];voice=''
  if n<=19:
   recipient=['정체불명 상대' if sp=='쿠레하' else '쿠레하'];voice='차분한 반말' if sp=='쿠레하' else '담담한 존댓말'
  elif 583<=n<=598 and (sp in ['쿠레하','모미지(딸)','모미지(아내)']):
   fn='quoted_lyric' if sp!='쿠레하' else 'lyric';voice='반복 가사 기준어'
  elif sp=='마키노':
   if n==337:recipient=['모미지(아내)의 사진'];voice='추억 속 아내에게 친근한 반말'
   elif n==329:recipient=['모미지(딸)','모미지(아내)의 사진'];voice='딸에게 대답한 뒤 사진 속 아내에게 사과; 둘 다 친근한 반말'
   elif n==613:recipient=['쿠레하'];voice='아내로 착각한 이름 부름'
   elif '（' in source or n in [145,148,285,302,423,431,570,576,580,584,588,599,602,607]:fn='aside';voice='자기 말/독백'
   elif 195<=n<=283 and n not in [261,265,267]:recipient=['마사키'];voice='첫 인사 정중체에서 친근한 어른 반말로 전환'
   elif 434<=n<=575 and n not in [446,457,473,487]:recipient=['장인'];voice='아버님, 존댓말'
   else:recipient=['모미지(딸)'];voice='다정한 아버지 반말'
   if n in [379,381,385]:voice='딸에게 미용사 흉내를 내는 장난스러운 존댓말'
  elif sp=='모미지(딸)':
   if n==332:recipient=['모미지(아내)의 사진'];voice='엄마 사진에 말하는 어린이 반말'
   elif n in [217,219,221,253,255,270,281]:recipient=['마사키'];voice='마사키 언니, 친근한 반말'
   elif n in [447,449,451,471,474,476]:recipient=['장인'];voice='할아버지에게 어린이 반말'
   elif n==239:recipient=['마키노','마사키'];voice='엘리베이터 안내 흉내'
   else:recipient=['마키노'];voice='아빠에게 밝은 어린이 반말'
   if n==217:voice='처음 만난 언니에게 공손한 자기소개'
  elif sp=='마사키':
   if n in [218,220,222,254,256]:recipient=['모미지(딸)'];voice='동생을 대하는 반말'
   elif n in [238,269,282]:recipient=['마키노','모미지(딸)'];voice='아버지에게 존댓말, 아이에게 반말; 238은 안내 흉내'
   else:recipient=['마키노'];voice='마키노 아저씨, 친근한 존댓말'
  elif sp=='장인':
   if n in [448,450,472,475,477]:recipient=['모미지(딸)'];voice='손녀에게 다정한 반말'
   else:recipient=['마키노'];voice='게이고 군/자네, 온화한 하게체'
  elif sp=='쿠레하':recipient=['마키노'];voice='침묵과 반응, 이름 공개 전'
 else:
  if 298<=n<=373:
   scene='school_gate_shiina_introduction'
   if not token:return {**common,'scene':scene,'speaker_identity':'신야','addressees':[],'text_function':'narration','voice':'가볍고 빈정거리는 1인칭; 시이나와 마호코의 반응을 대비'}
   sp='시이나' if '詩菜' in token else '마호코' if '真帆子' in token else '신야'
   if sp=='시이나':
    to_maho=n in [300,319,346,369]
    recipient=['마호코' if to_maho else '신야'];voice='마호코 언니, 다정하고 부드러운 존댓말' if to_maho else '선배, 냉담하고 가시 돋친 존댓말'
   elif sp=='마호코':
    recipient=['시이나'] if n in [299,316,345] else ['신야','시이나'] if n in [352,356,370] else ['신야']
    voice='부드러운 반말; 신야에게는 신 애칭; 시이나에게는 이름'
   else:
    recipient=['시이나'] if n in [303,306,308,310,337,341,344,348,359,361,363,366,367] else ['마호코']
    voice='친근하거나 불평하는 반말; 시이나에게 짓궂은 선배'
   return {**common,'scene':scene,'speaker_identity':sp,'addressees':recipient,'text_function':'dialogue','voice':voice}
  scene='morning_alone' if n<=51 else 'breakfast_and_childhood_friend' if n<=179 else 'walk_to_school'
  if not token:return {**common,'scene':scene,'speaker_identity':'신야','addressees':[],'text_function':'narration','voice':'가볍고 빈정거리는 청년 1인칭'}
  sp='마호코 어머니' if 'ママ' in token else '마호코' if ('真帆子' in token or 'まほほ' in token) else '신야'
  fn='dialogue';recipient=[];voice=''
  if sp=='신야':
   if n<=51 or n in [55,140,276] or '（' in source:fn='aside';voice='편한 독백/극중 혼잣말'
   elif n in [61,64,109,113,119,123,126,133,135,144,165]:recipient=['마호코 어머니'];voice='아주머니, 친근한 존댓말'
   else:recipient=['마호코'];voice='소꿉친구 반말; 장난스러운 말투'
   if n in [161,194]:voice='소꿉친구에게 장난스럽게 높여 말함'
  elif sp=='마호코 어머니':
   recipient=['마호코'] if n==162 else ['신야'];voice='아이를 돌보는 어른의 반말'
  else:
   recipient=['마호코 어머니'] if n==146 else ['신야'];voice='부드러운 반말; 신 애칭, 말끝 늘임'
   if n<=103:voice='잠 덜 깬 발음/침묵; 마호호는 의도된 오류'
 return {**common,'scene':scene,'speaker_identity':sp,'addressees':recipient,'text_function':fn,'voice':voice}
