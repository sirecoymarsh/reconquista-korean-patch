"""Build UTF-16 UI resources in a dedicated EXE copy; code/imports remain exact."""
from pathlib import Path
import json,struct,copy,hashlib,ctypes as C,ctypes.wintypes as W,shutil,pefile
U=Path('P:/AI/Codex/projects/reconquista-ko/ui-opening-ending').resolve();B=U.parent
source=B/'research/disc/bin/レコンキスタ.exe';blob=source.read_bytes();sha=lambda b:hashlib.sha256(b).hexdigest();assert sha(blob)=='cd1c38ac20d9e502fbc58b7392ca77ec32e3d56f90d988580a3cf58cb6f95146'
cat=json.loads((U/'source/pe-visible-catalog.json').read_text(encoding='utf-8'));trans=json.loads((U/'translation/native-ui-ko.json').read_text(encoding='utf-8'));mp={r['id']:r['target'] for r in trans['records']}
tree=json.loads((U/'evidence/pe-resources-original.json').read_text(encoding='utf-8'))['normalized_result']['resources'];byidx={e['index']:e for e in tree}
def w(n):return struct.pack('<H',n)
def z(s):return s.encode('utf-16-le')+b'\0\0'
def val(v):return w(0xffff)+w(v['ordinal']) if isinstance(v,dict) else z(v)
def serialize(d):
 k=d['kind']
 if k=='MENU':
  def walk(items):
   out=b''
   for it in items:
    out+=w(it['flags'])+(b'' if it['flags']&16 else w(it['id']))+z(it['text'])
    if it['flags']&16:out+=walk(it['children'])
   return out
  return b'\0'*4+walk(d['items'])
 if k=='STRING':return b''.join(w(len(s.encode('utf-16-le'))//2)+s.encode('utf-16-le') for s in d['strings'])
 out=struct.pack('<IIHhhhh',d['style'],d['exstyle'],len(d['controls']),*d['rect'])+val(d['menu'])+val(d['class'])+z(d['caption'])
 if d['font']:out+=w(d['font']['points'])+z(d['font']['face'])
 for it in d['controls']:
  out+=b'\0'*((-len(out))%4)
  extra=bytes.fromhex(it['extra']);out+=struct.pack('<IIhhhhH',it['style'],it['exstyle'],*it['rect'],it['id'])+val(it['class'])+val(it['text'])+w(len(extra))+extra
 return out
updates=[]
for rec in cat['structures']:
 e=byidx[rec['index']];loc=e['payload']['location'];old=blob[loc['offset']:loc['offset']+loc['bytes']];base=serialize(rec['structure']);assert base==old[:rec['parsed_bytes']] and not any(old[len(base):]),rec['name']
 d=copy.deepcopy(rec['structure']);root=f"pe::type{rec['type']}::{rec['name']}";changed=[]
 def tr(key,s):
  if key in mp:changed.append(key);return mp[key]
  return s
 if d['kind']=='MENU':
  def walk(items,path=''):
   for i,it in enumerate(items):
    key=path+str(i);it['text']=tr(root+'::'+key,it['text'])
    if 'children' in it:walk(it['children'],key+'/')
  walk(d['items'])
 elif d['kind']=='DIALOG':
  d['caption']=tr(root+'::caption',d['caption'])
  for it in d['controls']:it['text']=tr(root+f"::control:{it['id']}:{it['index']}",it['text'])
  if changed and d['font']:d['font']['face']='Malgun Gothic'
  if rec['name'] in ('SCREENOPTION','SCREENOPTION_FULL'):
   ix=3 if rec['name']=='SCREENOPTION' else 4; assert d['controls'][ix]['rect']==[0,10 if ix==3 else 35,45,15];d['controls'][ix]['rect'][2]=49
  if rec['name'] in ('SPEEDCONFIG','SPEEDCONFIG_ORG'):
   assert d['controls'][4]['rect']==[5,35,30,10];d['controls'][4]['rect'][2]=35
 else:
  for i,s in enumerate(d['strings']):d['strings'][i]=tr(root+'::'+str((int(rec['name'])-1)*16+i),s)
 if changed:updates.append({'meta':e,'data':serialize(d),'ids':changed,'source_sha256':sha(old)})
O=U/'candidates/native-ui-v2';O.mkdir(exist_ok=True);out=O/'レコンキスタ.exe';shutil.copy2(source,out)
K=C.WinDLL('kernel32',use_last_error=True);K.BeginUpdateResourceW.argtypes=[W.LPCWSTR,W.BOOL];K.BeginUpdateResourceW.restype=W.HANDLE;K.UpdateResourceW.argtypes=[W.HANDLE,C.c_void_p,C.c_void_p,W.WORD,C.c_void_p,W.DWORD];K.UpdateResourceW.restype=W.BOOL;K.EndUpdateResourceW.argtypes=[W.HANDLE,W.BOOL];K.EndUpdateResourceW.restype=W.BOOL
handle=K.BeginUpdateResourceW(str(out),False);assert handle,C.get_last_error();committed=False
try:
 for up in updates:
  e=up['meta'];name=e['name'].get('name',e['name'].get('id'));nameptr=C.c_wchar_p(name) if isinstance(name,str) else C.c_void_p(name);buf=C.create_string_buffer(up['data'])
  assert K.UpdateResourceW(handle,C.c_void_p(e['type']['id']),C.cast(nameptr,C.c_void_p),e['language']['id'],buf,len(up['data'])),C.get_last_error()
 assert K.EndUpdateResourceW(handle,False),C.get_last_error();committed=True
finally:
 if not committed:K.EndUpdateResourceW(handle,True)
new=out.read_bytes();p0=pefile.PE(data=blob);p1=pefile.PE(data=new)
def resources(p,data):
 result={}
 for t in p.DIRECTORY_ENTRY_RESOURCE.entries:
  for n in t.directory.entries:
   for l in n.directory.entries:
    x=l.data.struct;o=p.get_offset_from_rva(x.OffsetToData);result[(t.id,str(n.name) if n.name else n.id,l.id)]=data[o:o+x.Size]
 return result
rs0=resources(p0,blob);rs1=resources(p1,new);assert rs0.keys()==rs1.keys()
allowed={(u['meta']['type']['id'],u['meta']['name'].get('name',u['meta']['name'].get('id')),u['meta']['language']['id']):u['data'] for u in updates}
assert {k for k in rs0 if rs0[k]!=rs1[k]}==set(allowed)
assert all(rs1[k]==v for k,v in allowed.items())
sections=[]
assert [s.Name for s in p0.sections]==[s.Name for s in p1.sections]
for a,b in zip(p0.sections,p1.sections):
 name=a.Name.rstrip(b'\0').decode();same=a.get_data()==b.get_data()
 if name!='.rsrc':assert same,name
 sections.append({'name':name,'bytes_identical':same,'original_sha256':sha(a.get_data()),'candidate_sha256':sha(b.get_data())})
assert p0.OPTIONAL_HEADER.AddressOfEntryPoint==p1.OPTIONAL_HEADER.AddressOfEntryPoint
assert [(i.dll,[(j.name,j.ordinal,j.address) for j in i.imports]) for i in p0.DIRECTORY_ENTRY_IMPORT]==[(i.dll,[(j.name,j.ordinal,j.address) for j in i.imports]) for i in p1.DIRECTORY_ENTRY_IMPORT]
manifest={'translator_model':'Codex internal','source_exe_sha256':sha(blob),'candidate_sha256':sha(new),'translation_sha256':sha((U/'translation/native-ui-ko.json').read_bytes()),'semantic_fields':sum(len(u['ids']) for u in updates),'changed_resource_count':len(updates),'resource_key_set_preserved':True,'untouched_resources_identical':True,'entrypoint_imports_identical':True,'sections':sections,'changed_resources':[{'type':u['meta']['type'],'name':u['meta']['name'],'language':u['meta']['language'],'source_sha256':u['source_sha256'],'output_sha256':sha(u['data']),'ids':u['ids']} for u in updates],'native_dialog_font':'Malgun Gothic 9pt','layout_changes':[{'resources':['SCREENOPTION','SCREENOPTION_FULL'],'label':'전체 화면 모드','width_dlu':[45,49],'following_control_x':50},{'resources':['SPEEDCONFIG','SPEEDCONFIG_ORG'],'label':'글자 표시','width_dlu':[30,35],'following_control_x':45}],'runtime_pass':False,'defender_scan_pending':True,'status':'static_resource_patch_pass_runtime_pending'}
(O/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:manifest[k] for k in ['semantic_fields','changed_resource_count','candidate_sha256','status']},ensure_ascii=False))
