"""Patch only reviewed Unicode installer dialog resources in isolated copies."""
from pathlib import Path
import ast,json,struct,copy,hashlib,ctypes as C,ctypes.wintypes as W,shutil,pefile,datetime
U=Path.cwd().resolve();cat=json.loads((U/'source/installer-ui-catalog.json').read_bytes());O=U/'candidates/installer-ui-v1';assert not O.exists();assert not Path('C:/Users/CadriacLord/Documents/Codex/INCLUDED_USAGE_STOP.json').exists();sha=lambda b:hashlib.sha256(b).hexdigest()
mp={'ファイルのコピー中...':'파일 복사 중...','ｷｬﾝｾﾙ':'취소','ショートカットの作成':'바로 가기 만들기','OK':'확인','デスクトップにショートカットを作成':'바탕 화면에 바로 가기 만들기','インストール先のフォルダの指定':'설치 폴더 지정','次へ':'다음','参照(&B)':'찾아보기(&B)','インストール先フォルダを指定してください':'설치할 폴더를 지정해 주세요.','アンインストールの確認':'삭제 확인','セーブファイルも削除する':'저장 파일도 삭제',' スクリプトエンジン MAJIRO (C) 2004-2005 越畑声太':' 스크립트 엔진 MAJIRO (C) 2004-2005 越畑声太'}
for r in cat['records']:
 s=r['source']
 if s.startswith('デスクトップ上に、'):mp[s]='바탕 화면에 게임 실행용 바로 가기를'+('\\n' if '\\n' in s else '\n')+'만들 수 있습니다.'
 if s.startswith('[参照]ボタンで、'):mp[s]='[찾아보기]에서 기존 폴더를 선택합니다.'+('\\n' if '\\n' in s else '\n')+'[다음]을 누르면 설치를 시작합니다.'
records=[];pending=[]
for r in cat['records']:
 if r['source'] in mp:
  target=mp[r['source']];assert r['source'].count('\n')==target.count('\n') and r['source'].count('\\n')==target.count('\\n');records.append({**r,'target':target,'translator_model':'Codex internal'})
 else:pending.append({**r,'reason':'Source runtime placeholder or control label; initializer/consumer audit required before changing. MAINDIALOG caption may participate in startup window lookup.'})
