from pathlib import Path
import json,re,shutil,hashlib
from fontTools.ttLib import TTFont
U=Path.cwd();O=U/'candidates/opening-video-ko-v3';O.mkdir(exist_ok=True)
for k in ['subtitles','evidence','preview','build-source','payloads/movie','fonts']:(O/k).mkdir(parents=True,exist_ok=True)
N=[('まきいづみ','마키 이즈미','まきいづみ','source kana'),('芝原のぞみ','시바하라 노조미','しばはらのぞみ','https://myoji.jitenon.jp/content/芝原'),('羽沢月乃','하자와 쓰키노','はざわつきの','https://days366.com/title/31_06_01_177.html'),('北都南','호쿠토 미나미','ほくとみなみ','https://www.animecharactersdatabase.com/characters.php?id=840'),('青山ゆかり','아오야마 유카리','あおやまゆかり','source credit; established credited-stage-name reading'),('如月葵','기사라기 아오이','きさらぎあおい','https://www.hermit-game.com/h02/'),('一色ヒカル','잇시키 히카루','いっしきひかる','source credit; established credited-stage-name reading'),('松田理沙','마쓰다 리사','まつだりさ','source credit; established credited-stage-name reading'),('飛蘭','페이란','フェイラン','https://faylan.jp/biography.html'),('海富一','우나토미 하지메','HAJIME UNATOMI','original OP 14s Roman credit'),('上松範康','아게마쓰 노리야스','Noriyasu Agematsu','https://www.ariamusic.co.jp/creators/agematsu.php'),('菊田大介','기쿠타 다이스케','Daisuke Kikuta','https://www.ariamusic.co.jp/creators/kikuta.php'),('加納望','가노 노조무','KANOW NOZOMU','https://no3guitar.com/'),('森琢哉','모리 다쿠야','Takuya Mori','https://www.kenichi-m.com/ghcd-3025/'),('神月社','간즈키 야시로','Kanzuki Yashiro','https://mjuz-dept.com/web/'),('朋子','도모코','ともこ','https://www.animecharactersdatabase.com/characters.php?id=640; existing accepted central session-3 terminology')]
names=[{'source':a,'target':b,'reading':c,'evidence':d,'translator_model':'Codex internal'} for a,b,c,d in N]
(O/'name-readings.json').write_text(json.dumps({'translator_model':'Codex internal','scope':'Opening visible names only; credited aliases preserved; no performer identity substitution','records':names},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
j=json.loads((U/'translation/opening-credits-ko.json').read_text(encoding='utf-8'))
for r in j['records']:
 for a,b,_,_ in N:r['target']=r['target'].replace(a,b)
 r['translator_model']='Codex internal'
 r['v3_evidence']='name-readings.json; source movie visual audit; original frozen approved caption translation reused'
j['unresolved_name_span']=None;j['revision']='v3 all Japanese names localized; no external semantic model'
(O/'opening-credits-ko.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
s=(U/'candidates/opening-video-ko-v2/subtitles/opening-ko.ass').read_text(encoding='utf-8');rows=[];lookup={r['id']:r for r in j['records']}
for line in s.splitlines():
 if line.startswith('Dialogue:'):
  fields=line.split(',',9);uid=fields[4]
  if uid in lookup:
   size=re.match(r'\{\\fs(\d+)\}',fields[9]).group(1);fields[9]='{\\fs'+size+'}'+lookup[uid]['target'].replace('\n','\\N');line=','.join(fields)
 rows.append(line)
# Long names: keep theme credit in four short lines? Top bar is only 72px; use two balanced lines at 19px.
s='\n'.join(rows)+'\n';s=s.replace('{\\fs22}주제가 「Reconquista」','{\\fs19}주제가 「Reconquista」')
(O/'subtitles/opening-ko.ass').write_text(s,encoding='utf-8')
font=U/'research/typography/fonts/Eulyoo1945-SemiBold.otf';shutil.copy2(font,O/'fonts'/font.name)
cm=TTFont(font).getBestCmap();missing=sorted({c for r in j['records'] for c in r['target'] if not c.isspace() and ord(c) not in cm});assert not missing,missing
assert not re.search(r'[\u3040-\u30ff\u3400-\u9fff]',s)
report={'semantic_targets':len(j['records']),'replaced_name_mappings':len(N),'translator_model':'Codex internal','font_missing_codepoints':missing,'residual_Japanese_in_ASS':0,'state':'semantic authoring complete; visual/video work pending','runtime':'user-owned; not executed'}
(O/'evidence/semantic-gate.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,ensure_ascii=False))