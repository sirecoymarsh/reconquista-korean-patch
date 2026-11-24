"""Source-bound offline 4x assets. Original runtime archives remain immutable."""
from pathlib import Path
import sys,struct,json,hashlib,zlib,functools,subprocess,time,os,argparse
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'));from inspect_majiro import Arc
sys.path.insert(0,str(ROOT/'ui-opening-ending/tools'));from raster_codec import raw_image
OUT=ROOT/'candidates/hires-v1'; STYLE=OUT/'style'; RUNTIME=ROOT/'runtime-body-ui-20261023-v9'
STOP=Path(r'C:\Users\CadriacLord\Documents\Codex\INCLUDED_USAGE_STOP.json')
MODELROOT=Path('P:/AI/Codex/projects/image-upscaling-tools/apps/Upscayl-2.15.0/resources')
MODEL='high-fidelity-4x'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def checked():
 if STOP.exists():raise SystemExit('Included usage stop marker exists; local batch stopped.')
def inventory():
 table={};selected={}
 for arcn in ['slowdata.arc','data.arc','data1.arc','data2.arc','fastdata.arc']:
  a=Arc(RUNTIME/arcn)
  for e in a.entries:
   if e['name'].endswith(('.rct','.rc8')):
    key=e['name'].lower();table[key]=(a.path,e)
    if arcn in ['data.arc','data1.arc','data2.arc'] and e['name'].endswith('.rct'):
     with a.path.open('rb') as f:f.seek(e['offset']);head=f.read(20)
     w,h=struct.unpack_from('<II',head,8)
     if w>=400 and h>=400:selected[key]={'name':e['name'],'archive':arcn,'size':[w,h]}
 return table,selected
TABLE,SELECTED=inventory()
@functools.lru_cache(maxsize=100)
def decode(name):
 name=name.lower()
 if not name.endswith(('.rct','.rc8')):name+='.rct'
 path,e=TABLE[name]
 with path.open('rb') as f:f.seek(e['offset']);blob=f.read(e['size'])
 a,head,c=raw_image(blob)
 if blob[4:8]==b'TC01':
  base=head[22:].rstrip(b'\0').decode('cp932').lower();ba=decode(base);skip=np.all(a==[255,0,0],axis=2);a[skip]=ba[skip]
 return a

def run():
 checked();(OUT/'assets').mkdir(parents=True,exist_ok=True);(OUT/'batch-input').mkdir(exist_ok=True)
 manifest=OUT/'assets.json';old=json.loads(manifest.read_text('utf-8')) if manifest.exists() else {'model':MODEL,'model_sha256':sha(MODELROOT/'models'/f'{MODEL}.bin'),'scale':4,'entries':{},'status':'building','prior_game_unchanged':True}
 entries=old['entries']; keys={}
 for n,row in SELECTED.items():
  key=f'{zlib.crc32(n.encode("cp932")):08x}'
  assert key not in keys or keys[key]==n;keys[key]=n;row['key']=key
 todo=[n for n in sorted(SELECTED) if n not in entries]
 for begin in range(0,len(todo),32):
  checked();batch=todo[begin:begin+32];inputdir=OUT/'batch-input'
  # Remove only the exact prior batch's generated PNGs, within the resolved project candidate.
  for f in inputdir.glob('*.png'):f.unlink()
  for n in batch:
   row=SELECTED[n];a=decode(n);Image.fromarray(a).save(inputdir/(row['key']+'.png'))
  log=OUT/f'upscale-{len(entries):04d}.log';started=time.time()
  cmd=[str(MODELROOT/'bin/upscayl-bin.exe'),'-i',str(inputdir),'-o',str(OUT/'assets'),'-n',MODEL,'-m',str(MODELROOT/'models'),'-s','4','-t','256','-j','1:1:1','-f','png']
  env=os.environ.copy();env['TEMP']=env['TMP']=str(ROOT/'temp')
  with log.open('w',encoding='utf-8') as f:subprocess.run(cmd,cwd=OUT,stdout=f,stderr=f,check=True,creationflags=0x08000000,env=env)
  for n in batch:
   row=SELECTED[n].copy();fn=row['key']+'.png';op=OUT/'assets'/fn
   with Image.open(op) as im:assert im.size==tuple(x*4 for x in row['size']);im.verify()
   row.update(file=fn,sha256=sha(op),source_pixels_sha256=hashlib.sha256(decode(n).tobytes()).hexdigest(),source_archive_payload_sha256=None)
   path,e=TABLE[n]
   with path.open('rb') as f:f.seek(e['offset']);row['source_archive_payload_sha256']=hashlib.sha256(f.read(e['size'])).hexdigest()
   entries[n]=row
  old.update(status='building',completed=len(entries),total=len(SELECTED),last_batch_seconds=round(time.time()-started,2));dump(manifest,old)
  print(json.dumps({k:old[k] for k in ['completed','total','last_batch_seconds']}),flush=True)
 old.update(status='complete',completed=len(entries),total=len(SELECTED));dump(manifest,old)
if __name__=='__main__':run()