(U/'translation/installer-ui-ko.json').write_text(json.dumps({'translator_model':'Codex internal','task_id':'01a162df-720c-77d2-96ed-6429e90b3333','records':records,'deferred':pending,'protected_credit':'Author name 越畑声太 retained verbatim; reading not newly inferred.'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8');byid={r['id']:r['target'] for r in records}
module=ast.parse((U/'tools/build_native_ui.py').read_text(encoding='utf-8-sig'));defs=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in ['w','z','val','serialize']];exec(compile(ast.Module(body=defs,type_ignores=[]),'native_resource_serializer','exec'));updates=[];rebuilt=[]
for r in cat['structures']:
 src=Path(next(s['path'] for s in cat['sources'] if s['file']==r['file']));old=src.read_bytes()[r['offset']:r['offset']+r['size']];assert sha(old)==r['sha256'];assert serialize(r['structure'])==old[:r['parsed_bytes']] and not any(old[r['parsed_bytes']:]);d=copy.deepcopy(r['structure']);root=f'{r["file"]}::type{r["type"]}::{r["name"]}::{r["language"]}';ids=[]
 def tr(key,value):
  if key in byid:ids.append(key);return byid[key]
  return value
 if d['kind']=='DIALOG':
  d['caption']=tr(root+'::caption',d['caption'])
  for v in d['controls']:v['text']=tr(root+f'::control:{v["id"]}:{v["index"]}',v['text'])
  if ids and d['font']:d['font']['face']='Malgun Gothic'
 else:
  for i,s in enumerate(d['strings']):d['strings'][i]=tr(root+'::'+str((int(r['name'])-1)*16+i),s)
 if ids:updates.append({'file':r['file'],'type':r['type'],'name':r['name'],'language':r['language'],'bytes':serialize(d),'ids':ids,'source_sha256':sha(old),'structure':d})
K=C.WinDLL('kernel32',use_last_error=True);K.BeginUpdateResourceW.argtypes=[W.LPCWSTR,W.BOOL];K.BeginUpdateResourceW.restype=W.HANDLE;K.UpdateResourceW.argtypes=[W.HANDLE,C.c_void_p,C.c_void_p,W.WORD,C.c_void_p,W.DWORD];K.UpdateResourceW.restype=W.BOOL;K.EndUpdateResourceW.argtypes=[W.HANDLE,W.BOOL];K.EndUpdateResourceW.restype=W.BOOL
O.mkdir();(O/'resources').mkdir()
def resources(p,data):
 out={}
 for tt in p.DIRECTORY_ENTRY_RESOURCE.entries:
  for nn in tt.directory.entries:
   for ll in nn.directory.entries:
    st=ll.data.struct;off=p.get_offset_from_rva(st.OffsetToData);out[(str(tt.name) if tt.name else tt.id,str(nn.name) if nn.name else nn.id,ll.id)]=data[off:off+st.Size]
 return out
for src in cat['sources']:
 inp=Path(src['path']);before=inp.read_bytes();assert sha(before)==src['sha256'];dest=O/src['file'];shutil.copy2(inp,dest);handle=K.BeginUpdateResourceW(str(dest),False);assert handle,C.get_last_error();committed=False
 try:
  for up in updates:
   if up['file']!=src['file']:continue
   nameptr=C.c_wchar_p(up['name']) if isinstance(up['name'],str) else C.c_void_p(up['name']);buf=C.create_string_buffer(up['bytes']);assert K.UpdateResourceW(handle,C.c_void_p(up['type']),C.cast(nameptr,C.c_void_p),up['language'],buf,len(up['bytes'])),C.get_last_error();(O/'resources'/f'{src["file"]}-{up["name"]}.bin').write_bytes(up['bytes'])
  assert K.EndUpdateResourceW(handle,False),C.get_last_error();committed=True
 finally:
  if not committed:K.EndUpdateResourceW(handle,True)
 after=dest.read_bytes();p0=pefile.PE(data=before);p1=pefile.PE(data=after);a=resources(p0,before);b=resources(p1,after);allowed={(v['type'],v['name'],v['language']):v['bytes'] for v in updates if v['file']==src['file']};assert a.keys()==b.keys();assert {k for k in a if a[k]!=b[k]}==set(allowed);assert all(b[k]==v for k,v in allowed.items());assert [s.Name for s in p0.sections]==[s.Name for s in p1.sections];sections=[]
 for v,w in zip(p0.sections,p1.sections):
  same=v.get_data()==w.get_data();assert same or v.Name.rstrip(b'\0')==b'.rsrc';sections.append({'name':v.Name.rstrip(b'\0').decode(),'unchanged':same})
 assert p0.OPTIONAL_HEADER.AddressOfEntryPoint==p1.OPTIONAL_HEADER.AddressOfEntryPoint;imp=lambda p:[(i.dll,[(j.name,j.ordinal,j.address) for j in i.imports]) for i in p.DIRECTORY_ENTRY_IMPORT];assert imp(p0)==imp(p1);rebuilt.append({'file':src['file'],'source_sha256':sha(before),'candidate_sha256':sha(after),'changed_resources':len(allowed),'nonresource_sections':sections,'entrypoint_imports_unchanged':True,'resources_exact_allowlist':True,'untouched_resources_identical':True})
meta=[{k:v for k,v in u.items() if k!='bytes'}|{'output_sha256':sha(u['bytes'])} for u in updates];m={'translator_model':'Codex internal','task_id':'01a162df-720c-77d2-96ed-6429e90b3333','files':rebuilt,'semantic_fields':len(records),'resources_changed':len(updates),'updates':meta,'deferred_fields':len(pending),'dialog_font':'Malgun Gothic 9pt','source_control_rectangles_and_ids_unchanged':True,'structural_pass':True,'layout_visual_pass':False,'runtime_pass':False,'installer_executed':False,'defender_scan_pending':True,'release_ready':False,'scope':'Static resource subset only. Dynamic captions/messages, launcher buttons, title lookup and actual installation/uninstall flow remain unaudited.'};(O/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'fields':len(records),'deferred_fields':len(pending),'resources':len(updates),'files':rebuilt},ensure_ascii=False))
