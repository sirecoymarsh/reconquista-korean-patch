from pathlib import Path
import json,re,urllib.request,zipfile,io,shutil,subprocess,hashlib
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
U=Path.cwd(); R=U/'research/typography'; R.mkdir(parents=True,exist_ok=True)
fonts=R/'fonts';fonts.mkdir(exist_ok=True)
url='https://www.eulyoo.co.kr/board/down.php?file_name=eulyoo1945font.zip&file_save_name=eulyoo1945font.zip'
zpath=R/'eulyoo1945font.zip'
if not zpath.exists():zpath.write_bytes(urllib.request.urlopen(url,timeout=30).read())
with zipfile.ZipFile(zpath) as z:
 for n in z.namelist():
  if n.lower().endswith('.otf') and '/__MACOSX/' not in '/'+n and not Path(n).name.startswith('._'):
   (fonts/Path(n).name).write_bytes(z.read(n))
for name in ['MaruBuri-SemiBold.ttf','MaruBuri-Bold.ttf']:
 p=fonts/name
 if not p.exists():p.write_bytes(urllib.request.urlopen('https://hangeul.pstatic.net/hangeul_static/webfont/MaruBuri/'+name,timeout=30).read())
for name,url in [('eulyoo-license.html','https://www.eulyoo.co.kr/member/font.html'),('naver-license.html','https://hangeul.naver.com/font')]:
 p=R/name
 if not p.exists():p.write_bytes(urllib.request.urlopen(url,timeout=30).read())
p=fonts/'NotoSerifKR-SemiBold.ttf'
if not p.exists():
 f=TTFont('C:/Windows/Fonts/NotoSerifKR-VF.ttf');f=instantiateVariableFont(f,{'wght':600},inplace=True);f['OS/2'].usWeightClass=600
 for nid,s in [(1,'Reconquista Noto Serif Review'),(2,'Regular'),(4,'Reconquista Noto Serif Review'),(6,'ReconquistaNotoSerifReview')]:
  f['name'].setName(s,nid,3,1,0x409);f['name'].setName(s,nid,1,0,0)
 for nid in [16,17]:
  f['name'].names=[n for n in f['name'].names if n.nameID!=nid]
 f.save(p)
info=[]
for p in fonts.glob('*'):
 f=TTFont(p);names={nid:next((n.toUnicode() for n in f['name'].names if n.nameID==nid and n.langID==1033),None) for nid in [1,2,4,6]};info.append({'file':p.name,'names':names,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'cmap':len(f.getBestCmap())})
(R/'font-inventory.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
logo=U/'candidates/brand-logo-ko-v1';logo.mkdir(exist_ok=True)
for d in ['master','preview','clean','layers','masks','payloads']:(logo/d).mkdir(exist_ok=True)
shutil.copy2(Path('P:/AI/Codex/generated_images/01a162df-720c-77d2-96ed-6429e90b3333/exec-ec279989-f51b-4645-9e7c-86a2b34e5591.png'),logo/'master/reconquista-ko.png')
print(json.dumps({'font_inventory':info,'logo_master':str(logo/'master/reconquista-ko.png')},ensure_ascii=False))
