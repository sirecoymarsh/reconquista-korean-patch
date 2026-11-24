"""Read only matching temp-directory path metadata from the identified failing runtime; no memory dump."""
import ctypes as C,ctypes.wintypes as W,re,json
from pathlib import Path
rows=json.loads(Path('temp/node-repl-cpu-delta.json').read_text());assert len(rows)==1;pid=rows[0]['pid'];k=C.WinDLL('kernel32',use_last_error=True)
k.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];k.OpenProcess.restype=W.HANDLE;k.CloseHandle.argtypes=[W.HANDLE]
k.ReadProcessMemory.argtypes=[W.HANDLE,C.c_void_p,C.c_void_p,C.c_size_t,C.POINTER(C.c_size_t)]
class MBI(C.Structure):_fields_=[('BaseAddress',C.c_void_p),('AllocationBase',C.c_void_p),('AllocationProtect',W.DWORD),('PartitionId',W.WORD),('RegionSize',C.c_size_t),('State',W.DWORD),('Protect',W.DWORD),('Type',W.DWORD)]
k.VirtualQueryEx.argtypes=[W.HANDLE,C.c_void_p,C.POINTER(MBI),C.c_size_t];k.VirtualQueryEx.restype=C.c_size_t
h=k.OpenProcess(0x410,False,pid);assert h
pattern=re.compile(rb'C:\\Users\\(?:CADRIA~1|CadriacLord)\\AppData\\Local\\Temp\\\.tmp[A-Za-z0-9]{6}',re.I);found=set();address=0;readbytes=0
try:
 while address<0x7fffffffffff:
  m=MBI()
  if not k.VirtualQueryEx(h,address,C.byref(m),C.sizeof(m)):break
  base=m.BaseAddress or 0;size=m.RegionSize;address=base+size
  if not size:break
  if m.Type!=0x20000 or m.State!=0x1000 or m.Protect not in [2,4,8]:continue
  if size>64*1024*1024:continue
  for off in range(0,size,1024*1024):
   n=min(size-off,1024*1024);buf=C.create_string_buffer(n);done=C.c_size_t();ok=k.ReadProcessMemory(h,base+off,buf,n,C.byref(done))
   if not ok:continue
   data=buf.raw[:done.value];readbytes+=len(data)
   found.update(x.decode('ascii') for x in pattern.findall(data))
   # UTF-16 path representation, restricted to the same exact temp-directory pattern.
   found.update(x.decode('ascii') for x in pattern.findall(data.replace(b'\x00',b'')))
   del data,buf
  if readbytes>128*1024*1024:break
finally:k.CloseHandle(h)
report={'pid':pid,'read_mb':round(readbytes/1024**2,1),'matching_temporary_paths':[{'path':s,'exists':Path(s).exists()} for s in sorted(found)]};print(json.dumps(report,ensure_ascii=False));Path('reports/node-repl-failing-temp-path.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
