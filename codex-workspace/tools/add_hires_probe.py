from pathlib import Path
import pefile,capstone,json
r=Path('candidates/hires-v1/native');p=r/'ReconquistaHD.cpp';s=p.read_text('utf-8-sig');s=s.replace('static bool initialized=false;', 'static bool probe=false;static unsigned probeShots=0;static ULONGLONG probeTime=0;static bool initialized=false;')
s=s.replace('if(initialized)return;initialized=true;', 'if(initialized)return;initialized=true;wchar_t probeValue[8];probe=GetEnvironmentVariableW(L"RECON_HD_PROBE",probeValue,8)>0;')
s=s.replace('fullscreen=full!=0;', 'fullscreen=full!=0;if(probe){SetMenu(game,nullptr);SetWindowLongA(game,GWL_STYLE,WS_POPUP);SetWindowPos(game,HWND_NOTOPMOST,-20000,-20000,3840,2160,SWP_FRAMECHANGED|SWP_NOACTIVATE);if(logFile){fprintf(logFile,"probe hidden mode viewport=480,0,2880,2160\\n");fflush(logFile);}return;}')
insert='''static void DumpProbe(Bitmap*b){if(!probe||!loads||probeShots>=6||GetTickCount64()-probeTime<2000)return;probeTime=GetTickCount64();auto s=Get(b,{0,0,b->w,b->h},true);if(!s)return;wchar_t dir[MAX_PATH],path[MAX_PATH];swprintf_s(dir,L"%s\\\\qa",root);CreateDirectoryW(dir,nullptr);swprintf_s(path,L"%s\\\\probe-%02u.bmp",dir,probeShots++);FILE*f=nullptr;if(_wfopen_s(&f,path,L"wb")||!f)return;BITMAPFILEHEADER head{};head.bfType=0x4d42;head.bfOffBits=sizeof(head)+sizeof(BITMAPINFOHEADER);head.bfSize=head.bfOffBits+DWORD(s->pixels.size());fwrite(&head,sizeof(head),1,f);fwrite(&s->info.bmiHeader,sizeof(BITMAPINFOHEADER),1,f);fwrite(s->pixels.data(),1,s->pixels.size(),f);fclose(f);if(logFile){fprintf(logFile,"probe shot=%u assets=%llu blits=%llu memory=%llu\\n",probeShots,loads,blits,used);fflush(logFile);}}
using RenderFn=void(__cdecl*)();static RenderFn oldRender;static void __cdecl Render(){oldRender();if(probe){Bitmap*b=*(Bitmap**)0x56a6a8;if(Valid(b)){nesting++;try{DumpProbe(b);}catch(const std::bad_alloc&){}nesting--;}}}
'''
s=s.replace('static void IAT(',insert+'static void IAT(');p.write_text(s,encoding='utf-8-sig')
rows=json.loads((r/'hooks.json').read_text());pe=pefile.PE('builds/body-ui-20261023-v9/レコンキスタ.exe');cs=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32);cs.detail=True;addr=0x437ad0;data=pe.get_data(addr-0x400000,32);n=0;ins=[]
for x in cs.disasm(data,addr):
 if n>=5:break
 assert not any(g in x.groups for g in [capstone.CS_GRP_JUMP,capstone.CS_GRP_CALL]);n+=x.size;ins.append((hex(x.address),x.mnemonic,x.op_str))
rows.append({'name':'Render','address':hex(addr),'length':n,'expected':data[:n].hex(),'instructions':ins,'original':'oldRender'})
decl=['static const unsigned char bytes_'+x['name']+'[]={'+','.join(hex(v) for v in bytes.fromhex(x['expected']))+'};' for x in rows]+['static Hook hooks[]={']
for x in rows:decl.append('{'+x['address']+','+str(x['length'])+',bytes_'+x['name']+', (void*)'+x['name']+', '+('(void**)&'+x['original'] if x['original'] else 'nullptr')+'},')
decl+=['};'];(r/'hooks.inc').write_text('\n'.join(decl));(r/'hooks.json').write_text(json.dumps(rows,indent=2));print('probe instrumentation added')
