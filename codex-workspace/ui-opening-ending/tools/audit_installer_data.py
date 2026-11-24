from pathlib import Path
import json,re,hashlib,pefile,capstone
U=Path.cwd().resolve()
out={'schema_version':1,'method':'CP932 candidate scan of .data/.rdata; Capstone x86 linear references are candidates, not reachability or display-consumer proof','sources':[],'records':[]}
for fn in ['setup.exe','install.exe']:
 p=U.parent/'research/disc'/fn;b=p.read_bytes();pe=pefile.PE(data=b);base=pe.OPTIONAL_HEADER.ImageBase
 source={'file':fn,'path':str(p),'sha256':hashlib.sha256(b).hexdigest()};out['sources'].append(source)
 records=[]
 for section in pe.sections:
  if section.Name.rstrip(b'\0') not in [b'.data',b'.rdata']:continue
  raw=section.get_data()
  for m in re.finditer(rb'[^\x00]{4,}\x00',raw):
   q=m.group()[:-1]
   try:t=q.decode('cp932')
   except UnicodeDecodeError:continue
   if not all(c.isprintable() or c in '\n\r\t' for c in t) or not re.search('[ぁ-んァ-ヶ一-龯]',t):continue
   va=base+section.VirtualAddress+m.start();records.append({'id':fn+'::'+hex(va),'file':fn,'va':va,'section':section.Name.decode().rstrip('\0'),'file_offset':section.PointerToRawData+m.start(),'byte_length':len(q),'source':t,'references':[],'status':'unclassified_candidate'})
 byva={r['va']:r for r in records};md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32);md.detail=True;md.skipdata=True
 textsec=next(s for s in pe.sections if s.Name.rstrip(b'\0')==b'.text')
 instructions=list(md.disasm(textsec.get_data(),base+textsec.VirtualAddress))
 for ins in instructions:
  if not ins.id:continue
  for op in ins.operands:
   if op.type==capstone.x86.X86_OP_IMM and op.imm in byva:byva[op.imm]['references'].append({'va':ins.address,'instruction':ins.mnemonic+' '+ins.op_str,'bytes':ins.bytes.hex()})
 out['records']+=records
 if fn=='setup.exe':
  imports={i.address:i.name.decode() if i.name else str(i.ordinal) for e in pe.DIRECTORY_ENTRY_IMPORT for i in e.imports}
  for ins in instructions:
   if 0x401f90<=ins.address<=0x402175:
    notes=[]
    if ins.id:
     for op in ins.operands:
      if op.type==capstone.x86.X86_OP_MEM and op.mem.disp in imports:notes.append(imports[op.mem.disp])
      if op.type==capstone.x86.X86_OP_IMM and op.imm in byva:notes.append(repr(byva[op.imm]['source']))
    print(hex(ins.address),ins.mnemonic,ins.op_str,' '.join(notes))
(U/'source/installer-data-string-candidates.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Candidate records',len(out['records']),'sources',len(out['sources']))
