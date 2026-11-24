from pathlib import Path
import sys,ast,json,struct,hashlib,pefile
U=Path.cwd().resolve();tree=ast.parse((U/'tools/audit_pe_ui.py').read_text(encoding='utf-8-sig'));node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='R');exec(compile(ast.Module(body=[node],type_ignores=[]),'R','exec'));sha=lambda b:hashlib.sha256(b).hexdigest();out={'sources':[],'records':[],'structures':[],'translator_model':'Codex internal'}
for name in ['setup.exe','install.exe']:
 path=U.parent/'research/disc'/name;blob=path.read_bytes();pe=pefile.PE(data=blob);out['sources'].append({'file':name,'path':str(path),'sha256':sha(blob)})
 for typ in pe.DIRECTORY_ENTRY_RESOURCE.entries:
  if typ.id not in [5,6]:continue
  for nm in typ.directory.entries:
   rname=str(nm.name) if nm.name else nm.id
   for lang in nm.directory.entries:
    rs=lang.data.struct;offset=pe.get_offset_from_rva(rs.OffsetToData);b=blob[offset:offset+rs.Size];r=R(b);root=f'{name}::type{typ.id}::{rname}::{lang.id}'
    def add(key,text,role):
     if isinstance(text,str) and text:out['records'].append({'id':root+'::'+key,'source':text,'role':role,'resource_sha256':sha(b)})
    if typ.id==5:
     assert b[:4]!=b'\x01\x00\xff\xff';style,ex,count,x,y,w,h=r.unpack('<IIHhhhh');menu=r.value();cls=r.value();caption=r.string();add('caption',caption,'dialog_caption');font={'points':r.word(),'face':r.string()} if style&64 else None;controls=[]
     for i in range(count):
      r.align();st,es,xx,yy,ww,hh,cid=r.unpack('<IIhhhhH');cl=r.value();txt=r.value();add(f'control:{cid}:{i}',txt,'control_text');size=r.word();extra=b[r.p:r.p+size];r.p+=size;controls.append({'index':i,'id':cid,'style':st,'exstyle':es,'rect':[xx,yy,ww,hh],'class':cl,'text':txt,'extra':extra.hex()})
     data={'kind':'DIALOG','style':style,'exstyle':ex,'rect':[x,y,w,h],'menu':menu,'class':cls,'caption':caption,'font':font,'controls':controls}
    else:
     values=[]
     for i in range(16):
      size=r.word();text=b[r.p:r.p+2*size].decode('utf-16-le');r.p+=2*size;values.append(text);add(str((int(rname)-1)*16+i),text,'stringtable')
     data={'kind':'STRING','strings':values}
    assert r.p==len(b) or not any(b[r.p:]);out['structures'].append({'file':name,'type':typ.id,'name':rname,'language':lang.id,'offset':offset,'size':len(b),'parsed_bytes':r.p,'sha256':sha(b),'structure':data})
(U/'source/installer-ui-catalog.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('Fields',len(out['records']),'resources',len(out['structures']))
for r in out['records']:
 if r['id'].startswith('setup.exe'):print(r['id'],repr(r['source']))
