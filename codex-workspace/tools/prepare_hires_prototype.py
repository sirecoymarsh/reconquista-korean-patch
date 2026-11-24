from pathlib import Path
import pefile,capstone,json,struct,os,shutil
R=Path(__file__).resolve().parents[1];O=R/'candidates/hires-v1';N=O/'native';T=O/'runtime-prototype';T.mkdir(exist_ok=True)
p=N/'ReconquistaHD.cpp';s=p.read_text('utf-8-sig');s=s.replace('static CopyFn oldCopy;','static CopyFn oldCopy,oldSwap;')
s=s.replace('static bool Pair(Bitmap* a,Box* ar,Bitmap* b,Box* br,Shadow*& sa,Shadow*& sb){if(!shadows.count(a)', 'static bool Pair(Bitmap* a,Box* ar,Bitmap* b,Box* br,Shadow*& sa,Shadow*& sb){if(!Valid(a)||!Valid(b)||ar->x<0||ar->y<0||br->x<0||br->y<0||ar->w<0||ar->h<0||ar->x+ar->w>a->w||ar->y+ar->h>a->h||br->x+br->w>b->w||br->y+br->h>b->h)return false;if(!shadows.count(a)')
s=s.replace('static void __cdecl Copy(Bitmap* a,Box* ar,Bitmap* b,Box* br){if(nesting)', 'static void __cdecl Copy(Bitmap* a,Box* ar,Bitmap* b,Box* br){Box target{br->x,br->y,ar->w,ar->h};br=&target;if(nesting)')
s=s.replace('int alpha){if(nesting)', 'int alpha){Box target{br->x,br->y,ar->w,ar->h};br=&target;if(nesting)')
insert='''static void __cdecl Swap(Bitmap* a,Box* ar,Bitmap* b,Box* br){Box target{br->x,br->y,ar->w,ar->h};br=&target;if(nesting){oldSwap(a,ar,b,br);return;}nesting++;Shadow *sa,*sb;bool hd=Pair(a,ar,b,br,sa,sb);if(hd){Box x=Scale(*ar),y=Scale(*br);oldSwap(&sa->b,&x,&sb->b,&y);blits++;}oldSwap(a,ar,b,br);if(hd){Snapshot(sa,a,*ar);Snapshot(sb,b,*br);}nesting--;}\n'''
s=s.replace('static void AlphaCommon',insert+'static void AlphaCommon');p.write_text(s,encoding='utf-8-sig')
base=R/'builds/body-ui-20261023-v9/レコンキスタ.exe';pe=pefile.PE(str(base));cs=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32);cs.detail=True;rows=[];decl=[]
for name,addr,orig in [('Load',0x417950,'oldLoad'),('Free',0x43afb0,'oldFree'),('Copy',0x442870,'oldCopy'),('Swap',0x442c60,'oldSwap'),('Alpha',0x443180,'oldAlpha'),('Mask',0x440640,'oldMask'),('Transform',0x4434e0,'oldTransform'),('Mode',0x43f4a0,None)]:
 data=pe.get_data(addr-0x400000,32);n=0;ins=[]
 for x in cs.disasm(data,addr):
  if n>=5:break
  assert not any(g in x.groups for g in [capstone.CS_GRP_JUMP,capstone.CS_GRP_CALL]);n+=x.size;ins.append((hex(x.address),x.mnemonic,x.op_str))
 raw=data[:n];decl.append('static const unsigned char bytes_'+name+'[]={'+','.join(hex(x) for x in raw)+'};');rows.append({'name':name,'address':hex(addr),'length':n,'expected':raw.hex(),'instructions':ins,'original':orig})
decl.append('static Hook hooks[]={')
for r in rows:decl.append('{'+r['address']+','+str(r['length'])+',bytes_'+r['name']+', (void*)'+r['name']+', '+('(void**)&'+r['original'] if r['original'] else 'nullptr')+'},')
decl.append('};');(N/'hooks.inc').write_text('\n'.join(decl),encoding='ascii');(N/'hooks.json').write_text(json.dumps(rows,indent=2))
# Add one PE section; preserve existing section bytes and the original product filename.
b=bytearray(base.read_bytes());last=pe.sections[-1];align=lambda v,a:(v+a-1)//a*a
va=align(last.VirtualAddress+max(last.Misc_VirtualSize,last.SizeOfRawData),pe.OPTIONAL_HEADER.SectionAlignment);raw=align(len(b),pe.OPTIONAL_HEADER.FileAlignment);b.extend(b'\0'*(raw-len(b)))
imports={i.name:i.address for d in pe.DIRECTORY_ENTRY_IMPORT for i in d.imports if i.name};dll=b'ReconquistaHD.dll\0';nameva=0x400000+va+128
code=b'\x9c\x60\x68'+struct.pack('<I',nameva)+b'\xff\x15'+struct.pack('<I',imports[b'LoadLibraryA'])+b'\x85\xc0\x75\x08\x6a\x48\xff\x15'+struct.pack('<I',imports[b'ExitProcess'])+b'\x61\x9d'
code+=b'\xe9'+struct.pack('<i',(0x400000+pe.OPTIONAL_HEADER.AddressOfEntryPoint)-(0x400000+va+len(code)+5));section=code.ljust(128,b'\0')+dll;section=section.ljust(align(len(section),pe.OPTIONAL_HEADER.FileAlignment),b'\0');b.extend(section)
header=pe.sections[-1].get_file_offset()+40;assert header+40<=pe.OPTIONAL_HEADER.SizeOfHeaders and not any(b[header:header+40]);struct.pack_into('<8sIIIIIIHHI',b,header,b'.hd\0\0\0\0\0',len(section),va,len(section),raw,0,0,0,0,0x60000020)
struct.pack_into('<H',b,pe.FILE_HEADER.get_field_absolute_offset('NumberOfSections'),pe.FILE_HEADER.NumberOfSections+1);struct.pack_into('<I',b,pe.OPTIONAL_HEADER.get_field_absolute_offset('AddressOfEntryPoint'),va);struct.pack_into('<I',b,pe.OPTIONAL_HEADER.get_field_absolute_offset('SizeOfImage'),align(va+len(section),pe.OPTIONAL_HEADER.SectionAlignment));struct.pack_into('<H',b,pe.FILE_HEADER.get_field_absolute_offset('Characteristics'),pe.FILE_HEADER.Characteristics|0x20)
# Original is fixed-base x86. Native patch addresses are only valid at 0x400000.
assert pe.OPTIONAL_HEADER.ImageBase==0x400000 and not (pe.OPTIONAL_HEADER.DllCharacteristics&0x40)
(T/'レコンキスタ.exe').write_bytes(b);(O/'exe-prototype.json').write_text(json.dumps({'base':'body-ui-20261023-v9','new_section_rva':hex(va),'old_entry':hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint),'large_address_aware':True,'library':'ReconquistaHD.dll','game_installed':False},indent=2))
for path in (R/'runtime-body-ui-20261023-v9').rglob('*'):
 rel=path.relative_to(R/'runtime-body-ui-20261023-v9');dest=T/rel
 if path.is_dir():dest.mkdir(exist_ok=True)
 elif rel.name!='レコンキスタ.exe' and not dest.exists():
  if rel.parts[0]=='savedata':shutil.copy2(path,dest)
  else:os.link(path,dest)
print('prototype created; DLL copy required after compile')
