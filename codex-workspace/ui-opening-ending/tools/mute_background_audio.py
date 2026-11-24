"""Mute only the hash-bound private-desktop test process via Core Audio sessions."""
from pathlib import Path
import ctypes as C,uuid,json,hashlib,datetime,re,psutil,argparse
ap=argparse.ArgumentParser();ap.add_argument("--report",required=True);args=ap.parse_args();assert re.fullmatch(r"background-runtime-[a-z0-9-]+-audio\.json",args.report)
U=Path(__file__).resolve().parents[1];state=json.loads((U/'reports/background-runtime-state.json').read_text(encoding='utf-8'));pid=state['pid'];exe=(U/'runtime-ui-bg/レコンキスタ.exe').resolve()
assert Path(psutil.Process(pid).exe()).resolve()==exe
assert hashlib.sha256(exe.read_bytes()).hexdigest()==state['exe_sha256']=='f67195682944663b9546665eb3b63a639ace3f910e2ebf6ffaccda001d625b50'
P=C.c_void_p;PP=C.POINTER(P);I=C.c_int;D=C.c_ulong;HR=C.c_long
class GUID(C.Structure):_fields_=[('a',D),('b',C.c_ushort),('c',C.c_ushort),('d',C.c_ubyte*8)]
def guid(s):return GUID.from_buffer_copy(uuid.UUID(s).bytes_le)
refs=[]
def ok(hr):
 if hr<0:raise OSError(f'HRESULT 0x{hr&0xffffffff:08x}')
 return hr
def call(p,i,types,*args):
 v=C.cast(p,C.POINTER(C.POINTER(P))).contents
 return C.WINFUNCTYPE(HR,P,*types)(v[i])(p,*args)
def outcall(p,i,types,*args):
 o=P();ok(call(p,i,[*types,PP],*args,C.byref(o)));assert o;refs.append(o);return o
def qi(p,s):return outcall(p,0,[C.POINTER(GUID)],C.byref(guid(s)))
# Verify ABI slot ordering against the installed Microsoft Windows SDK.
sdk=Path('C:/Program Files (x86)/Windows Kits/10/Include/10.0.26100.0/um')
checks={'IMMDeviceEnumerator':('mmdeviceapi.h',{'EnumAudioEndpoints':3}),'IMMDeviceCollection':('mmdeviceapi.h',{'GetCount':3,'Item':4}),'IMMDevice':('mmdeviceapi.h',{'Activate':3}),'IAudioSessionManager2':('audiopolicy.h',{'GetSessionEnumerator':5}),'IAudioSessionEnumerator':('audiopolicy.h',{'GetCount':3,'GetSession':4}),'IAudioSessionControl2':('audiopolicy.h',{'GetProcessId':14}),'ISimpleAudioVolume':('audioclient.h',{'SetMute':5,'GetMute':6})}
for name,(header,slots) in checks.items():
 txt=(sdk/header).read_text(encoding='utf-8',errors='replace');body=txt.split('typedef struct '+name+'Vtbl')[1].split('} '+name+'Vtbl;')[0];methods=re.findall(r'STDMETHODCALLTYPE\s*\*(\w+)\s*\)',body)
 assert all(methods[index]==method for method,index in slots.items()),(name,methods)
ole=C.OleDLL('ole32');ole.CoInitializeEx.argtypes=[P,D];ole.CoInitializeEx.restype=HR;ole.CoCreateInstance.argtypes=[C.POINTER(GUID),P,D,C.POINTER(GUID),PP];ole.CoCreateInstance.restype=HR
ok(ole.CoInitializeEx(None,0));records=[];endpoints=0
try:
 enum=P();ok(ole.CoCreateInstance(C.byref(guid('BCDE0395-E52F-467C-8E3D-C4579291692E')),None,23,C.byref(guid('A95664D2-9614-4F35-A746-DE8DB63617E6')),C.byref(enum)));refs.append(enum)
 devices=outcall(enum,3,[I,D],0,1);count=D();ok(call(devices,3,[C.POINTER(D)],C.byref(count)));endpoints=count.value
 for ei in range(count.value):
  dev=outcall(devices,4,[D],ei);mgr=outcall(dev,3,[C.POINTER(GUID),D,P],C.byref(guid('77AA99A0-1BD6-484F-8BC7-2C654C9A9B6F')),23,None);sessions=outcall(mgr,5,[]);n=I();ok(call(sessions,3,[C.POINTER(I)],C.byref(n)))
  for si in range(n.value):
   control=outcall(sessions,4,[I],si);control2=qi(control,'bfb7ff88-7239-4fc9-8fa2-07c950be9c6d');owner=D();ok(call(control2,14,[C.POINTER(D)],C.byref(owner)))
   if owner.value!=pid:continue
   assert Path(psutil.Process(pid).exe()).resolve()==exe
   vol=qi(control,'87CE5498-68D6-44E5-9215-6DA47EF883D8');before=I();after=I();ok(call(vol,6,[C.POINTER(I)],C.byref(before)));ok(call(vol,5,[I,P],1,None));ok(call(vol,6,[C.POINTER(I)],C.byref(after)));assert after.value==1
   records.append({'endpoint_index':ei,'session_index':si,'pid':pid,'muted_before':bool(before.value),'muted_after':bool(after.value)})
finally:
 for p in reversed(refs):call(p,2,[])
 ole.CoUninitialize()
report={'time_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'target_pid':pid,'target_exe':str(exe),'target_exe_sha256':state['exe_sha256'],'active_render_endpoints_enumerated':endpoints,'sessions':records,'muted_target_sessions':len(records),'all_observed_target_sessions_muted':bool(records),'other_processes_modified':False,'endpoint_master_volume_modified':False,'limits':'Applies to observed sessions; a newly created separate audio session must be checked before movie validation.','references':['https://learn.microsoft.com/en-us/windows/win32/api/audiopolicy/nn-audiopolicy-iaudiosessioncontrol2','https://learn.microsoft.com/en-us/windows/win32/api/audioclient/nf-audioclient-isimpleaudiovolume-setmute']}
(U/'reports'/args.report).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,ensure_ascii=False));assert records,'No target audio session found; no mute guarantee'
