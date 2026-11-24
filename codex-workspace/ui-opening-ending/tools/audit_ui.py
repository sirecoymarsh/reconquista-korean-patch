from pathlib import Path
import json,sys,hashlib,collections,re,io
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT.parent
sys.path.insert(0,str(BASE/'tools'))
from inspect_majiro import Arc
sys.path.insert(0,str(BASE/'research/vendor/majiro-py/src'))
from mjotool import MjoScript
FILES={'buttonmenu.mjo','start.mjo','console.mjo','config.mjo','pausemenu.mjo','cgmode.mjo','load_sysdata.mjo','message_box.mjo','loadsave.mjo','menu.mjo','history.mjo','music.mjo','chronicle.mjo','staffroom.mjo','staffroll.mjo','sightchange.mjo','transit_top.mjo','c_setumei.mjo'}
def sha(b):return hashlib.sha256(b).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
keys=set(); images=[]
for p in (BASE/'reports/archive_inventory').glob('*.json'):
 a=json.loads(p.read_text(encoding='utf-8'))
 for e in a['entries']:
  keys.update([e['name'],Path(e['name']).stem])
  if p.stem=='fastdata' and Path(e['name']).suffix in ['.rct','.rc8']:
   b=(BASE/'research/extracted/fastdata'/e['name']).read_bytes()
   import struct
   w,h=struct.unpack_from('<II',b,8)
   images.append({'id':f"fastdata.arc::{e['name']}",'file':e['name'],'sha256':sha(b),'header':b[:20].hex(),'signature':b[4:8].decode('ascii'),'width':w,'height':h,'role':'credits_pending' if e['name'].startswith('staffroll') else 'ui_audit_pending','status':'source_verified'})
records=[]; excluded=[];counts=collections.Counter()
for f in sorted(FILES):
 b=(BASE/'research/extracted/scenario'/f).read_bytes()
 s=MjoScript.disassemble_script(io.BytesIO(b))
 for i,x in enumerate(s.instructions):
  if x.string is None or x.opcode.mnemonic=='ctrl':continue
  t=x.string;row={'id':f'{f}::{i:06d}','archive':'scenario.arc','entry':f,'instruction_index':i,'offset':x.offset,'source':t,'opcode':x.opcode.mnemonic,'source_sha256':sha(b),'context':[z.format_instruction() for z in s.instructions[max(0,i-3):i+6]],'status':'consumer_audit_pending'}
  if t in keys:row['reason']='exact_archive_resource_key';excluded.append(row)
  elif not re.search('[\u3040-\u30ff\u3400-\u9fff]',t):row['reason']='ascii_or_empty_requires_display_audit';excluded.append(row)
  else:records.append(row);counts[f]+=1
raster_refs={}
for row in records+excluded:
 t=row['source']
 if t in keys:raster_refs.setdefault(t,[]).append(row['id'])
for im in images:im['consumers']=raster_refs.get(Path(im['file']).stem,[])
dump(ROOT/'source/ui-string-candidates.json',{'source':'existing extracted original MJO','records':records,'excluded':excluded,'counts':counts})
dump(ROOT/'source/raster-inventory.json',{'images':images,'count':len(images),'format_counts':collections.Counter(i['signature'] for i in images)})
surfaces=[{'id':i,'status':'pending','source':s,'static_pass':False,'runtime_pass':False} for i,s in [('UI-TITLE','start.mjo + title*'),('UI-CONFIG','config.mjo/config.cfg + config_*'),('UI-SAVELOAD','loadsave.mjo/loadsave.cfg + sl_*'),('UI-HISTORY','history.mjo/history.cfg'),('UI-MENU','console/buttonmenu/menu/pausemenu + console/submenu'),('UI-MODAL','message_box.mjo/messagebox.cfg + askyesno_base'),('UI-EXTRA','cgmode/music/chronicle/staffroom/c_setumei/sightchange'),('UI-PE','main EXE, setup.exe, install.exe'),('UI-RASTER','source/raster-inventory.json'),('OP','movie/Recon_OP800_H.mpg'),('ED','staffroll.mjo/staffrolla/staffrollb_001..011; audio consumer pending')]]
dump(ROOT/'surface_inventory.json',{'translator_model':'Codex internal','surfaces':surfaces})
print('UI_CANDIDATES',len(records),dict(counts));print('RASTER',len(images),dict(collections.Counter(i['signature'] for i in images)))
for x in records:
 if x['entry']!='c_setumei.mjo':print(x['id'],json.dumps(x['source'],ensure_ascii=False))
