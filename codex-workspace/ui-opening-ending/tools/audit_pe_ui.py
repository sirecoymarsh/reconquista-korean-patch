from pathlib import Path
import json,struct,hashlib
U=Path(r'P:\AI\Codex\projects\reconquista-ko\ui-opening-ending').resolve();B=U.parent
blob=(B/'research/disc/bin/レコンキスタ.exe').read_bytes();tree=json.loads((U/'evidence/pe-resources-original.json').read_text(encoding='utf-8'))
class R:
 def __init__(self,b):self.b=b;self.p=0
 def unpack(self,f):v=struct.unpack_from(f,self.b,self.p);self.p+=struct.calcsize(f);return v
 def word(self):return self.unpack('<H')[0]
 def align(self):self.p=(self.p+3)&~3
 def string(self):
  start=self.p
  while self.word():pass
  return self.b[start:self.p-2].decode('utf-16-le')
 def value(self):
  n=struct.unpack_from('<H',self.b,self.p)[0]
  if n==0xffff:self.p+=2;return {'ordinal':self.word()}
  return self.string()
rows=[];structures=[]
for e in tree['normalized_result']['resources']:
 typ=e['type']['id']
 if typ not in [4,5,6]:continue
 loc=e['payload']['location'];b=blob[loc['offset']:loc['offset']+loc['bytes']];r=R(b);name=str(e['name'].get('name',e['name'].get('id')));root=f'pe::type{typ}::{name}'
 def add(path,text,role):
  if isinstance(text,str) and text:rows.append({'id':root+'::'+path,'source':text,'role':role,'resource_index':e['index'],'resource_sha256':e['payload']['sha256'],'status':'source_verified_consumer_pending'})
 if typ==4:
  version,offset=r.unpack('<HH');assert version==0;r.p+=offset
  def menu(path):
   result=[];i=0
   while True:
    flags=r.word();mid=None if flags&16 else r.word();txt=r.string();key=path+str(i);add(key,txt,'menu_label');item={'flags':flags,'id':mid,'text':txt}
    if flags&16:item['children']=menu(key+'/')
    result.append(item);i+=1
    if flags&128:return result
  data={'kind':'MENU','items':menu('')}
 elif typ==5:
  assert b[:4]!=b'\x01\x00\xff\xff'
  style,exstyle,count,x,y,cx,cy=r.unpack('<IIHhhhh');m=r.value();cls=r.value();title=r.string();add('caption',title,'dialog_caption');font=None
  if style&64:font={'points':r.word(),'face':r.string()}
  controls=[]
  for i in range(count):
   r.align();st,ex,xx,yy,ww,hh,cid=r.unpack('<IIhhhhH');cc=r.value();text=r.value();add(f'control:{cid}:{i}',text,'control_text');n=r.word();extra=b[r.p:r.p+n];r.p+=n
   controls.append({'index':i,'id':cid,'style':st,'exstyle':ex,'rect':[xx,yy,ww,hh],'class':cc,'text':text,'extra':extra.hex()})
  data={'kind':'DIALOG','style':style,'exstyle':exstyle,'rect':[x,y,cx,cy],'menu':m,'class':cls,'caption':title,'font':font,'controls':controls}
 else:
  strings=[]
  for i in range(16):
   n=r.word();txt=b[r.p:r.p+n*2].decode('utf-16-le');r.p+=n*2;strings.append(txt);add(str((int(name)-1)*16+i),txt,'stringtable')
  data={'kind':'STRING','strings':strings}
 assert r.p==len(b) or not any(b[r.p:]),(name,r.p,len(b))
 structures.append({'index':e['index'],'name':name,'type':typ,'parsed_bytes':r.p,'total_bytes':len(b),'structure':data})
(U/'source/pe-visible-catalog.json').write_text(json.dumps({'evidence_id':tree['evidence_id'],'source_exe_sha256':hashlib.sha256(blob).hexdigest(),'records':rows,'structures':structures},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('PE_RECORDS',len(rows))
for a in rows:
 if any(x in a['id'] for x in ['MAJIRO_MAIN_NOCONFIG','SCREENOPTION','SELFONT','SPEEDCONFIG::','VOICE_SETUP','VOLUMECONFIG','ABOUTDIALOG_NORMAL']):print(a['id'],repr(a['source']))
