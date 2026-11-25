#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <psapi.h>
#include <imm.h>
#pragma comment(lib,"imm32.lib")
#include <wincodec.h>
#include <cstdint>
#include <cstdio>
#include <vector>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <memory>
#include <algorithm>
#include <atomic>
#include <execution>
#include <numeric>
#include <thread>
#include <mutex>
#include <cwctype>
#include <cmath>
#include <climits>
#include <cstdlib>
#include <new>
#include <share.h>
#include <wrl/client.h>
#include <intrin.h>
#include <nmmintrin.h>

// Exact v9 x86 ABI; no script or save-file dimensions change.
struct Bitmap {int w,h,pitch,keep,format,unknown; Bitmap* mask; BITMAPINFO* info; RGBQUAD* palette; unsigned char* pixels; HBITMAP handle; void* prev; void* next;};
static_assert(sizeof(Bitmap)==52,"engine bitmap ABI");
struct Box {int x,y,w,h;};
// blank: the 4x pixels (and the other-quality copy) are not filled yet; the caller overwrites all of them next.
// job: a worker is decoding its 4x art (LoadHD); Join waits for it before anything else touches the shadow.
struct DecodeJob;
struct Shadow {Bitmap b{},alternateBitmap{};Shadow*maskShadow=nullptr; BITMAPINFO info{}; std::vector<unsigned char> pixels,snapshot,alternate; uint64_t age=0,revision=0;Box dirty{};bool blank=false;DecodeJob*job=nullptr;};
static std::unordered_map<Bitmap*,std::unique_ptr<Shadow>> shadows;
static std::unordered_set<uint32_t> missing;
struct AssetTag {std::string name;uint64_t hash;bool hd=false;}; static std::unordered_map<Bitmap*,AssetTag> assets;   // hd: its shadow got the 4x art
// RECON_OFF=a,b,... turns single stutter fixes off, for side-by-side timing in one build: crc (fingerprint), pool (buffer
// reuse), trash (background frees), blank (no upscale before an overwrite), reuse (same picture handed back), par (row
// bands for upscales and copies), async (background decode), defer (the screen batch); alt (timing only: no other-quality
// copies at all, so the CG/menu quality switch does nothing), ahead (reading pictures ahead), cover (skipping screen draws a later Copy covers).
enum {OFF_CRC=1,OFF_POOL=2,OFF_TRASH=4,OFF_BLANK=8,OFF_REUSE=16,OFF_PAR=32,OFF_ASYNC=64,OFF_DEFER=128,OFF_ALT=256,OFF_AHEAD=512,OFF_COVER=1024,OFF_SPARSE=2048};
static bool Off(unsigned f){static const unsigned mask=[]{wchar_t v[256]{};unsigned m=0;if(GetEnvironmentVariableW(L"RECON_OFF",v,256)){const wchar_t*names[]={L"crc",L"pool",L"trash",L"blank",L"reuse",L"par",L"async",L"defer",L"alt",L"ahead",L"cover",L"sparse"};
  for(unsigned i=0;i<12;i++)if(wcsstr(v,names[i]))m|=1u<<i;}return m;}();return (mask&f)!=0;}
// The asset check's hash of the low-res pixels, compared only within a run. Byte-wise FNV-1a took 3.3 ms for an 800x600
// RGB bitmap and a load ran it up to three times; CRC32C over 4-byte words in three lanes takes 0.1 ms (tools/membench).
static uint64_t Fingerprint(Bitmap*b){static const bool crc=[]{int r[4];__cpuid(r,1);return ((r[2]>>20)&1)!=0;}();int span=b->w*(b->format?1:3);uint64_t tail=1469598103934665603ull;
 if(!crc||Off(OFF_CRC)){for(int y=0;y<b->h;y++)for(int x=0;x<span;x++){tail^=b->pixels[y*b->pitch+x];tail*=1099511628211ull;}return tail;}   // no SSE4.2: the old hash
 uint32_t l0=~0u,l1=~1u,l2=~2u;for(int y=0;y<b->h;y++){const unsigned char*r=b->pixels+size_t(y)*b->pitch;int i=0;
  for(;i+12<=span;i+=12){uint32_t v[3];memcpy(v,r+i,12);l0=_mm_crc32_u32(l0,v[0]);l1=_mm_crc32_u32(l1,v[1]);l2=_mm_crc32_u32(l2,v[2]);}for(;i<span;i++){tail^=r[i];tail*=1099511628211ull;}}
 return tail^(uint64_t(l0)<<32|l1)^(uint64_t(l2)*0x9e3779b97f4a7c15ull);}
#include "cg_keys.inc"
#include "ui_keys.inc"
static bool hdPack=false;   // the 4K pictures are installed (the release's 고화질 묶음: hires or hires-jxl beside the DLL)
static bool cg4k=true,cgDesired=true,cgPending=false,cgApplyFailed=false;static unsigned cgRetries=0;static ULONGLONG cgRetryAt=0;static void QualityStatus();static int decoding=0;static uint64_t revisionClock=0;
static bool IsCG(uint32_t key){return std::binary_search(std::begin(cgKeys),std::end(cgKeys),key)||std::binary_search(std::begin(uiKeys),std::end(uiKeys),key);}
static bool perf=false;
static void Dirty(Shadow*s,Box r){if(!s||r.w<=0||r.h<=0)return;s->revision=++revisionClock;
 if(s->dirty.w<=0||s->dirty.h<=0)s->dirty=r;else{int x=std::min(s->dirty.x,r.x),y=std::min(s->dirty.y,r.y);s->dirty={x,y,std::max(s->dirty.x+s->dirty.w,r.x+r.w)-x,std::max(s->dirty.y+s->dirty.h,r.y+r.h)-y};}}
static bool LoadHD(Bitmap*,const char*,uint64_t);static void Join(Shadow*);static void JoinAll();static void ApplyCG();static void SettleFor(Shadow*);static void SettleAll();static bool Defer(char,Bitmap*,Bitmap*,Shadow*,Shadow*,const Box&,const Box&,int);static void FinishFrame();   // defer.inc
static bool screenDrawn=false;   // something was drawn onto the screen page since the last present (copy and mask in Defer, alpha, transform)
static bool lastFrameDrew=false;
static int flowWarmStage=0;static ULONGLONG flowArriveTick=0;static uint64_t tick=0,used=0; static int nesting=0; static FILE* logFile=nullptr;
static wchar_t root[MAX_PATH]; static IWICImagingFactory* wic=nullptr;
static bool probe=false,probeNative=false;static bool inputProbe=false;static bool configProbe=false;static HWND reviewButton=nullptr;static HFONT reviewFont=nullptr;static int reviewFontPixels=0;static const UINT REVIEW_BUTTON_ID=0x7e42;static bool reviewProbe=false;static bool reviewEnabled=false;static HMENU reviewMenu=nullptr;static const UINT REVIEW_ID=0x7e41;static bool forceStartupFullscreen=false,titleReady=false;static unsigned probeShots=0;static ULONGLONG probeTime=0;static bool initialized=false; static HWND game=nullptr; static HMENU oldMenu=nullptr; static LONG oldStyle=0; static RECT oldRect{}; static bool fullscreen=false;static bool displayConfigured=false;static RECT desired{};static HMONITOR probeMonitor=nullptr;
static uint64_t frames=0,loads=0,blits=0,fallbackPixels=0; static LARGE_INTEGER freq{};
static std::unordered_map<const void*,uint64_t> perfMoved;   // perf: 1x pixels synced into each bitmap's 4x (defer.inc's layer dump)
static bool parity=false;static double pNearest=0,pDecode=0,pCompose=0;static unsigned pPresent=0,pMode=0;   // RECON_PERF=1 also byte-checks the fast paths against the old ones (slow); =2 only times
static bool hitch=false;static uint64_t hShadows=0;static int traceFrames=0;   // stutter profiler (hitch.inc, RECON_HITCH=1); traceFrames: trace the frames after one with many alpha blits
// RECON_HITCH_TRACE=1 (with the profiler): every blit and shadow made or dropped goes into this frame's buffer, and hitch.inc
// writes the buffer out only for a frame that turned out long and busy.
static bool traceRecord=false;static std::string traceBuffer;static unsigned traceLines=0;
static void TraceNote(const char*line){if(traceRecord){if(traceLines<1500){traceBuffer+=line;traceLines++;}}else if(logFile)fputs(line,logFile);}
static LONGLONG Now(){LARGE_INTEGER t;QueryPerformanceCounter(&t);return t.QuadPart;}
static double Ms(LONGLONG t){return 1000.0*(Now()-t)/freq.QuadPart;}
// hitch.inc: the layer's work outside its decode/sync/compose timers (alternate copies, frees, engine load and blit time
// inside the hooks, shadow pairing, snapshots), so the profiler can split a long frame further.
static double hAltMs=0,hFreeMs=0,hLoadMs=0,hEngLoadMs=0,hHookMs=0,hEngBlitMs=0,hPairMs=0,hSnapMs=0;static uint64_t hAltMade=0,hAltDropped=0,hSpareHit=0,hSpareMiss=0,hLoadReuse=0;
static double hDecodeDone=0,hNearestDone=0,hComposeDone=0;   // what the perf timers held when Present zeroed them (they are per present)
struct HitchTime {double&total;LONGLONG start;HitchTime(double&t):total(t),start(hitch?Now():0){}~HitchTime(){if(hitch)total+=Ms(start);}};
struct Timing {double& total;LONGLONG start;Timing(double&t):total(t),start(Now()){}~Timing(){if(perf)total+=Ms(start);}};
// perf only: what each 4x blit cost (kind, logical size), summarised in the next perf_present
struct BlitStat {char kind;int w,h;double ms;};static std::vector<BlitStat> blitStats;
struct BlitTiming {char kind;int w,h;LONGLONG start;BlitTiming(char k,int ww,int hh):kind(k),w(ww),h(hh),start(Now()){}~BlitTiming(){if(perf){double ms=Ms(start);pCompose+=ms;blitStats.push_back({kind,w,h,ms});}}};
static void PerfCommand(HWND,WPARAM);static void DumpVar(uint32_t);static void DumpElem(uint32_t,int,int);
#include "crashlog.inc"
static void Init(){if(initialized)return;initialized=true;CrashlogInstall();perf=GetEnvironmentVariableW(L"RECON_PERF",nullptr,0)>0;hitch=GetEnvironmentVariableW(L"RECON_HITCH",nullptr,0)>0;traceRecord=hitch&&GetEnvironmentVariableW(L"RECON_HITCH_TRACE",nullptr,0)>0;wchar_t probeValue[8];parity=perf&&!(GetEnvironmentVariableW(L"RECON_PERF",probeValue,8)>0&&probeValue[0]==L'2');probe=GetEnvironmentVariableW(L"RECON_HD_PROBE",probeValue,8)>0;probeNative=probe&&probeValue[0]==L'2';reviewProbe=probe&&GetEnvironmentVariableW(L"RECON_REVIEW_PROBE",probeValue,8)>0;inputProbe=probe&&GetEnvironmentVariableW(L"RECON_INPUT_PROBE",probeValue,8)>0;configProbe=probe&&GetEnvironmentVariableW(L"RECON_CONFIG_PROBE",probeValue,8)>0;forceStartupFullscreen=GetEnvironmentVariableW(L"RECON_HD_START_FULLSCREEN",probeValue,8)>0; GetModuleFileNameW(GetModuleHandleW(L"ReconquistaHD.dll"),root,MAX_PATH);wchar_t* p=wcsrchr(root,L'\\');if(p)*p=0;
 wchar_t path[MAX_PATH];swprintf_s(path,L"%s\\hires-runtime.log",root);logFile=_wfsopen(path,L"w",_SH_DENYNO); QueryPerformanceFrequency(&freq);
 CoInitializeEx(nullptr,COINIT_MULTITHREADED);CoCreateInstance(CLSID_WICImagingFactory,nullptr,CLSCTX_INPROC_SERVER,IID_PPV_ARGS(&wic));
 wchar_t reviewPath[MAX_PATH];swprintf_s(reviewPath,L"%s\\review-unlock.enabled",root);reviewEnabled=GetFileAttributesW(reviewPath)!=INVALID_FILE_ATTRIBUTES;
 swprintf_s(path,L"%s\\cg-quality.ini",root);cg4k=GetPrivateProfileIntW(L"graphics",L"cg_4k",1,path)!=0;cgDesired=cg4k;
 for(auto dir:{L"hires-jxl",L"hires"}){swprintf_s(path,L"%s\\%s\\*",root,dir);WIN32_FIND_DATAW fd{};HANDLE h=FindFirstFileW(path,&fd);if(h==INVALID_HANDLE_VALUE)continue;do{if(!(fd.dwFileAttributes&FILE_ATTRIBUTE_DIRECTORY)){hdPack=true;break;}}while(FindNextFileW(h,&fd));FindClose(h);if(hdPack)break;}
 if(logFile){fprintf(logFile,"Reconquista HD v1 logical=800x600 backing=3200x2400 dpi_aware=%d\n",IsProcessDPIAware());fflush(logFile);}}
static Box Clip(Bitmap* b,Box r){int ex=std::min(b->w,r.x+std::max(0,r.w)),ey=std::min(b->h,r.y+std::max(0,r.h));r.x=std::max(0,r.x);r.y=std::max(0,r.y);r.w=std::max(0,ex-r.x);r.h=std::max(0,ey-r.y);return r;}
static bool Valid(Bitmap* b){return b&&b->pixels&&b->w>0&&b->h>0&&b->w<=8192&&b->h<=8192&&b->pitch>0&&uint64_t(b->w)*b->h<16000000;}
static void Snapshot(Shadow* s,Bitmap* b,Box box){box=Clip(b,box);int ch=b->format?1:3;for(int y=box.y;y<box.y+box.h;y++)memcpy(s->snapshot.data()+y*b->pitch+box.x*ch,b->pixels+y*b->pitch+box.x*ch,box.w*ch);Dirty(s,box);}
// A low-res pixel becomes a 4x4 block. A run of pixels is widened into the block's first 4x row, and that span is copied
// to the other three rows and to the other-quality copy: the same bytes as writing each pixel 16 times, at a fraction of
// the cost (a fresh 800x600 shadow took 21-34 ms pixel by pixel, a scene change loads several).
static void Widen(unsigned char* d,const unsigned char* p,int n,int ch){
 if(ch==1){for(int i=0;i<n;i++)memset(d+i*4,p[i],4);return;}
 for(int i=0;i<n;i++,p+=3,d+=12){d[0]=d[3]=d[6]=d[9]=p[0];d[1]=d[4]=d[7]=d[10]=p[1];d[2]=d[5]=d[8]=d[11]=p[2];}}
static void NearestRun(Shadow*s,const unsigned char*p,int x,int y,int n,int ch){size_t span=size_t(n)*4*ch,at=size_t(x)*4*ch;auto d0=s->pixels.data()+size_t(y*4)*s->b.pitch+at;Widen(d0,p,n,ch);
 for(int yy=1;yy<4;yy++)memcpy(d0+size_t(yy)*s->b.pitch,d0,span);
 if(!s->alternate.empty())for(int yy=0;yy<4;yy++)memcpy(s->alternate.data()+size_t(y*4+yy)*s->b.pitch+at,d0,span);}
// perf only: the first 30 large syncs and 10 base fills also run the old pixel-by-pixel loops on copies; they must match.
static void NearestPixelwise(std::vector<unsigned char>&px,std::vector<unsigned char>&alt,std::vector<unsigned char>&snap,int pitch4,Bitmap*b,Box box,bool changedOnly){int ch=b->format?1:3;
 for(int y=box.y;y<box.y+box.h;y++)for(int x=box.x;x<box.x+box.w;x++){auto p=b->pixels+y*b->pitch+x*ch;auto q=snap.data()+y*b->pitch+x*ch;if(changedOnly&&memcmp(p,q,ch)==0)continue;
  for(int yy=0;yy<4;yy++){auto d=px.data()+(y*4+yy)*pitch4+x*4*ch;for(int xx=0;xx<4;xx++)memcpy(d+xx*ch,p,ch);if(!alt.empty()){auto a=alt.data()+(y*4+yy)*pitch4+x*4*ch;for(int xx=0;xx<4;xx++)memcpy(a+xx*ch,p,ch);}}memcpy(q,p,ch);}}
static int nearestParity=0,baseParity=0;
static void BandsRun(int bands,void(*fn)(void*,int),void*ctx);   // fn(ctx,0..bands-1) on the band workers (BandPool, below)
// Rows [ya,yb) of box: the changed runs (every pixel unless changedOnly) are upscaled and taken into the snapshot, and the
// extent of what changed is grown.
struct NearestBox {int x0=INT_MAX,x1=INT_MIN,y0=INT_MAX,y1=INT_MIN;uint64_t moved=0;};
static void NearestRows(Shadow*s,Bitmap*b,Box box,int ch,bool changedOnly,int ya,int yb,NearestBox&e){
 for(int y=ya;y<yb;y++){auto row=b->pixels+size_t(y)*b->pitch+box.x*ch;auto previous=s->snapshot.data()+size_t(y)*b->pitch+box.x*ch;
  if(changedOnly&&memcmp(row,previous,size_t(box.w)*ch)==0)continue;
  for(int x=box.x,end=box.x+box.w;x<end;){auto p=row+size_t(x-box.x)*ch;auto q=previous+size_t(x-box.x)*ch;if(changedOnly&&memcmp(p,q,ch)==0){x++;continue;}
   int n=1;if(changedOnly)while(x+n<end&&memcmp(p+n*ch,q+n*ch,ch))n++;else n=end-x;   // the run of changed pixels
   NearestRun(s,p,x,y,n,ch);memcpy(q,p,size_t(n)*ch);e.x0=std::min(e.x0,x);e.x1=std::max(e.x1,x+n);e.y0=std::min(e.y0,y);e.y1=std::max(e.y1,y+1);if(changedOnly)e.moved+=n;x+=n;}}}
struct NearestJob {Shadow*s;Bitmap*b;Box box;int ch;bool changedOnly;int ya,bands;NearestBox part[32];};
static void NearestBand(void*p,int k){auto&j=*(NearestJob*)p;int rows=j.box.y+j.box.h-j.ya;NearestRows(j.s,j.b,j.box,j.ch,j.changedOnly,j.ya+MulDiv(rows,k,j.bands),j.ya+MulDiv(rows,k+1,j.bands),j.part[k]);}
static void Nearest(Shadow* s,Bitmap* b,Box box,bool changedOnly){Timing timer(pNearest);box=Clip(b,box);int ch=b->format?1:3;
 std::vector<unsigned char> rp,ra,rs;bool check=parity&&logFile&&nearestParity<30&&box.w*box.h>=20000;
 if(check){SettleFor(s);rp=s->pixels;ra=s->alternate;rs=s->snapshot;NearestPixelwise(rp,ra,rs,s->b.pitch,b,box,changedOnly);}
 int ya=box.y,yend=box.y+box.h;   // nothing is written above the first changed row; queued 4x blits on s go before it
 if(changedOnly)while(ya<yend&&!memcmp(b->pixels+size_t(ya)*b->pitch+box.x*ch,s->snapshot.data()+size_t(ya)*b->pitch+box.x*ch,size_t(box.w)*ch))ya++;
 NearestBox e;if(ya<yend){SettleFor(s);
  // A large fill is cut into row bands: a sprite change makes and frees several 800x600 work pages a frame, and each new
  // page is a 23 MB fill (~5 ms on one core). Only when at least 128 rows change: banding the many small syncs as well
  // kept the band workers awake and spinning beside the game thread (matrix m: twice the long frames).
  int rows=yend-ya;if(changedOnly){rows=0;for(int y=ya;y<yend&&rows<128;y++)rows+=memcmp(b->pixels+size_t(y)*b->pitch+box.x*ch,s->snapshot.data()+size_t(y)*b->pitch+box.x*ch,size_t(box.w)*ch)!=0;}
  int bands=Off(OFF_PAR)||rows<128?1:int(std::min<int64_t>({int64_t(yend-ya)*box.w/16384,(yend-ya)/8,32}));
  if(bands>=2){NearestJob j{s,b,box,ch,changedOnly,ya,bands};BandsRun(bands,NearestBand,&j);
   for(int k=0;k<bands;k++){auto&q=j.part[k];e.x0=std::min(e.x0,q.x0);e.x1=std::max(e.x1,q.x1);e.y0=std::min(e.y0,q.y0);e.y1=std::max(e.y1,q.y1);e.moved+=q.moved;}}
  else NearestRows(s,b,box,ch,changedOnly,ya,yend,e);}
 fallbackPixels+=e.moved;if(perf&&e.moved)perfMoved[b]+=e.moved;if(e.x0<e.x1)Dirty(s,{e.x0,e.y0,e.x1-e.x0,e.y1-e.y0});
 if(check){nearestParity++;fprintf(logFile,"perf_nearest_parity n=%d size=%dx%d changed_only=%d equal=%d\n",nearestParity,box.w,box.h,changedOnly,rp==s->pixels&&ra==s->alternate&&rs==s->snapshot);fflush(logFile);}
}
// 4x buffers that ForgetShadow, DropAlternate and the decode cache let go wait here (exact sizes, up to 192 MB) for the
// next one of that size: a fresh 23 MB buffer cost 7.5 ms in page faults and zero fill, a fresh copy 8.5 ms, against 1.2
// and 1.8 ms reused (tools/membench), and a scene change lets go of and makes several. Past the limit they are freed on a
// background thread.
static std::vector<std::vector<unsigned char>> spare;static size_t spareBytes=0;
static SRWLOCK trashLock=SRWLOCK_INIT;static std::vector<std::vector<unsigned char>> trash;static HANDLE trashEvent=nullptr;
static void Discard(std::vector<unsigned char>&v){if(v.capacity()<(4u<<20)||Off(OFF_TRASH)){std::vector<unsigned char>().swap(v);return;}
 if(!trashEvent){trashEvent=CreateEventW(nullptr,FALSE,FALSE,nullptr);if(!trashEvent){std::vector<unsigned char>().swap(v);return;}
  std::thread([]{SetThreadPriority(GetCurrentThread(),THREAD_PRIORITY_BELOW_NORMAL);for(;;){WaitForSingleObject(trashEvent,INFINITE);std::vector<std::vector<unsigned char>> mine;AcquireSRWLockExclusive(&trashLock);mine.swap(trash);ReleaseSRWLockExclusive(&trashLock);}}).detach();}
 AcquireSRWLockExclusive(&trashLock);trash.emplace_back();trash.back().swap(v);ReleaseSRWLockExclusive(&trashLock);SetEvent(trashEvent);}
// A big copy (an other-quality copy, a cached decode: 23 MB, 1.8 ms on one core) in eight parts on the band workers.
static void ParallelCopy(unsigned char*d,const unsigned char*s,size_t n){if(n<(4u<<20)||Off(OFF_PAR)){memcpy(d,s,n);return;}struct Job{unsigned char*d;const unsigned char*s;size_t n;} j{d,s,n};
 BandsRun(8,[](void*p,int k){auto&j=*(Job*)p;size_t a=size_t(uint64_t(j.n)*k/8),e=size_t(uint64_t(j.n)*(k+1)/8);memcpy(j.d+a,j.s+a,e-a);},&j);}
static void Recycle(std::vector<unsigned char>&v){if(v.empty())return;if(!Off(OFF_POOL)&&v.size()>=(1u<<20)&&spareBytes+v.size()<=(192ull<<20)){spareBytes+=v.size();spare.emplace_back();spare.back().swap(v);}else Discard(v);}
// v (empty) becomes an n-byte buffer whose old contents are left as they are: the caller overwrites all of it.
static void Reuse(std::vector<unsigned char>&v,size_t n){for(size_t i=spare.size();i-->0;)if(spare[i].size()==n){spareBytes-=n;v.swap(spare[i]);spare.erase(spare.begin()+i);hSpareHit++;return;}hSpareMiss++;v.resize(n);}
static void ForgetShadow(Bitmap*b){auto it=shadows.find(b);if(it==shadows.end())return;auto*victim=it->second.get();if(victim->job)Join(victim);SettleFor(victim);if(hitch&&logFile){char note[128];sprintf_s(note,"shadow_gone %p %dx%d fmt=%d alt=%d\n",(void*)b,b->w,b->h,b->format,!victim->alternate.empty());TraceNote(note);}for(auto&v:shadows)if(v.second->maskShadow==victim){v.second->maskShadow=nullptr;v.second->b.mask=nullptr;v.second->alternateBitmap.mask=nullptr;}used-=victim->pixels.size()+victim->snapshot.size()+victim->alternate.size();Recycle(victim->pixels);Recycle(victim->alternate);shadows.erase(it);}
// blank: the caller overwrites every 4x pixel next (a whole-picture decode, a Copy over all of a new bitmap), so the
// low-res picture is not upscaled first; only the snapshot is taken.
static Shadow* Get(Bitmap* b,Box box,bool create,bool useMask=false,bool blank=false){if(flowWarmStage==2)return nullptr;if(blank&&Off(OFF_BLANK))blank=false;if(!Valid(b))return nullptr;auto it=shadows.find(b);if(it!=shadows.end()){auto*s=it->second.get();if(s->job)Join(s);if(s->b.w!=b->w*4||s->b.h!=b->h*4||s->b.format!=b->format||s->snapshot.size()!=size_t(b->pitch)*b->h){if(logFile){fprintf(logFile,"shadow_recreated new=%d,%d,%d\n",b->w,b->h,b->format);fflush(logFile);}ForgetShadow(b);it=shadows.end();}}Shadow* s=nullptr;bool created=false;
 if(it==shadows.end()){if(!create)return nullptr;size_t pitch=((b->w*4*(b->format?1:3)+3)&~3);size_t n=pitch*b->h*4;if(n>512ull*1024*1024||used+n+size_t(b->pitch)*b->h>1400ull*1024*1024){if(logFile){fprintf(logFile,"shadow_limit used=%llu needed=%llu count=%u\n",used,uint64_t(n),unsigned(shadows.size()));fflush(logFile);}return nullptr;}
 auto u=std::make_unique<Shadow>();s=u.get();s->b=*b;s->b.w*=4;s->b.h*=4;s->b.pitch=int(pitch);uint64_t hit0=hSpareHit;Reuse(s->pixels,n);s->snapshot.resize(size_t(b->pitch)*b->h);
 if(hitch&&logFile){auto tag=assets.find(b);char note[384];sprintf_s(note,"shadow_new %p %dx%d fmt=%d blank=%d reused=%d name=%.200s\n",(void*)b,b->w,b->h,b->format,blank,hSpareHit!=hit0,tag!=assets.end()?tag->second.name.c_str():"");TraceNote(note);}s->b.pixels=s->pixels.data();s->b.handle=nullptr;s->b.prev=s->b.next=nullptr;
 s->info.bmiHeader={sizeof(BITMAPINFOHEADER),s->b.w,-s->b.h,1,WORD(b->format?8:24),BI_RGB,DWORD(n),0,0,0,0};s->b.info=&s->info;if(blank){memcpy(s->snapshot.data(),b->pixels,s->snapshot.size());s->blank=true;Dirty(s,{0,0,b->w,b->h});}else Nearest(s,b,{0,0,b->w,b->h},false);shadows[b]=std::move(u);used+=n+s->snapshot.size();created=true;hShadows++;
 }else{s=it->second.get();if(s->b.w!=b->w*4||s->b.h!=b->h*4||s->b.format!=b->format||s->snapshot.size()!=size_t(b->pitch)*b->h){if(logFile){fprintf(logFile,"shadow_mismatch old=%d,%d,%d new=%d,%d,%d ptr=%p\n",s->b.w,s->b.h,s->b.format,b->w*4,b->h*4,b->format,b);fflush(logFile);}return nullptr;}if(blank){SettleFor(s);memcpy(s->snapshot.data(),b->pixels,s->snapshot.size());s->blank=true;Dirty(s,{0,0,b->w,b->h});}else Nearest(s,b,box,true);}
 // The engine attaches a fresh matte after its named-image loader returns.
 // Cached RGB records may still contain the previous matte during decoding.
 if(created&&!decoding){auto tag=assets.find(b);uint64_t fp=0;if(tag!=assets.end()&&(fp=Fingerprint(b))==tag->second.hash){std::string name=tag->second.name;LoadHD(b,name.c_str(),fp);if(s->job)Join(s);}}   // the caller draws with it now
 s->age=++tick;s->b.palette=b->palette;s->b.mask=nullptr;s->maskShadow=nullptr;if(!decoding&&useMask&&b->mask&&b->mask!=b){auto m=Get(b->mask,box,true);if(m){s->b.mask=&m->b;s->maskShadow=m;}else return nullptr;}return s;}
static uint32_t Key(const char* name){wchar_t w[512];char raw[1024];if(!MultiByteToWideChar(932,0,name,-1,w,512))return 0;wchar_t* p=w;for(wchar_t* t=w;*t;t++)if(*t==L'\\'||*t==L'/')p=t+1;for(wchar_t* t=p;*t;t++)*t=(wchar_t)towlower(*t);if(!wcschr(p,L'.'))wcscat_s(w,512,L".rct");int n=WideCharToMultiByte(932,0,p,-1,raw,1024,nullptr,nullptr);if(n<=0)return 0;uint32_t crc=~0u;for(int i=0;i<n-1;i++){crc^=(unsigned char)raw[i];for(int k=0;k<8;k++)crc=(crc>>1)^(0xedb88320u&-(int)(crc&1));}uint32_t key=~crc;for(auto&a:uiAliases)if(key==a[0])return a[1];return key;}
static void EnsureAlternate(Shadow*s){if(s->alternate.empty()){HitchTime ht(hAltMs);hAltMade++;SettleFor(s);if(used+s->pixels.size()>1400ull*1024*1024)throw std::bad_alloc();Reuse(s->alternate,s->pixels.size());if(!s->blank)ParallelCopy(s->alternate.data(),s->pixels.data(),s->pixels.size());used+=s->alternate.size();}if(s->maskShadow)EnsureAlternate(s->maskShadow);}
static void DropAlternate(Shadow*s){HitchTime ht(hAltMs);hAltDropped++;SettleFor(s);used-=s->alternate.size();Recycle(s->alternate);}
// A shadow taken blank whose overwrite did not happen (a failed decode, no memory for the other-quality copy) gets the
// low-res picture upscaled after all.
static bool Fits(const Shadow*s,const Bitmap*b){return s->b.w==b->w*4&&s->b.h==b->h*4&&s->b.format==b->format;}   // 11-21: the engine can reuse a bitmap at another size while its decode is still out
static void Unblank(Shadow*s,Bitmap*b){if(s&&s->blank){s->blank=false;if(Fits(s,b))Nearest(s,b,{0,0,b->w,b->h},false);}}
static Bitmap AltBitmap(Shadow*s){s->alternateBitmap=s->b;if(!s->alternate.empty())s->alternateBitmap.pixels=s->alternate.data();if(s->maskShadow){AltBitmap(s->maskShadow);s->alternateBitmap.mask=&s->maskShadow->alternateBitmap;}return s->alternateBitmap;}
static void BasePixels(Shadow*s,Bitmap*b,std::vector<unsigned char>&out){if(!Fits(s,b)||out.size()<size_t(b->h)*4*s->b.pitch){if(logFile){fprintf(logFile,"base_pixels_stale bitmap=%dx%d shadow=%dx%d out=%zu\n",b->w,b->h,s->b.w,s->b.h,out.size());fflush(logFile);}return;}int ch=b->format?1:3;size_t span=size_t(b->w)*4*ch;
 std::vector<unsigned char> ref;bool check=parity&&logFile&&baseParity<10;if(check){ref=out;for(int y=0;y<b->h;y++)for(int x=0;x<b->w;x++){auto p=b->pixels+y*b->pitch+x*ch;for(int yy=0;yy<4;yy++){auto d=ref.data()+(y*4+yy)*s->b.pitch+x*4*ch;for(int xx=0;xx<4;xx++)memcpy(d+xx*ch,p,ch);}}}
 struct Job{Shadow*s;Bitmap*b;unsigned char*out;int ch;size_t span;int bands;} j{s,b,out.data(),ch,span,Off(OFF_PAR)||b->h<128?1:std::clamp(b->h/16,1,32)};   // row bands, like Nearest
 BandsRun(j.bands,[](void*p,int k){auto&j=*(Job*)p;for(int y=MulDiv(j.b->h,k,j.bands),y1=MulDiv(j.b->h,k+1,j.bands);y<y1;y++){auto d0=j.out+size_t(y*4)*j.s->b.pitch;
  Widen(d0,j.b->pixels+size_t(y)*j.b->pitch,j.b->w,j.ch);for(int yy=1;yy<4;yy++)memcpy(d0+size_t(yy)*j.s->b.pitch,d0,j.span);}},&j);
 if(check){baseParity++;fprintf(logFile,"perf_base_parity n=%d size=%dx%d equal=%d\n",baseParity,b->w,b->h,ref==out);fflush(logFile);}}
#include "artfile.inc"
static void HitchMemory();   // hitch.inc: the 32-bit address space next to the layer's own buffers (defined after the decode cache)
#include "hitch.inc"
// Decoded 4x art by asset key. Scene changes reload the same backgrounds and sprites over and over (one short test
// reloaded one background five times) and each PNG decode took 5-54 ms; the file never changes during a run, so the bytes
// are the decoder's own. The least recently used entry goes first past 256 MB.
struct Decoded {int w=0,h=0,format=0;std::vector<unsigned char> pixels;uint64_t used=0;bool ahead=false;};   // ahead: read ahead (prefetch.inc), not asked for yet
static std::unordered_map<uint32_t,Decoded> decodedArt;static size_t decodedBytes=0;static uint64_t decodedTick=0,pfHits=0,pfUnused=0;static int pfAhead=0;   // pfAhead: read ahead, not asked for yet
static const Decoded* CachedArt(uint32_t key,int w,int h,int format){auto it=decodedArt.find(key);if(it==decodedArt.end()||it->second.w!=w||it->second.h!=h||it->second.format!=format)return nullptr;if(it->second.ahead){it->second.ahead=false;pfHits++;pfAhead--;}it->second.used=++decodedTick;return &it->second;}
static bool CacheRoom(uint32_t key,size_t n){const size_t limit=256ull<<20;if(n>limit/4)return false;
 if(auto old=decodedArt.find(key);old!=decodedArt.end()){decodedBytes-=old->second.pixels.size();pfUnused+=old->second.ahead;pfAhead-=old->second.ahead;Recycle(old->second.pixels);decodedArt.erase(old);}
 while(decodedBytes+n>limit&&!decodedArt.empty()){auto lru=std::min_element(decodedArt.begin(),decodedArt.end(),[](const auto&a,const auto&c){return a.second.used<c.second.used;});decodedBytes-=lru->second.pixels.size();pfUnused+=lru->second.ahead;pfAhead-=lru->second.ahead;Recycle(lru->second.pixels);decodedArt.erase(lru);}
 return true;}
static void KeepArt(uint32_t key,int w,int h,int format,const std::vector<unsigned char>&px){if(!CacheRoom(key,px.size()))return;
 try{Decoded e;e.w=w;e.h=h;e.format=format;Reuse(e.pixels,px.size());ParallelCopy(e.pixels.data(),px.data(),px.size());e.used=++decodedTick;decodedBytes+=px.size();decodedArt.emplace(key,std::move(e));}catch(const std::bad_alloc&){}}
// a picture read ahead goes into the cache as it is (no copy)
static void KeepAhead(uint32_t key,int w,int h,int format,std::vector<unsigned char>&px){if(!CacheRoom(key,px.size()))return;
 try{Decoded e;e.w=w;e.h=h;e.format=format;e.pixels.swap(px);e.used=++decodedTick;e.ahead=true;size_t n=e.pixels.size();decodedArt.emplace(key,std::move(e));decodedBytes+=n;pfAhead++;}catch(const std::bad_alloc&){}}
static void HitchMemory(){if(!logFile)return;PROCESS_MEMORY_COUNTERS_EX pm{};pm.cb=sizeof(pm);K32GetProcessMemoryInfo(GetCurrentProcess(),(PROCESS_MEMORY_COUNTERS*)&pm,sizeof(pm));size_t largest=0,freeTotal=0;MEMORY_BASIC_INFORMATION mi{};
 for(uintptr_t a=0x10000;VirtualQuery((void*)a,&mi,sizeof(mi))==sizeof(mi);){if(mi.State==MEM_FREE){freeTotal+=mi.RegionSize;largest=std::max(largest,size_t(mi.RegionSize));}uintptr_t next=uintptr_t(mi.BaseAddress)+mi.RegionSize;if(next<=a)break;a=next;}
 fprintf(logFile,"hitch_memory private_mb=%u free_mb=%u largest_free_mb=%u shadows_mb=%u spare_mb=%u decoded_mb=%u\n",unsigned(pm.PrivateUsage>>20),unsigned(freeTotal>>20),unsigned(largest>>20),unsigned(used>>20),unsigned(spareBytes>>20),unsigned(decodedBytes>>20));}
#include "prefetch.inc"
// ------------------------------------------------------------------------------------------------ decoding off the game thread
// A load used to decode its 4x art on the spot (PNG 6-27 ms, JPEG XL 20-50 ms for 3200x2400) and a scene change loads
// several pictures in one frame (seven in 150 ms, hitch-read-loadfix). Now the shadow is taken blank, one of four workers
// decodes into it, and whoever needs the shadow next (a blit, a sync, a free, the quality switch) waits for it in Join, so
// the pictures of one frame decode side by side while the engine carries on. JPEG XL pictures take turns on the shared
// 16-thread runner; PNGs (single-threaded WIC) decode in parallel. The low-res fill of a CG's other quality and the copy
// for the decode cache are done in Join, on the band workers.
// patch: a standing picture's expression (hires-sprites.txt): its base's 4x (decoded here unless baseReady, then kept for the
// decode cache in basePixels) with the 4x of the changed box (hires-patch\<key>) laid over it
struct DecodeJob {Shadow*s=nullptr;Bitmap*b=nullptr;uint32_t key=0;int w=0,h=0,format=0,pitch=0;bool selectable=false,jxl=false,png=false,jxlFailed=false;
 wchar_t path[MAX_PATH]{},jpath[MAX_PATH]{};unsigned char*target=nullptr;size_t size=0;HRESULT hr=E_PENDING;const char*src="";double ms=0;LONGLONG submitted=0;HANDLE done=nullptr;
 bool patch=false,baseReady=false,ppng=false,pjxl=false;uint32_t baseKey=0;Box box{};wchar_t ppath[MAX_PATH]{},pjpath[MAX_PATH]{};std::vector<unsigned char> basePixels;};
static std::mutex jxlMutex;static SRWLOCK decodeLock=SRWLOCK_INIT;static CONDITION_VARIABLE decodeWake=CONDITION_VARIABLE_INIT;static std::vector<DecodeJob*> decodeQueue;static int decodeWorkers=0;
static void DecodeRun(DecodeJob&j){LONGLONG t=Now();HRESULT hr=E_FAIL;
 // background decodes run on below-normal threads (the 16-thread runner too), so they fill the gaps between the game's
 // frames instead of taking cores from the band workers; on the spot (RECON_OFF=async) it is the shared normal runner
 auto one=[&](bool jx,bool png,const wchar_t*jp,const wchar_t*pp,int w,int h,unsigned char*dst,int pitch,size_t size,bool&failed)->HRESULT{HRESULT r=E_FAIL;
  if(jx){std::lock_guard<std::mutex> one(jxlMutex);static LowPool pool;static int ready=-1;bool low=!Off(OFF_ASYNC);if(low&&ready<0)ready=LowStart(pool,16,THREAD_PRIORITY_BELOW_NORMAL);
   JxlArt art;if(art.Open(jp,w,h,j.format?1:3,low&&ready>0?LowRun:nullptr,low&&ready>0?&pool:nullptr))r=art.Finish(dst,pitch);if(FAILED(r))failed=true;else j.src="jxl";}
  if(FAILED(r)&&png){PngArt art;r=art.Open(pp,UINT(w),UINT(h),j.format);if(SUCCEEDED(r))r=art.CopyTo(dst,pitch,size);if(SUCCEEDED(r))j.src="png";}
  return r;};
 hr=j.patch&&j.baseReady?S_OK:one(j.jxl,j.png,j.jpath,j.path,j.w,j.h,j.target,j.pitch,j.size,j.jxlFailed);
 if(j.patch&&SUCCEEDED(hr)){if(!j.baseReady){try{j.basePixels.assign(j.target,j.target+j.size);}catch(const std::bad_alloc&){j.basePixels.clear();}}
  int pw=j.box.w*4,ph=j.box.h*4,pitch=(pw*3+3)&~3;std::vector<unsigned char> patch;bool failed=false;try{patch.resize(size_t(pitch)*ph);}catch(const std::bad_alloc&){hr=E_OUTOFMEMORY;}
  if(SUCCEEDED(hr))hr=one(j.pjxl,j.ppng,j.pjpath,j.ppath,pw,ph,patch.data(),pitch,patch.size(),failed);
  if(SUCCEEDED(hr)){int x0=j.box.x*4,y0=j.box.y*4,c0=std::max(0,-x0),c1=std::min(pw,j.w-x0);
   for(int r=0;r<ph;r++){int y=y0+r;if(y>=0&&y<j.h&&c1>c0)memcpy(j.target+size_t(y)*j.pitch+size_t(x0+c0)*3,patch.data()+size_t(r)*pitch+size_t(c0)*3,size_t(c1-c0)*3);}j.src="patch";}}
 j.hr=hr;j.ms=Ms(t);SetEvent(j.done);}
static DWORD WINAPI DecodeWorker(void*){SetThreadPriority(GetCurrentThread(),THREAD_PRIORITY_BELOW_NORMAL);CoInitializeEx(nullptr,COINIT_MULTITHREADED);
 for(;;){AcquireSRWLockExclusive(&decodeLock);while(decodeQueue.empty())SleepConditionVariableSRW(&decodeWake,&decodeLock,INFINITE,0);DecodeJob*j=decodeQueue.front();decodeQueue.erase(decodeQueue.begin());ReleaseSRWLockExclusive(&decodeLock);DecodeRun(*j);}}
static bool SubmitDecode(DecodeJob*j){if(!(j->done=CreateEventW(nullptr,TRUE,FALSE,nullptr)))return false;
 if(!decodeWorkers)for(int i=0;i<4;i++)if(HANDLE t=CreateThread(nullptr,0,DecodeWorker,nullptr,0,nullptr)){CloseHandle(t);decodeWorkers++;}
 if(!decodeWorkers){CloseHandle(j->done);j->done=nullptr;return false;}
 AcquireSRWLockExclusive(&decodeLock);decodeQueue.push_back(j);ReleaseSRWLockExclusive(&decodeLock);WakeConditionVariable(&decodeWake);return true;}
// A 4x UI mask can be opaque where its 1x mask is clear (255): Codex's 4K message-window masks have 3,000-11,000 such
// pixels around the Korean button labels, dark in the picture, and they showed as thin dark box lines the 1x screen does
// not have (the opening's sky, 10-25: 「실제 오프닝 부분 하늘 보면 검은색 사각형 무늬가 있어」). Every 4x mask is kept inside
// its 1x mask: where the 1x pixel is clear, its whole 4x4 block is clear. Partly clear 1x pixels keep the 4x detail.
// Authored 4x menu glyphs have their own validated coverage; clipping them to
// enlarged 1x glyphs destroys their strokes. Other masks retain the sky-artifact guard.
static bool AuthoredGlyphMask(uint32_t key){switch(key){case 0xb97b5455u:case 0xe07abd81u:case 0xfedb2e85u:case 0x66eecf2fu:case 0xc3bb0735u:case 0xadb21c8au:case 0x719bdb25u:case 0xb0b72c32u:case 0x4cfbf295u:case 0x7bebff97u:case 0x0b5b8845u:case 0xfd7f8d39u:case 0x363ba1f5u:case 0x36235e9cu:case 0xb46b3624u:case 0xc775ec49u:case 0xdff71c66u:case 0xc1be3669u:case 0xf2186fcbu:case 0x69de5283u:case 0x8eddee56u:case 0x22ce5072u:return true;default:return false;}}
static void ClipMaskToBase(Shadow*s,Bitmap*b,uint32_t key){if(AuthoredGlyphMask(key)||!b->format||s->b.w!=b->w*4||s->b.h!=b->h*4||s->pixels.empty())return;
 for(int y=0;y<b->h;y++){const unsigned char*r1=b->pixels+size_t(y)*b->pitch;
  for(int x=0;x<b->w;x++){if(r1[x]!=255)continue;for(int k=0;k<4;k++)memset(s->pixels.data()+size_t(y*4+k)*s->b.pitch+size_t(x)*4,255,4);}}}
static void Join(Shadow*s){DecodeJob*j=s->job;if(!j)return;s->job=nullptr;LONGLONG t=Now();WaitForSingleObject(j->done,INFINITE);double waited=Ms(t);CloseHandle(j->done);if(perf)pDecode+=waited;
 Bitmap*b=j->b;if(j->jxlFailed)JxlFailed(j->patch?j->baseKey:j->key,"decode");
 if(SUCCEEDED(j->hr)){auto&target=j->selectable&&!cg4k?s->alternate:s->pixels;if(j->selectable)BasePixels(s,b,cg4k?s->alternate:s->pixels);ClipMaskToBase(s,b,j->key);KeepArt(j->key,j->w,j->h,j->format,target);s->blank=false;
  if(j->patch&&!j->basePixels.empty())KeepArt(j->baseKey,j->w,j->h,j->format,j->basePixels);}   // the next expression of this base decodes only its patch
 else{Unblank(s,b);if(auto tag=assets.find(b);tag!=assets.end())tag->second.hd=false;if(j->selectable)cgApplyFailed=true;if(logFile){fprintf(logFile,"asset error %08x hr=%08lx\n",j->key,j->hr);fflush(logFile);}}
 if(perf&&logFile){fprintf(logFile,"perf_load key=%08x size=%dx%d cg=%d cached=0 src=%s decode=%.1f waited=%.1f since_load=%.1f\n",j->key,b->w,b->h,j->selectable,j->src,j->ms,waited,Ms(j->submitted));}
 delete j;}
static void JoinAll(){for(auto&a:shadows)if(a.second->job)Join(a.second.get());}
// fp: Fingerprint(b), computed once by the caller
// Standing pictures (tools/sprite_index.py -> hires-sprites.txt; the user, 10-25: 「인물 그림 4K를 바탕+얼굴 조각 방식으로
// 하자」): the game keeps an expression as its changed pixels over a base, so its 4x is the base's 4x with the 4x of the
// changed box laid over it (P <key> <base key> <x> <y> <w> <h>, 1x box, the patch in hires-patch\<key>); a mask is the 4x
// of the first mask with the same pixels (M <key> <file key>; gray 4x art was otherwise the UI's alone).
struct SpritePatch {uint32_t base;Box box;};static std::unordered_map<uint32_t,SpritePatch> spritePatches;static std::unordered_map<uint32_t,uint32_t> spriteMasks;
static void SpriteIndex(){static bool read=false;if(read)return;read=true;wchar_t p[MAX_PATH];swprintf_s(p,L"%s\\hires-sprites.txt",root);FILE*f=nullptr;if(_wfopen_s(&f,p,L"r")||!f)return;char line[160];
 while(fgets(line,sizeof line,f)){char kind=0;unsigned a=0,c=0;int x=0,y=0,w=0,h=0;
  if(line[0]=='P'&&sscanf_s(line,"%c %x %x %d %d %d %d",&kind,1,&a,&c,&x,&y,&w,&h)==7&&w>0&&h>0)spritePatches[a]={c,{x,y,w,h}};else if(line[0]=='M'&&sscanf_s(line,"%c %x %x",&kind,1,&a,&c)==3)spriteMasks[a]=c;}
 fclose(f);if(logFile){fprintf(logFile,"sprites patches=%zu masks=%zu\n",spritePatches.size(),spriteMasks.size());fflush(logFile);}}
static ULONGLONG titleShownTick=0;   // when a title picture was last drawn (flow.inc: was the story map opened at the title?)
static bool LoadHD(Bitmap* b,const char* name,uint64_t fp){if(flowWarmStage==2)return false;if(!Valid(b))return false;Init();SpriteIndex();uint32_t key=Key(name);
 auto sm=spriteMasks.find(key);uint32_t art=sm!=spriteMasks.end()?sm->second:key;auto sp=b->format?spritePatches.end():spritePatches.find(key);const SpritePatch*patch=sp!=spritePatches.end()?&sp->second:nullptr;
 if(b->format&&sm==spriteMasks.end()&&!std::binary_search(std::begin(uiGrayKeys),std::end(uiGrayKeys),key))return false;if(missing.count(key)||!wic)return false;
 uint32_t file=patch?patch->base:art;wchar_t path[MAX_PATH],jpath[MAX_PATH],ppath[MAX_PATH]{},pjpath[MAX_PATH]{};swprintf_s(path,L"%s\\hires\\%08x.png",root,file);swprintf_s(jpath,L"%s\\hires-jxl\\%08x.jxl",root,file);bool png=false,jx=JxlCurrent(file,jpath,path,png);
 bool ppng=false,pjx=false;if(patch){swprintf_s(ppath,L"%s\\hires-patch\\%08x.png",root,key);swprintf_s(pjpath,L"%s\\hires-patch\\%08x.jxl",root,key);pjx=JxlCurrent(key,pjpath,ppath,ppng);}
 if((!png&&!jx)||(patch&&!ppng&&!pjx)){missing.insert(key);return false;}   // an expression without its patch keeps its 1x, not its base's face
 Timing timer(pDecode);LONGLONG lt0=Now();int w=b->w*4,h=b->h*4;PrefetchClaim(key);PrefetchDrain();const Decoded* hit=CachedArt(art,w,h,b->format);bool selectable=IsCG(key)&&!Off(OFF_ALT);
 struct DecodeScope{DecodeScope(){decoding++;}~DecodeScope(){decoding--;}} decodeScope;   // Named loading can expose a cached RGB record before the caller replaces its old matte.
 // the decode (and for CGs the low-res fill of the other quality) writes every 4x pixel, so the shadow is taken blank
 auto s=Get(b,{0,0,b->w,b->h},true,false,true);if(!s)return false;struct BlankGuard{Shadow*s;Bitmap*b;~BlankGuard(){Unblank(s,b);}} guard{s,b};
 SettleFor(s);if(selectable)EnsureAlternate(s);else if(!s->alternate.empty())DropAlternate(s);auto&target=selectable&&!cg4k?s->alternate:s->pixels;
 if(hit){if(target.size()!=hit->pixels.size()){if(logFile){fprintf(logFile,"asset error %08x hr=%08lx\n",key,E_UNEXPECTED);fflush(logFile);}return false;}
  ParallelCopy(target.data(),hit->pixels.data(),target.size());if(selectable)BasePixels(s,b,cg4k?s->alternate:s->pixels);ClipMaskToBase(s,b,art);s->blank=false;
  if(perf&&logFile)fprintf(logFile,"perf_load key=%08x size=%dx%d cg=%d cached=1 src=cache ms=%.1f\n",key,b->w,b->h,selectable,Ms(lt0));}
 else{auto*j=new DecodeJob();j->s=s;j->b=b;j->key=art;j->w=w;j->h=h;j->format=b->format;j->pitch=s->b.pitch;j->selectable=selectable;j->jxl=jx;j->png=png;
  wcscpy_s(j->path,path);wcscpy_s(j->jpath,jpath);j->target=target.data();j->size=target.size();j->submitted=lt0;
  if(patch){j->patch=true;j->baseKey=patch->base;j->box=patch->box;j->ppng=ppng;j->pjxl=pjx;wcscpy_s(j->ppath,ppath);wcscpy_s(j->pjpath,pjpath);
   if(const Decoded*bh=CachedArt(patch->base,w,h,b->format);bh&&bh->pixels.size()==target.size()){ParallelCopy(target.data(),bh->pixels.data(),target.size());j->baseReady=true;}}   // its base was decoded for an earlier expression
  if(Off(OFF_ASYNC)){if(!(j->done=CreateEventW(nullptr,TRUE,FALSE,nullptr))){delete j;return false;}DecodeRun(*j);s->job=j;guard.s=nullptr;Join(s);}   // on the spot, as before
  else{if(!SubmitDecode(j)){delete j;return false;}   // the guard upscales the low-res picture instead
   s->job=j;guard.s=nullptr;}}   // the shadow stays blank until Join
 Dirty(s,{0,0,b->w,b->h});assets[b]={name,fp,true};loads++;if(key==0xef1f6a40u||key==0xd6925685u||key==0xc1e942c6u){titleReady=true;titleShownTick=GetTickCount64();}
 if(logFile){if(patch)fprintf(logFile,"asset %08x %dx%d -> %dx%d patch_on=%08x\n",key,b->w,b->h,w,h,patch->base);else if(art!=key)fprintf(logFile,"asset %08x %dx%d -> %dx%d file=%08x\n",key,b->w,b->h,w,h,art);
  else fprintf(logFile,"asset %08x %dx%d -> %dx%d\n",key,b->w,b->h,w,h);fflush(logFile);}return true;}
// Each shadow's quality copies swapped; sizes from the shadow itself, never its engine bitmap, which may be gone by now
// (11-25: a switch read a freed one and crashed).
static void ApplyCG(){if(!cgPending||flowWarmStage)return;JoinAll();SettleAll();auto t=Now();unsigned changed=0;if(cgDesired!=cg4k){for(auto&a:shadows){auto*s=a.second.get();if(s->alternate.empty())continue;s->pixels.swap(s->alternate);s->b.pixels=s->pixels.data();Dirty(s,{0,0,s->b.w/4,s->b.h/4});changed++;}cg4k=cgDesired;}cgPending=false;QualityStatus();InvalidateRect(game,nullptr,FALSE);if(logFile){fprintf(logFile,"cg_apply quality=%s source_count=%u failed=%d pending=0 ms=%.3f\n",cg4k?"4k":"base",changed,cgApplyFailed,Ms(t));fflush(logFile);}}
using LoadFn=Bitmap*(__cdecl*)(const char*);static LoadFn oldLoad,oldLoadDirect;
static ULONGLONG lastLoadTick=0;   // the last picture the engine asked for (flow.inc: a screen being rebuilt has settled)
static Bitmap* LoadCommon(LoadFn fn,const char* n){if(nesting)return fn(n);nesting++;HitchTime ht(hLoadMs);LONGLONG engineLoad=hitch?Now():0;Bitmap* b=fn(n);lastLoadTick=GetTickCount64();if(hitch)hEngLoadMs+=Ms(engineLoad);if(probe&&logFile){fprintf(logFile,"load call %s %dx%d\n",n,b?b->w:0,b?b->h:0);fflush(logFile);}{try{bool loaded=false;uint64_t fp=Valid(b)?Fingerprint(b):0;
  // The engine hands back the bitmap it already had (same name, same pixels): its shadow still holds the 4x art, and a CG
  // both qualities, so there is nothing to decode or copy again (a cached reload cost ~9 ms).
  if(Valid(b)){auto tag=assets.find(b);bool same=tag!=assets.end()&&Key(tag->second.name.c_str())==Key(n)&&tag->second.hash==fp;auto sh=same&&tag->second.hd?shadows.find(b):shadows.end();
   if(!Off(OFF_REUSE)&&sh!=shadows.end()&&(!IsCG(Key(n))||Off(OFF_ALT)||!sh->second->alternate.empty())){loaded=true;hLoadReuse++;sh->second->age=++tick;}else{if(!same)ForgetShadow(b);loaded=LoadHD(b,n,fp);}}
  if(!loaded&&hdPack&&Valid(b)&&IsCG(Key(n))&&flowWarmStage!=2){cgApplyFailed=true;if(logFile){fprintf(logFile,"required_asset_failed key=%08x name=%s format=%d used=%llu\n",Key(n),n,b->format,used);fflush(logFile);}}if(Valid(b))assets[b]={n,fp,loaded};if(Valid(b)&&!b->format)PrefetchAfter(Key(n));}catch(const std::bad_alloc&){cgApplyFailed=true;if(logFile)fprintf(logFile,"asset allocation fallback\n");}nesting--;}return b;}
static Bitmap* __cdecl Load(const char*n){return LoadCommon(oldLoad,n);}
static Bitmap* __cdecl LoadDirect(const char*n){return LoadCommon(oldLoadDirect,n);}
using FreeFn=int(__cdecl*)(Bitmap*,int);static FreeFn oldFree;
static int __cdecl Free(Bitmap* b,int force){if(b && !force && b->keep)return oldFree(b,force);HitchTime ht(hFreeMs);assets.erase(b);ForgetShadow(b);return oldFree(b,force);}
using CopyFn=void(__cdecl*)(Bitmap*,Box*,Bitmap*,Box*);using AlphaFn=void(__cdecl*)(Bitmap*,Box*,Bitmap*,Box*,int);using TransformFn=void(__cdecl*)(Bitmap*,Box*,Bitmap*,Box*,double,double,double);
static CopyFn oldCopy,oldSwap;static AlphaFn oldAlpha,oldMask;static TransformFn oldTransform;
// One large 4x Copy/Mask/Alpha blit split into row bands over persistent workers. The engine's loops (0x442870, 0x440640,
// 0x443180 and their callees) touch no globals; Alpha's MMX path reads a CPU-feature flag that 0x4461b0 sets once to the
// same value, and ends with emms. A chronicle frame issues ~270 Mask blits, so dispatch must cost microseconds: workers
// spin briefly after a job, then park. The ticket packs generation|bands|next, so a band runs exactly once.
static int bandSpin=20000;   // spins before a worker parks; RECON_SPIN=n for timing runs
struct BandPool {
 std::atomic<uint64_t> ticket{0};std::atomic<int> remaining{0};void(*run)(void*,int)=nullptr;void*ctx=nullptr;uint32_t gen=0;int workers=0;bool started=false;
 static uint32_t Gen(uint64_t t){return uint32_t(t>>32);}static int Bands(uint64_t t){return int((t>>16)&0xffff);}static int Next(uint64_t t){return int(t&0xffff);}
 void Start(){started=true;wchar_t v[16]{};if(GetEnvironmentVariableW(L"RECON_SPIN",v,16))bandSpin=std::max(1,_wtoi(v));int n=int(std::thread::hardware_concurrency());workers=std::clamp(n-2,0,std::max(7,n/2-1));for(int i=0;i<workers;i++)std::thread([this]{Loop();}).detach();}   // up to one per physical core on big machines
 bool Take(uint32_t g){uint64_t t=ticket.load(std::memory_order_acquire);for(;;){if(Gen(t)!=g||Next(t)>=Bands(t))return false;
  if(ticket.compare_exchange_weak(t,t+1,std::memory_order_acq_rel,std::memory_order_acquire)){run(ctx,Next(t));remaining.fetch_sub(1,std::memory_order_acq_rel);return true;}}}
 void Loop(){uint32_t seen=0;for(;;){uint64_t t;int spins=0;while(Gen(t=ticket.load(std::memory_order_acquire))==seen){if(++spins<bandSpin)YieldProcessor();else{WaitOnAddress((volatile VOID*)&ticket,&t,sizeof(t),INFINITE);spins=0;}}seen=Gen(t);while(Take(seen)){}}}
 void Run(int n,void(*fn)(void*,int),void*c){run=fn;ctx=c;remaining.store(n,std::memory_order_relaxed);ticket.store((uint64_t(++gen)<<32)|(uint64_t(n)<<16),std::memory_order_release);WakeByAddressAll((PVOID)&ticket);
  while(Take(gen)){}while(remaining.load(std::memory_order_acquire)>0)YieldProcessor();}
};
static BandPool bandPool;static int bandParity[3]{};   // per kind: Copy, Mask, Alpha
static void BandsRun(int bands,void(*fn)(void*,int),void*ctx){if(bands>=2&&!bandPool.started)bandPool.Start();if(bands<2||!bandPool.workers){for(int k=0;k<bands;k++)fn(ctx,k);return;}bandPool.Run(bands,fn,ctx);}
struct BandBlit {CopyFn copy;AlphaFn alpha;Bitmap*a;Bitmap*b;Box x,y;int t,bands;};
static void BandRun(void*p,int k){auto&j=*(BandBlit*)p;int r0=MulDiv(j.x.h,k,j.bands),r1=MulDiv(j.x.h,k+1,j.bands);Box bx{j.x.x,j.x.y+r0,j.x.w,r1-r0},by{j.y.x,j.y.y+r0,j.y.w,r1-r0};
 if(j.copy)j.copy(j.a,&bx,j.b,&by);else j.alpha(j.a,&bx,j.b,&by,j.t);}
static void Single(const BandBlit&j){Box x=j.x,y=j.y;if(j.copy)j.copy(j.a,&x,j.b,&y);else j.alpha(j.a,&x,j.b,&y,j.t);}
static std::vector<BYTE> Rows(Bitmap*b,int y,int h){std::vector<BYTE> v;if(b&&b->pixels&&y>=0&&h>0&&y+h<=b->h)v.assign(b->pixels+size_t(y)*b->pitch,b->pixels+size_t(y+h)*b->pitch);return v;}
static void PutRows(Bitmap*b,int y,const std::vector<BYTE>&v){if(!v.empty())memcpy(b->pixels+size_t(y)*b->pitch,v.data(),v.size());}
// Big blits between different bitmaps run as bands; small or same-bitmap ones stay on this thread. The first 40 banded
// blits of each kind in a perf run also run single-threaded from the same start and must match byte for byte (pixels, mask).
static void Banded(CopyFn copy,AlphaFn alpha,Bitmap*a,Box x,Bitmap*b,Box y,int t){
 int64_t px=int64_t(x.w)*x.h;BandBlit j{copy,alpha,a,b,x,y,t,a==b||a->pixels==b->pixels||(a->mask&&b->mask&&a->mask->pixels==b->mask->pixels)?1:int(std::min<int64_t>({px/24576,int64_t(x.h)/16,8}))};   // smaller cut-offs measured slower (dispatch, contention)
 if(j.bands>=2&&!bandPool.started)bandPool.Start();if(j.bands<2||!bandPool.workers){Single(j);return;}
 int kind=copy?0:alpha==oldAlpha?2:1;if(!parity||bandParity[kind]>=40){bandPool.Run(j.bands,BandRun,&j);return;}
 auto p0=Rows(b,y.y,y.h),m0=Rows(b->mask,y.y,y.h);bandPool.Run(j.bands,BandRun,&j);auto p1=Rows(b,y.y,y.h),m1=Rows(b->mask,y.y,y.h);
 PutRows(b,y.y,p0);PutRows(b->mask,y.y,m0);Single(j);bool same=p1==Rows(b,y.y,y.h)&&m1==Rows(b->mask,y.y,y.h);bandParity[kind]++;
 if(logFile){fprintf(logFile,"perf_band_parity n=%d kind=%c bands=%d size=%dx%d mask=%d equal=%d\n",bandParity[kind],"CMA"[kind],j.bands,x.w,x.h,b->mask!=nullptr,same);fflush(logFile);}}
static Box Scale(Box r){return {r.x*4,r.y*4,r.w*4,r.h*4};}
// cover: the blit is a Copy over all of b, so a new shadow for b is taken blank (no upscale it would overwrite at once).
static bool Pair(Bitmap* a,Box* ar,Bitmap* b,Box* br,Shadow*& sa,Shadow*& sb,bool swap=false,bool useMask=false,bool cover=false,bool transform=false){
 // Transform's destination box describes its centre, not a pre-clipped blit. The modal sprite uses a
 // 596x596 box at (0,-33) even when settled. The engine clips it internally (0x4437a1..0x4437ef);
 // rejecting it here discarded every 4x glyph/plate. Get clips only the synchronization region;
 // preserve the original box for the transform itself so clipping cannot move its centre.
 if(flowWarmStage==2)return false;
 if(!Valid(a)||!Valid(b)||ar->x<0||ar->y<0||ar->w<0||ar->h<0||ar->x+ar->w>a->w||ar->y+ar->h>a->h)return false;
 if(!transform&&(br->x<0||br->y<0||br->x+br->w>b->w||br->y+br->h>b->h))return false;
 if(transform){Box visible=Clip(b,*br);if(visible.w<=0||visible.h<=0)return false;}
 if(!shadows.count(a)&&!shadows.count(b))return false;bool fresh=cover&&!shadows.count(b);sa=Get(a,*ar,true,useMask);sb=Get(b,*br,true,useMask,fresh&&sa!=nullptr);
 if(sa&&sb){try{if(!sa->alternate.empty()||!sb->alternate.empty()){EnsureAlternate(sb);if(swap||!sa->alternate.empty())EnsureAlternate(sa);}}catch(...){Unblank(sb,b);throw;}return true;}cgApplyFailed=true;return false;}
// perf only: every top-level blit of one idle chronicle frame (the one after present 150): what does the script redraw?
static void TraceBlit(char kind,Bitmap*a,const Box&ar,Bitmap*b,const Box&br,int t){if(!perf||!logFile||(pPresent!=150&&!traceFrames&&!traceRecord))return;Bitmap*screen=*(Bitmap**)0x56a6a8;auto named=assets.find(a);auto sa=shadows.find(a),sb=shadows.find(b);bool altA=sa!=shadows.end()&&!sa->second->alternate.empty(),altB=sb!=shadows.end()&&!sb->second->alternate.empty();
 char note[512];sprintf_s(note,"trace %c src=%p %dx%d box=%d,%d,%d,%d dst=%s%p %dx%d at=%d,%d t=%d shadows=%d%d alt=%d%d mask=%d name=%.200s\n",kind,(void*)a,a->w,a->h,ar.x,ar.y,ar.w,ar.h,b==screen?"SCREEN ":"",(void*)b,b->w,b->h,br.x,br.y,t,sa!=shadows.end(),sb!=shadows.end(),altA,altB,a->mask!=nullptr,named!=assets.end()?named->second.name.c_str():"");TraceNote(note);}
static void __cdecl Copy(Bitmap* a,Box* ar,Bitmap* b,Box* br){Box target{br->x,br->y,ar->w,ar->h};br=&target;if(nesting){oldCopy(a,ar,b,br);return;}TraceBlit('C',a,*ar,b,*br,0);nesting++;HitchTime hook(hHookMs);Shadow *sa=nullptr,*sb=nullptr;bool hd=false,deferred=false;bool cover=a!=b&&a->pixels!=b->pixels&&br->x==0&&br->y==0&&ar->w==b->w&&ar->h==b->h;try{HitchTime pair(hPairMs);hd=Pair(a,ar,b,br,sa,sb,false,false,cover);}catch(const std::bad_alloc&){cgApplyFailed=true;}if(hd){BlitTiming timer('C',ar->w,ar->h);Box x=Scale(*ar),y=Scale(*br);if(!(deferred=Defer('C',a,b,sa,sb,x,y,0))){Banded(oldCopy,nullptr,&sa->b,x,&sb->b,y,0);if(!sa->alternate.empty()||!sb->alternate.empty()){auto aa=AltBitmap(sa),bb=AltBitmap(sb);Banded(oldCopy,nullptr,&aa,x,&bb,y,0);}}sb->blank=false;blits++;}{HitchTime engine(hEngBlitMs);oldCopy(a,ar,b,br);}if(hd){HitchTime snap(hSnapMs);Snapshot(sb,b,*br);if(sa!=sb&&sa->alternate.empty()&&br->x==0&&br->y==0&&ar->w==b->w&&ar->h==b->h&&!sb->alternate.empty())DropAlternate(sb);}nesting--;}
static void __cdecl Swap(Bitmap* a,Box* ar,Bitmap* b,Box* br){Box target{br->x,br->y,ar->w,ar->h};br=&target;if(nesting){oldSwap(a,ar,b,br);return;}nesting++;Shadow *sa=nullptr,*sb=nullptr;bool hd=false;try{hd=Pair(a,ar,b,br,sa,sb,true);}catch(const std::bad_alloc&){cgApplyFailed=true;}if(hd){BlitTiming timer('S',ar->w,ar->h);Box x=Scale(*ar),y=Scale(*br);SettleAll();oldSwap(&sa->b,&x,&sb->b,&y);if(!sa->alternate.empty()||!sb->alternate.empty()){auto aa=AltBitmap(sa),bb=AltBitmap(sb);oldSwap(&aa,&x,&bb,&y);}blits++;}oldSwap(a,ar,b,br);if(hd){Snapshot(sa,a,*ar);Snapshot(sb,b,*br);}nesting--;}
static void AlphaCommon(AlphaFn fn,Bitmap* a,Box* ar,Bitmap* b,Box* br,int alpha){Box target{br->x,br->y,ar->w,ar->h};br=&target;if(nesting){fn(a,ar,b,br,alpha);return;}if(b==*(Bitmap**)0x56a6a8)screenDrawn=true;hAlphas++;
 TraceBlit(fn==oldAlpha?'A':'M',a,*ar,b,*br,alpha);nesting++;HitchTime hook(hHookMs);Shadow *sa=nullptr,*sb=nullptr;bool hd=false,deferred=false;try{HitchTime pair(hPairMs);hd=Pair(a,ar,b,br,sa,sb,false,fn==oldMask);}catch(const std::bad_alloc&){cgApplyFailed=true;}if(hd){BlitTiming timer(fn==oldAlpha?'A':'M',ar->w,ar->h);Box x=Scale(*ar),y=Scale(*br);auto blit=[&](Bitmap*p,Bitmap*q){Banded(nullptr,fn,p,x,q,y,alpha);};
  if(!(deferred=Defer(fn==oldAlpha?'A':'M',a,b,sa,sb,x,y,alpha))){blit(&sa->b,&sb->b);if(!sa->alternate.empty()||!sb->alternate.empty()){auto aa=AltBitmap(sa),bb=AltBitmap(sb);blit(&aa,&bb);}}blits++;}{HitchTime engine(hEngBlitMs);fn(a,ar,b,br,alpha);}if(hd){HitchTime snap(hSnapMs);Snapshot(sb,b,*br);if(fn==oldMask&&b->mask){auto m=shadows.find(b->mask);if(m!=shadows.end())Snapshot(m->second.get(),b->mask,*br);}}nesting--;}
static void __cdecl Alpha(Bitmap*a,Box*x,Bitmap*b,Box*y,int t){AlphaCommon(oldAlpha,a,x,b,y,t);}static void __cdecl Mask(Bitmap*a,Box*x,Bitmap*b,Box*y,int t){AlphaCommon(oldMask,a,x,b,y,t);}
static void __cdecl Transform(Bitmap*a,Box*x,Bitmap*b,Box*y,double angle,double sx,double sy){if(nesting){oldTransform(a,x,b,y,angle,sx,sy);return;}if(b==*(Bitmap**)0x56a6a8)screenDrawn=true;nesting++;Shadow *sa=nullptr,*sb=nullptr;bool hd=false;try{hd=Pair(a,x,b,y,sa,sb,false,true,false,true);}catch(const std::bad_alloc&){cgApplyFailed=true;}if(hd){if(perf&&logFile&&(y->x<0||y->y<0||y->x+y->w>b->w||y->y+y->h>b->h)){static int count=0;if(count++<32){fprintf(logFile,"transform4k clipped_target src=%dx%d dst=%dx%d box=%d,%d,%d,%d scale=%.3f,%.3f\n",a->w,a->h,b->w,b->h,y->x,y->y,y->w,y->h,sx,sy);fflush(logFile);}}BlitTiming timer('T',x->w,x->h);Box xx=Scale(*x),yy=Scale(*y);SettleAll();oldTransform(&sa->b,&xx,&sb->b,&yy,angle,sx,sy);if(!sa->alternate.empty()||!sb->alternate.empty()){auto aa=AltBitmap(sa),bb=AltBitmap(sb);oldTransform(&aa,&xx,&bb,&yy,angle,sx,sy);}blits++;}oldTransform(a,x,b,y,angle,sx,sy);if(hd){Snapshot(sb,b,*y);if(b->mask){auto m=shadows.find(b->mask);if(m!=shadows.end())Snapshot(m->second.get(),b->mask,*y);}}nesting--;}
static HWND Game(){return ((HWND(__cdecl*)())0x43aa00)();}
struct View {int x,y,w,h;};static View Viewport(HWND hwnd){RECT r{};GetClientRect(hwnd,&r);int w=r.right,h=r.bottom;if(w*3>h*4)w=h*4/3;else h=w*3/4;return {(r.right-w)/2,(r.bottom-h)/2,w,h};}
static bool chronicleOpen=false;   // the game's 연표 script is up (defer.inc); the 연표 view (chronicle_proto.inc) covers it
namespace cproto{void Tick();void Frame();bool Shown();bool Covered();bool MapUp();}   // chronicle_proto.inc: the 연표 view
static void ToLogical(const View&v,int&x,int&y){x=(int)floor(double(x-v.x)*800/std::max(1,v.w));y=(int)floor(double(y-v.y)*600/std::max(1,v.h));}
static void ToPhysical(const View&v,LONG&x,LONG&y){x=v.x+(int)ceil(double(x)*v.w/800);y=v.y+(int)ceil(double(y)*v.h/600);}
static BOOL WINAPI Invalidate(HWND h,const RECT* r,BOOL erase){if(r&&h==Game()){auto v=Viewport(h);RECT z{v.x+MulDiv(r->left,v.w,800),v.y+MulDiv(r->top,v.h,600),v.x+(int)ceil(double(r->right)*v.w/800),v.y+(int)ceil(double(r->bottom)*v.h/600)};return InvalidateRect(h,&z,erase);}return InvalidateRect(h,r,erase);}
static BOOL WINAPI ToClient(HWND h,LPPOINT p){BOOL ok=ScreenToClient(h,p);if(ok&&h==Game()){auto v=Viewport(h);int x=p->x,y=p->y;ToLogical(v,x,y);p->x=x;p->y=y;}return ok;}
static BOOL WINAPI ToScreen(HWND h,LPPOINT p){if(h==Game()){auto v=Viewport(h);ToPhysical(v,p->x,p->y);}return ClientToScreen(h,p);}
// The chronicle drags with the cursor clipped to ClientToScreen(0,0) plus the engine's 800x600 size, which in HD was an
// 800x600 box of physical pixels at the viewport's corner. Map the logical box onto the viewport. Probe runs never clip.
static BOOL WINAPI ClipToGame(const RECT* r){HWND g=Game();if(!r||!g)return ClipCursor(r);POINT o{0,0};ToScreen(g,&o);POINT a{r->left-o.x,r->top-o.y},b{r->right-o.x+1,r->bottom-o.y+1};ToScreen(g,&a);ToScreen(g,&b);RECT s{a.x,a.y,b.x,b.y};
 if(logFile){fprintf(logFile,"clip_cursor logical=%ld,%ld,%ld,%ld screen=%ld,%ld,%ld,%ld\n",r->left-o.x,r->top-o.y,r->right-o.x+1,r->bottom-o.y+1,s.left,s.top,s.right,s.bottom);fflush(logFile);}
 return probe?TRUE:ClipCursor(&s);}
// Legacy input callback 41b560 reads WM_MOUSEMOVE LPARAM directly at 41ba00.
// It rejects physical coordinates >=800x600 before hit testing; convert at this consumer.
static bool FCBlockInput(UINT);
static bool ConsoleKey(UINT msg,WPARAM wp,LPARAM lp);   // below, after the VM variables
static bool BacklogKey(UINT msg,WPARAM wp,LPARAM lp);static void BacklogJump();static void BacklogLeft();   // backlog.inc
using InputFn=int(__cdecl*)(HWND,UINT,WPARAM,LPARAM);static InputFn oldInput;
static int __cdecl Input(HWND h,UINT msg,WPARAM wp,LPARAM lp){
 if(h==Game()&&FCBlockInput(msg))return 1;
 if(h==Game()&&(BacklogKey(msg,wp,lp)||ConsoleKey(msg,wp,lp)))return 1;
 if(h==Game()&&((msg>=WM_MOUSEMOVE&&msg<=WM_MBUTTONDBLCLK)||(msg>=WM_XBUTTONDOWN&&msg<=WM_XBUTTONDBLCLK))){
  auto v=Viewport(h);int x=(short)LOWORD(lp),y=(short)HIWORD(lp);
  ToLogical(v,x,y);
  lp=MAKELPARAM((WORD)(short)x,(WORD)(short)y);
 }
 return oldInput(h,msg,wp,lp);
}

// Review unlock uses virtual integer records, never writes completion flags to the save table.
static const uint32_t reviewIds[]={0xa23038c5,0xaf541358,0x948dd22a,0xe644c876,0xc177171a,0x38f5e23c};
struct Variable {uint32_t hash,type,scope;int value;};static_assert(sizeof(Variable)==16,"VM variable ABI");
static Variable flowFast{0xb32354beu,0,0,0},flowMark{0x22e2e43eu,0,0,0};static Variable reviewVars[6]{};static Variable configVisibleVar{0xfe9ea26bu,0,0,0};
static Variable* ReviewVar(uint32_t hash){if(!reviewEnabled)return nullptr;for(unsigned i=0;i<6;i++)if(reviewIds[i]==hash){reviewVars[i]={hash,0,0,1};return &reviewVars[i];}return nullptr;}
// 연표: chronicle.mjo's display reads of its cell table (bit 0 hidden, bit 1 link locked) are ANDed with this (build_storymap
// review_chronicle), so with the review unlock on every cell reads as open. The saved table itself is never touched.
static Variable reviewChronicle{0x8763b40au,0,0,-1};
static Variable* ReviewChronicle(uint32_t hash){if(hash!=reviewChronicle.hash)return nullptr;reviewChronicle.value=reviewEnabled?~3:-1;return &reviewChronicle;}
static Variable* FCVar(uint32_t,const Variable*);
static bool FCReplaying();   // flow.inc: a story flow replay is on
using VarFn=Variable*(__cdecl*)(Variable*,short*);using VarHashFn=Variable*(__cdecl*)(uint32_t);static VarFn oldVarFind,oldVarWrite;static VarHashFn oldVarHash;
static void ChoiceAtWait(Variable*v);         // a choice waiting for the pause loop (below)
static Variable* __cdecl VarFind(Variable*v,short*index){if(v&&v->scope==0){if(auto p=FCVar(v->hash,nullptr))return p;if(v->hash==flowFast.hash)return &flowFast;if(v->hash==flowMark.hash)return &flowMark;if(v->hash==configVisibleVar.hash)return &configVisibleVar;if(auto p=ReviewVar(v->hash))return p;if(auto p=ReviewChronicle(v->hash))return p;}Variable*p=oldVarFind(v,index);ChoiceAtWait(p);return p;}
static bool MapTabPressed(const Variable*v);   // the text box's 「지도」 button (below)
static void ReplayNoSave(Variable*v);         // a save or load chosen in a replay (below)
static Variable* __cdecl VarWrite(Variable*v,short*index){if(MapTabPressed(v))return oldVarWrite(v,index);ReplayNoSave(v);if(v&&v->scope==0){if(auto p=FCVar(v->hash,v))return p;if(v->hash==flowFast.hash){flowFast.value=v->value;flowWarmStage=v->value;return &flowFast;}if(v->hash==flowMark.hash){flowMark.value=v->value;flowArriveTick=GetTickCount64();if(v->value>0){SetWindowTextW(Game(),L"레콘키스타 · 검수용 재생 (F11: 이야기 흐름)");if(forceStartupFullscreen){forceStartupFullscreen=false;PostMessageW(Game(),WM_KEYDOWN,VK_F4,0);}}if(logFile){fprintf(logFile,"flow_arrived=%d fast=%d\n",v->value,flowFast.value);fflush(logFile);}return &flowMark;}if(v->hash==configVisibleVar.hash){configVisibleVar.value=v->value;PostMessageW(Game(),WM_APP+81,0,0);return &configVisibleVar;}if(auto p=ReviewVar(v->hash))return p;}return oldVarWrite(v,index);}
static Variable* __cdecl VarHash(uint32_t hash){if(auto p=FCVar(hash,nullptr))return p;if(hash==flowFast.hash)return &flowFast;if(hash==flowMark.hash)return &flowMark;if(hash==configVisibleVar.hash)return &configVisibleVar;if(auto p=ReviewVar(hash))return p;if(auto p=ReviewChronicle(hash))return p;return oldVarHash(hash);}
static Variable* VarOf(uint32_t hash){return oldVarHash?oldVarHash(hash):nullptr;}   // a VM variable by its hash, the engine's own lookup
// The text box's buttons by key (11-25, the user: 「플레이 창에서 단축키로 게임 조작 가능하게. 지금은 하단 커맨드들은
// 마우스로만 작동해」): a key is a choice the way console.mjo's own non-button handlers ($lclick/$rclick/$mroll@CONSOLE)
// make one: @ret the button's id, @is_select 2. The pause loop then runs that button's case; with 2 (not a button's 1) it
// skips the press and release art, which reads the hovered button's @no/@lx/@ly (a 1 without a hover crashed the engine,
// 11-25). Only while the pause loop waits (@is_select 0, set_pausebutton_menu). S is console.mjo's case 12 (tools/
// build_console.py: the next empty slot, as the save menu numbers them). M opens the story map.
// The text box's 「지도」 button (tools/build_console.py: console.mjo's button 11, left of 퀵 저장): its $click@CONSOLE writes
// @ret 11 after @is_select 1. That choice is taken back (@is_select 0, the pause loop goes on waiting) and the story map
// opens through the map's own menu command, once the script has returned to its wait.
static bool MapTabPressed(const Variable*v){if(!v||v->hash!=0xcaceeb7fu||v->value!=11)return false;if(Variable*sel=VarOf(0x405ba90fu))sel->value=0;
 PostMessageW(Game(),WM_COMMAND,0x7e43,0);if(logFile){fprintf(logFile,"console_map_tab\n");fflush(logFile);}return true;}
static void OpenFlowChart();
// No saving or loading during a story flow replay (11-25, the user: 「다시보기에선 세이브 로드 기능을 비활성화 시키는게
// 좋겠어」): the text box's save and load choices (불러오기 1, 퀵 저장 8, 퀵 로드 9, 저장 12; by button, $click@CONSOLE's
// @ret, or by key, ConsoleChoose) become case 13, where the game's own message box says they cannot be used now
// (tools/build_console.py save_case).
static bool SaveLoadChoice(int id){return id==1||id==8||id==9||id==12;}
static void ReplayNoSave(Variable*v){if(!v||v->hash!=0xcaceeb7fu||!SaveLoadChoice(v->value)||!FCReplaying())return;if(logFile){fprintf(logFile,"console_replay_no_save id=%d%c",v->value,10);fflush(logFile);}v->value=13;}
#include "auto_rate.inc"
static const struct ConsoleKeyButton{WPARAM vk;int id;}consoleKeys[]={{'S',12},{'Q',8},{'W',9},{'L',1},{'A',2},{VK_PRIOR,6},{VK_ESCAPE,7}};   // 빈 칸 저장, 퀵 저장, 퀵 로드, 불러오기, 자동, 기록, 설정 (written on the buttons, tools/build_console.py LABELS)
// A choice made for the pause loop: now if it waits (@is_select 0), else, if later is asked (the story map's 「연표」: the
// map closes while the script is still on its way back to the loop), at its next wait: when the loop reads @is_select 0
// (VarFind; only the pause loop reads it, console.mjo 1fd318c6), that 0 becomes the choice, within 3 s. (Not at the write of
// that 0: on 11-25 a choice put there was gone
// again before the loop read it.)
static int choiceLater=0;static ULONGLONG choiceAt=0;
static bool ConsoleChoose(int id,bool later){Variable*sel=VarOf(0x405ba90fu),*ret=VarOf(0xcaceeb7fu);if(!sel||!ret)return false;if(SaveLoadChoice(id)&&FCReplaying())id=13;
 if(sel->value==0){ret->value=id;sel->value=2;return true;}if(!later)return false;choiceLater=id;choiceAt=GetTickCount64();return true;}
static void ChoiceAtWait(Variable*v){if(!v||v->hash!=0x405ba90fu||v->value!=0)return;BacklogLeft();if(!choiceLater)return;int id=choiceLater;choiceLater=0;if(GetTickCount64()-choiceAt>3000)return;
 if(Variable*ret=VarOf(0xcaceeb7fu)){ret->value=id;v->value=2;if(logFile){fprintf(logFile,"console_choice id=%d at_wait%c",id,10);fflush(logFile);}}}
static bool ConsoleKey(UINT msg,WPARAM wp,LPARAM lp){if(msg!=WM_KEYDOWN||(lp&(1L<<30)))return false;
 if(wp=='M'){OpenFlowChart();return true;}
 if(wp=='A'&&AutoOn()){AutoRateStep();return true;}   // auto runs: its rate (auto_rate.inc)
 for(auto&k:consoleKeys){if(k.vk!=wp)continue;if(!ConsoleChoose(k.id,false))return false;if(logFile){fprintf(logFile,"console_key vk=%02x id=%d%c",unsigned(wp),k.id,10);fflush(logFile);}return true;}
 return false;}
// The chronicle's scroll position (x $4d7f11ee max $704d8d29, y $b1fffe23 max $d95c0a13) set at once, any glide stopped.
static bool ChroniclePosition(int*x,int*y,int*xmax,int*ymax){if(!oldVarHash)return false;Variable *vx=oldVarHash(0x4d7f11eeu),*vy=oldVarHash(0xb1fffe23u),*mx=oldVarHash(0x704d8d29u),*my=oldVarHash(0xd95c0a13u);
 if(!vx||!vy||!mx||!my)return false;if(x)*x=vx->value;if(y)*y=vy->value;if(xmax)*xmax=mx->value;if(ymax)*ymax=my->value;return true;}
static bool ChronicleMoveTo(int x,int y){if(!oldVarHash)return false;Variable *vx=oldVarHash(0x4d7f11eeu),*vy=oldVarHash(0xb1fffe23u),*mx=oldVarHash(0x704d8d29u),*my=oldVarHash(0xd95c0a13u),*tx=oldVarHash(0x1d19c016u),*ty=oldVarHash(0xdc971fd6u);
 if(!vx||!vy||!mx||!my||!tx||!ty)return false;vx->value=std::clamp(x,0,std::max(0,mx->value));vy->value=std::clamp(y,0,std::max(0,my->value));tx->value=ty->value=-99;return true;}
using VoidFn=void(__cdecl*)();static VoidFn oldSeenGet,oldSeenSet;
static void __cdecl SeenGet(){if(reviewEnabled){((void(__cdecl*)(int))0x41c760)(1);return;}oldSeenGet();}
static void __cdecl SeenSet(){if(reviewEnabled){((void(__cdecl*)(int))0x41c760)(0);return;}oldSeenSet();}

#include "compare.inc"
// The story map's short name on the 연표 / map switch (11-25, the user: 「지도는 적당한 단어가 아니다」)
static const wchar_t FLOW_WORD[]=L"흐름";
#include "flow.inc"
#include "movie.inc"
static bool FCBlockInput(UINT m){return fcOpen&&FCInputMessage(m);}

static void AddReviewMenu(){if(!oldMenu)return;HMENU m=GetSubMenu(oldMenu,0);if(!m)return;reviewMenu=m;if(GetMenuState(m,0x7e43,MF_BYCOMMAND)==UINT(-1))AppendMenuW(m,MF_STRING|MF_ENABLED,0x7e43,L"이야기 흐름\tF11");if(GetMenuState(m,REVIEW_ID,MF_BYCOMMAND)==UINT(-1)){AppendMenuW(m,MF_SEPARATOR,0,nullptr);AppendMenuW(m,MF_STRING|MF_ENABLED,REVIEW_ID,L"검수용 모든 콘텐츠 개방\tCtrl+F10");}CheckMenuItem(m,REVIEW_ID,MF_BYCOMMAND|(reviewEnabled?MF_CHECKED:MF_UNCHECKED));}
static bool SetReview(bool enabled){Init();wchar_t path[MAX_PATH];swprintf_s(path,L"%s\\review-unlock.enabled",root);
 if(enabled){HANDLE h=CreateFileW(path,GENERIC_WRITE,FILE_SHARE_READ,nullptr,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,nullptr);if(h==INVALID_HANDLE_VALUE)return false;DWORD written=0;BOOL ok=WriteFile(h,"1\r\n",3,&written,nullptr);CloseHandle(h);if(!ok||written!=3){DeleteFileW(path);return false;}}
 else if(!DeleteFileW(path)&&GetLastError()!=ERROR_FILE_NOT_FOUND)return false;
 reviewEnabled=enabled;if(reviewButton)InvalidateRect(reviewButton,nullptr,FALSE);if(reviewMenu)CheckMenuItem(reviewMenu,REVIEW_ID,MF_BYCOMMAND|(enabled?MF_CHECKED:MF_UNCHECKED));if(logFile){fprintf(logFile,"review_unlock=%d original_completion_and_cg_tables_preserved\n",enabled);fflush(logFile);}return true;}
static void ToggleReview(){if(!SetReview(!reviewEnabled)){MessageBoxW(Game(),L"검수 옵션을 저장하지 못했습니다.",L"레콘키스타",MB_OK|MB_ICONERROR);return;}if(reviewProbe||configProbe)return;MessageBoxW(Game(),reviewEnabled?L"모든 콘텐츠 검수 개방을 켰습니다.\n\n타이틀로 돌아가거나 추가 메뉴에 다시 들어가면 반영됩니다.\n기존 달성·CG 해금 기록은 변경하지 않습니다.":L"검수 개방을 취소했습니다.\n\n타이틀과 추가 메뉴에 다시 들어가면 원래 해금 상태로 표시됩니다.",L"검수 옵션",MB_OK|MB_ICONINFORMATION);}


// A native owner-drawn child button consumes its own press/release/capture events.
// Config's private VM flag is emitted only while its event loop is active. Not while the story map is over it (11-25: opened
// from the config screen, the map had 「CG·메뉴」 and 「모든 콘텐츠 개방」 left on top of it).
static bool ReviewButtonWanted(){return configVisibleVar.value!=0&&!fcOpen;}
static WNDPROC oldReviewButtonProc=nullptr;
static LRESULT CALLBACK ReviewButtonProc(HWND h,UINT msg,WPARAM wp,LPARAM lp){
 if((msg==WM_KEYDOWN||msg==WM_KEYUP||msg==WM_SYSKEYDOWN||msg==WM_SYSKEYUP)&&wp!=VK_SPACE)return SendMessageW(GetParent(h),msg,wp,lp);
 LRESULT result=CallWindowProcW(oldReviewButtonProc,h,msg,wp,lp);
 if((msg==WM_LBUTTONUP||msg==WM_CAPTURECHANGED||msg==WM_CANCELMODE)&&GetFocus()==h)SetFocus(GetParent(h));
 return result;
}
static void SyncReviewButton(){
 HWND parent=Game();if(!parent)return;
 bool wanted=ReviewButtonWanted();
 if(!wanted){if(reviewButton&&(GetWindowLongW(reviewButton,GWL_STYLE)&WS_VISIBLE)){if(GetFocus()==reviewButton)SetFocus(parent);ShowWindow(reviewButton,SW_HIDE);}return;}
 if(!reviewButton){
  if(!(GetWindowLongW(parent,GWL_STYLE)&WS_CLIPCHILDREN))SetWindowLongW(parent,GWL_STYLE,GetWindowLongW(parent,GWL_STYLE)|WS_CLIPCHILDREN);
  reviewButton=CreateWindowExW(0,L"BUTTON",L"검수용 모든 콘텐츠 개방",WS_CHILD|WS_TABSTOP|BS_OWNERDRAW,0,0,1,1,parent,(HMENU)(UINT_PTR)REVIEW_BUTTON_ID,GetModuleHandleW(nullptr),nullptr);
  if(reviewButton)oldReviewButtonProc=(WNDPROC)SetWindowLongPtrW(reviewButton,GWLP_WNDPROC,(LONG_PTR)ReviewButtonProc);
 }
 if(!reviewButton)return;
 if(!(GetWindowLongW(parent,GWL_STYLE)&WS_CLIPCHILDREN))SetWindowLongW(parent,GWL_STYLE,GetWindowLongW(parent,GWL_STYLE)|WS_CLIPCHILDREN);
 auto v=Viewport(parent);int x=v.x+MulDiv(380,v.w,800),y=v.y+MulDiv(55,v.h,600),w=MulDiv(210,v.w,800),h=MulDiv(25,v.h,600);
 RECT r{};GetWindowRect(reviewButton,&r);MapWindowPoints(nullptr,parent,(POINT*)&r,2);
 if(r.left!=x||r.top!=y||r.right-r.left!=w||r.bottom-r.top!=h){
  SetWindowPos(reviewButton,HWND_TOP,x,y,w,h,SWP_NOACTIVATE);
  int cut=std::max(3,h/5);POINT pts[6]={{cut,0},{w-cut,0},{w,h/2},{w-cut,h},{cut,h},{0,h/2}};
  HRGN region=CreatePolygonRgn(pts,6,WINDING);if(region&&!SetWindowRgn(reviewButton,region,TRUE))DeleteObject(region);
 }
 int fp=std::max(12,MulDiv(12,v.h,600));
 if(fp!=reviewFontPixels){HFONT f=CreateFontW(-fp,0,0,0,FW_MEDIUM,FALSE,FALSE,FALSE,HANGUL_CHARSET,OUT_DEFAULT_PRECIS,CLIP_DEFAULT_PRECIS,CLEARTYPE_QUALITY,DEFAULT_PITCH,L"맑은 고딕");if(f){SendMessageW(reviewButton,WM_SETFONT,(WPARAM)f,FALSE);if(reviewFont)DeleteObject(reviewFont);reviewFont=f;reviewFontPixels=fp;}}
 if(!(GetWindowLongW(reviewButton,GWL_STYLE)&WS_VISIBLE))ShowWindow(reviewButton,SW_SHOWNOACTIVATE);
}
static void DrawReviewButton(const DRAWITEMSTRUCT* di){
 int saved=SaveDC(di->hDC);RECT r=di->rcItem;
 bool down=(di->itemState&ODS_SELECTED)!=0;
 COLORREF fill=reviewEnabled?RGB(103,37,54):RGB(48,24,36);if(down)fill=RGB(126,57,70);
 HBRUSH brush=CreateSolidBrush(fill);HPEN pen=CreatePen(PS_SOLID,std::max<int>(1,(r.bottom-r.top)/25),RGB(185,128,135));
 FillRect(di->hDC,&r,brush);HGDIOBJ ob=SelectObject(di->hDC,brush),op=SelectObject(di->hDC,pen);
 int cut=std::max<int>(3,(r.bottom-r.top)/5);POINT pts[6]={{cut,1},{r.right-cut-1,1},{r.right-1,r.bottom/2},{r.right-cut-1,r.bottom-1},{cut,r.bottom-1},{1,r.bottom/2}};Polygon(di->hDC,pts,6);
 SelectObject(di->hDC,op);SelectObject(di->hDC,ob);DeleteObject(pen);DeleteObject(brush);
 if(reviewFont)SelectObject(di->hDC,reviewFont);SetBkMode(di->hDC,TRANSPARENT);SetTextColor(di->hDC,RGB(249,228,214));
 const wchar_t* label=reviewEnabled?L"개방 취소  ·  현재 켜짐":L"모든 콘텐츠 개방  ·  현재 꺼짐";
 DrawTextW(di->hDC,label,-1,&r,DT_CENTER|DT_VCENTER|DT_SINGLELINE|DT_NOPREFIX);
 if(di->itemState&ODS_FOCUS){InflateRect(&r,-cut,-4);DrawFocusRect(di->hDC,&r);}
 RestoreDC(di->hDC,saved);
}
#include "quality.inc"
#include "config_buttons.inc"
static void CALLBACK ReviewButtonTimer(HWND,UINT,UINT_PTR,DWORD){SyncReviewButton();SyncQualityButton();SyncConfigButtons();cproto::Tick();FCWarmStart();}

static void CALLBACK ProbeTimer(HWND,UINT,UINT_PTR,DWORD);
static RECT lastModeRect{},lastMonitorRect{};static HMONITOR lastModeMonitor=nullptr;
static void ApplyDisplayMode(int full,bool honorStartup){Init();SettleAll();auto tmode=Now();pMode++;if(honorStartup&&forceStartupFullscreen&&titleReady){full=1;forceStartupFullscreen=false;}game=Game();if(!game)return;FCSubclass(game);RECT currentModeRect{};GetWindowRect(game,&currentModeRect);auto modeMonitor=probe&&probeMonitor?probeMonitor:MonitorFromWindow(game,MONITOR_DEFAULTTONEAREST);MONITORINFO mi{sizeof(mi)};if(!GetMonitorInfoW(modeMonitor,&mi))return;if(displayConfigured&&fullscreen==(full!=0)&&EqualRect(&currentModeRect,&lastModeRect)&&modeMonitor==lastModeMonitor&&(!full||EqualRect(&mi.rcMonitor,&lastMonitorRect))){if(perf&&logFile){fprintf(logFile,"perf_mode request=%d serial=%u winapi_ms=%.3f skipped=1\n",full,pMode,Ms(tmode));fflush(logFile);}return;}if(probe&&!probeMonitor)probeMonitor=modeMonitor;if(!oldStyle){oldStyle=GetWindowLongA(game,GWL_STYLE);oldMenu=GetMenu(game);GetWindowRect(game,&oldRect);}AddReviewMenu();SetTimer(game,0x4845,50,ReviewButtonTimer);fullscreen=full!=0;displayConfigured=true;if(probe&&!probeNative){desired={-20000,-20000,-20000+3840,-20000+2160};SetMenu(game,nullptr);SetWindowLongA(game,GWL_STYLE,WS_POPUP);SetWindowPos(game,HWND_NOTOPMOST,desired.left,desired.top,3840,2160,SWP_FRAMECHANGED|SWP_NOACTIVATE|SWP_NOREDRAW);if(logFile){RECT r{};GetClientRect(game,&r);fprintf(logFile,"probe hidden mode actual=%ldx%ld\n",r.right,r.bottom);fflush(logFile);}SetTimer(game,0x4844,2500,ProbeTimer);return;}
 // Keep engine's legacy display-mode machinery in window mode. Only this wrapper controls the physical window.
 *(int*)0x56ac78=0;
 if(fullscreen){desired=mi.rcMonitor;SetMenu(game,nullptr);SetWindowLongA(game,GWL_STYLE,WS_POPUP|WS_CLIPCHILDREN|(probe?0:WS_VISIBLE));SetWindowPos(game,HWND_TOP,probe?-20000:mi.rcMonitor.left,probe?-20000:mi.rcMonitor.top,mi.rcMonitor.right-mi.rcMonitor.left,mi.rcMonitor.bottom-mi.rcMonitor.top,SWP_FRAMECHANGED|SWP_NOACTIVATE|SWP_NOREDRAW);}
 else{SetWindowLongA(game,GWL_STYLE,(probe?(oldStyle&~WS_VISIBLE):oldStyle)|WS_CLIPCHILDREN);SetMenu(game,oldMenu);RECT rc{0,0,1600,1200};int maxh=mi.rcWork.bottom-mi.rcWork.top-80;if(rc.bottom>maxh){rc.bottom=maxh;rc.right=maxh*4/3;}AdjustWindowRect(&rc,oldStyle,oldMenu!=nullptr);desired={mi.rcWork.left+40,mi.rcWork.top+30,mi.rcWork.left+40+rc.right-rc.left,mi.rcWork.top+30+rc.bottom-rc.top};SetWindowPos(game,HWND_NOTOPMOST,probe?-20000:desired.left,probe?-20000:desired.top,rc.right-rc.left,rc.bottom-rc.top,SWP_FRAMECHANGED|SWP_NOACTIVATE|SWP_NOREDRAW);}
 if(perf&&logFile){fprintf(logFile,"perf_mode request=%d serial=%u winapi_ms=%.3f\n",full,pMode,Ms(tmode));fflush(logFile);}GetWindowRect(game,&lastModeRect);lastModeMonitor=modeMonitor;lastMonitorRect=mi.rcMonitor;if(fcOpen&&fcWindow){RECT cr{};GetClientRect(game,&cr);MoveWindow(fcWindow,0,0,cr.right,cr.bottom,TRUE);}SyncReviewButton();SyncQualityButton();SyncConfigButtons();FitMovie();InvalidateRect(game,nullptr,FALSE);if(probe)SetTimer(game,0x4844,2500,ProbeTimer);if(logFile){auto v=Viewport(game);RECT cr{};GetClientRect(game,&cr);fprintf(logFile,"mode full=%d viewport=%d,%d,%d,%d physical=%ldx%ld monitor=%ld,%ld,%ld,%ld cg4k=%d\n",full,v.x,v.y,v.w,v.h,cr.right,cr.bottom,mi.rcMonitor.left,mi.rcMonitor.top,mi.rcMonitor.right,mi.rcMonitor.bottom,cg4k);fflush(logFile);}}
// Engine/user mode requests own the one-shot startup override; display refits must not consume it.
static void __cdecl Mode(int full){ApplyDisplayMode(full,true);}
// Refit after a display-mode change. Defer until the current Windows message has
// finished; never change the desktop mode or pull a minimized game to the front.
static const UINT WM_DISPLAYFIT=WM_APP+86;static bool displayFitQueued=false;
static void QueueDisplayFit(HWND h){if(!displayFitQueued)displayFitQueued=PostMessageW(h,WM_DISPLAYFIT,0,0)!=FALSE;}
// Native callback 43f9f0 overwrites WINDOWPOS.cx/cy at 43fddd for every window-mode size request.
// Suppress only that handler's legacy sizing branch, leaving other callbacks and normal window moves intact.
static int __cdecl GetMode(){return fullscreen?1:0;}
using LayoutFn=int(__cdecl*)(HWND,UINT,WPARAM,LPARAM);static LayoutFn oldLayout;
static int __cdecl Layout(HWND h,UINT msg,WPARAM wp,LPARAM lp){
 if(displayConfigured&&h==Game()){
  if(msg==WM_DISPLAYFIT){displayFitQueued=false;if(fullscreen&&!IsIconic(h))ApplyDisplayMode(1,false);return 1;}
  if(fullscreen&&(msg==WM_DISPLAYCHANGE||msg==WM_DPICHANGED||(msg==WM_ACTIVATEAPP&&wp))){
   QueueDisplayFit(h);if(msg==WM_DISPLAYCHANGE||msg==WM_DPICHANGED)return 1;
  }
  if(msg==WM_APP+81){SyncReviewButton();SyncQualityButton();SyncConfigButtons();return 1;}
  if(msg==WM_APP+82){BacklogJump();return 1;}   // backlog.inc: from the 기록
  if(perf&&msg==WM_APP+80){PerfCommand(h,wp);return 1;}
  if(perf&&msg==WM_APP+84){DumpVar(uint32_t(wp));return 1;}   // tests: a VM variable and what it points at
  if(perf&&msg==WM_APP+85){DumpElem(uint32_t(wp),int(HIWORD(lp)),int(LOWORD(lp)));return 1;}   // tests: one element of a VM array
  if(perf&&msg==WM_APP+83){bool ok=ChronicleMoveTo(int(wp),int(lp));if(logFile){int x=0,y=0,mx=0,my=0;ChroniclePosition(&x,&y,&mx,&my);fprintf(logFile,"chronicle_moved ok=%d at=%d,%d max=%d,%d\n",ok,x,y,mx,my);fflush(logFile);}return 1;}   // tests: put the chronicle at x,y
  if(fcOpen&&FCInputMessage(msg))return 1;
  if(ConfigButtonMessage(h,msg,wp,lp))return 1;
  if(msg==WM_DRAWITEM&&wp==QUALITY_ID&&lp){DrawQualityButton((const DRAWITEMSTRUCT*)lp);return 1;}
  if(msg==WM_COMMAND&&LOWORD(wp)==QUALITY_ID&&HIWORD(wp)==BN_CLICKED&&(HWND)lp==qualityButton){ToggleQuality();SetFocus(h);return 1;}
  if(msg==WM_DRAWITEM&&wp==REVIEW_BUTTON_ID&&lp){DrawReviewButton((const DRAWITEMSTRUCT*)lp);return 1;}
  if(msg==WM_COMMAND&&LOWORD(wp)==REVIEW_BUTTON_ID&&HIWORD(wp)==BN_CLICKED&&(HWND)lp==reviewButton){ToggleReview();SyncReviewButton();InvalidateRect(reviewButton,nullptr,FALSE);UpdateWindow(reviewButton);SetFocus(h);return 1;}
  if((msg==WM_COMMAND&&LOWORD(wp)==0x7e43)||((msg==WM_KEYDOWN||msg==WM_SYSKEYDOWN)&&wp==VK_F11)){if(msg==WM_COMMAND||!(lp&(1L<<30)))OpenFlowChart();return 1;}
  if(msg==WM_COMMAND&&LOWORD(wp)==REVIEW_ID){ToggleReview();return 1;}
  if((msg==WM_KEYDOWN||msg==WM_SYSKEYDOWN)&&wp==VK_F10&&(GetKeyState(VK_CONTROL)&0x8000)){if(!(lp&(1L<<30)))ToggleReview();return 1;}
  if(msg==WM_WINDOWPOSCHANGING)return 0;
  if(msg==WM_KEYDOWN&&wp==VK_F4){if(!(lp&(1L<<30)))Mode(1);return 1;}
  // the window menu's 「전체 화면」/「창 모드」 (40002/40003) as F4/Alt+Enter: the engine's own handler only stretched the window
  // to the screen, title and menu kept (11-25, the user: 「게임 프로그램 상단의 전체 화면을 누르면 옵션의 전체 화면과 달리」)
  if(msg==WM_COMMAND&&(LOWORD(wp)==40002||LOWORD(wp)==40003)){Mode(LOWORD(wp)==40002);return 1;}
  // the title bar's maximize button (and a double click on the title bar) is the same full screen: Windows' own maximize
  // kept the title bar and menu (11-25, the user: 「우측 상단 전체화면 아이콘을 클릭하면 이렇게 되어버려」)
  if(msg==WM_SYSCOMMAND&&(wp&0xFFF0)==SC_MAXIMIZE){Mode(1);return 1;}
  if(msg==WM_SYSKEYDOWN&&wp==VK_RETURN){if(!(lp&(1L<<30)))Mode(0);return 1;}
 }
 return oldLayout(h,msg,wp,lp);
}

// Isolated QA only: restore both VM globals before returning; no user save record is edited.
static void ProbeReview(){
 if(!reviewProbe||!titleReady)return;static bool done=false;if(done)return;done=true;int failures=0,checks=0;
 auto check=[&](bool ok,const char*name){checks++;if(!ok)failures++;if(logFile){fprintf(logFile,"review_probe %s %s\n",name,ok?"PASS":"FAIL");fflush(logFile);}};
 int count=*(int*)0x4f3a6c;auto table=*(Variable**)0x5123b0;
 if(count<0||count>20000||!table){check(false,"table_bounds");return;}
 std::vector<Variable> records(table,table+count);unsigned char seen[40000];memcpy(seen,(void*)0x4e9e20,sizeof(seen));
 check(reviewMenu&&GetMenuState(reviewMenu,REVIEW_ID,MF_BYCOMMAND)!=UINT(-1),"native_menu_exists");
 check(SetReview(false),"disable_initial");SendMessageW(Game(),WM_COMMAND,REVIEW_ID,0);
 check(reviewEnabled,"menu_command_enables");check((GetMenuState(reviewMenu,REVIEW_ID,MF_BYCOMMAND)&MF_CHECKED)!=0,"menu_checked");
 wchar_t path[MAX_PATH];swprintf_s(path,L"%s\\review-unlock.enabled",root);check(GetFileAttributesW(path)!=INVALID_FILE_ATTRIBUTES,"enable_persisted");
 for(auto id:reviewIds){Variable request{id,0,0,0};short cache=0;auto a=((VarFn)0x41c130)(&request,&cache);auto b=((VarHashFn)0x41c230)(id);check(a&&b&&a->value==1&&b->value==1&&a->type==0&&a->scope==0,"flag_read_virtual");auto w=((VarFn)0x41c310)(&request,&cache);check(w&&w->value==1,"flag_write_isolated");w->value=0;check(((VarHashFn)0x41c230)(id)->value==1,"direct_virtual_write_isolated");}
 // Test the real patched syscall entries with a private synthetic VM argument stack.
 uintptr_t oldTask=*(uintptr_t*)0x56e1a4,oldVm=*(uintptr_t*)0x56e1a8;int task[16]{},vm[16]{};Variable stack[64]{};char str[272]{};strcpy_s(str+12,260,"__REVIEW_PROBE_UNSEEN_8EAD91.rct");task[2]=1;vm[4]=64;vm[9]=(int)stack;stack[0]={0,2,3,(int)str};
 *(uintptr_t*)0x56e1a4=(uintptr_t)task;*(uintptr_t*)0x56e1a8=(uintptr_t)vm;
 ((VoidFn)0x420390)();bool getOk=task[2]==2&&stack[1].value==1&&stack[1].type==0&&stack[1].scope==3;task[2]=1;
 ((VoidFn)0x420260)();bool setOk=task[2]==2&&stack[1].value==0;task[2]=1;reviewEnabled=false;((VoidFn)0x420390)();bool offOk=task[2]==2&&stack[1].value==0;reviewEnabled=true;
 *(uintptr_t*)0x56e1a4=oldTask;*(uintptr_t*)0x56e1a8=oldVm;
 check(getOk,"cg_query_unlocked_vm_return");check(setOk,"cg_write_suppressed_vm_return");check(offOk,"cg_query_off_original");
 SendMessageW(Game(),WM_COMMAND,REVIEW_ID,0);check(!reviewEnabled,"menu_command_disables");check(!(GetMenuState(reviewMenu,REVIEW_ID,MF_BYCOMMAND)&MF_CHECKED),"menu_unchecked");check(GetFileAttributesW(path)==INVALID_FILE_ATTRIBUTES,"disable_persisted");
 for(auto id:reviewIds){Variable request{id,0,0,0};auto a=((VarFn)0x41c130)(&request,nullptr),b=oldVarFind(&request,nullptr);check(a==b&&((VarHashFn)0x41c230)(id)==oldVarHash(id),"disabled_reads_original");}
 check(*(int*)0x4f3a6c==count&&memcmp(records.data(),*(void**)0x5123b0,count*sizeof(Variable))==0,"completion_table_unchanged");check(memcmp(seen,(void*)0x4e9e20,sizeof(seen))==0,"cg_table_unchanged");
 BYTE keyboard[256],pressed[256];GetKeyboardState(keyboard);memcpy(pressed,keyboard,256);pressed[VK_CONTROL]=0x80;SetKeyboardState(pressed);
 SendMessageW(Game(),WM_SYSKEYDOWN,VK_F10,0);check(reviewEnabled,"ctrl_f10_system_key_enables");SendMessageW(Game(),WM_SYSKEYDOWN,VK_F10,1L<<30);check(reviewEnabled,"ctrl_f10_repeat_no_toggle");SendMessageW(Game(),WM_KEYDOWN,VK_F10,0);check(!reviewEnabled,"ctrl_f10_key_disables");SetKeyboardState(keyboard);

 if(logFile){fprintf(logFile,"review_probe_result checks=%d failures=%d state_off=%d\n",checks,failures,!reviewEnabled);fflush(logFile);}
}

static void ProbeInput(){
 if(!inputProbe||!titleReady)return;static bool done=false;if(done)return;done=true;int checks=0,failures=0;
 auto check=[&](bool ok,const char*n){checks++;if(!ok)failures++;if(logFile){fprintf(logFile,"input_probe %s %s\n",n,ok?"PASS":"FAIL");fflush(logFile);}};
 auto testMode=[&](int mode){
  Mode(mode);auto v=Viewport(Game());int x=640,y=348;
  LPARAM physical=MAKELPARAM(v.x+(int)ceil(double(x)*v.w/800),v.y+(int)ceil(double(y)*v.h/600));
  int oldx=*(int*)0x4e980c,oldy=*(int*)0x4e9808;oldInput(Game(),WM_MOUSEMOVE,0,physical);
  check(*(int*)0x4e980c==oldx&&*(int*)0x4e9808==oldy,"baseline_physical_move_rejected");
  SendMessageW(Game(),WM_MOUSEMOVE,0,physical);
  check(*(int*)0x4e980c==x&&*(int*)0x4e9808==y,"physical_move_reaches_logical_button");
  SendMessageW(Game(),WM_LBUTTONDOWN,MK_LBUTTON,physical);
  check(*(unsigned char*)(0x4e9afc+0x82)!=0,"left_button_down_recorded");
  SendMessageW(Game(),WM_LBUTTONUP,0,physical);
  check(*(unsigned char*)(0x4e9afc+0x82)==0,"left_button_up_recorded");
  if(v.x>0){SendMessageW(Game(),WM_MOUSEMOVE,0,MAKELPARAM(2,100));check(*(int*)0x4e980c==x&&*(int*)0x4e9808==y,"letterbox_rejected");}
 };
 forceStartupFullscreen=false;testMode(0);testMode(1);
 if(logFile){fprintf(logFile,"input_probe_result checks=%d failures=%d\n",checks,failures);fflush(logFile);}
}


static void ProbeConfig(){
 if(!configProbe||!titleReady)return;static int phase=0,checks=0,failures=0,tries=0,settle=0;if(phase>=6)return;
 auto check=[&](bool ok,const char*name){checks++;if(!ok)failures++;if(logFile){fprintf(logFile,"config_probe %s %s\n",name,ok?"PASS":"FAIL");fflush(logFile);}};
 auto mouse=[&](UINT msg,int x,int y,WPARAM state=0){auto v=Viewport(Game());LPARAM lp=MAKELPARAM(v.x+(int)ceil(double(x)*v.w/800),v.y+(int)ceil(double(y)*v.h/600));SendMessageW(Game(),msg,state,lp);};
 if(phase==0){if(settle++<3)return;check(!ReviewButtonWanted(),"hidden_on_title");SendMessageW(Game(),WM_ACTIVATEAPP,TRUE,0);SendMessageW(Game(),WM_ACTIVATE,WA_ACTIVE,0);SendMessageW(Game(),WM_SETFOCUS,0,0);mouse(WM_MOUSEMOVE,640,430);mouse(WM_LBUTTONDOWN,640,430,MK_LBUTTON);phase=1;return;}
 if(phase==1){mouse(WM_LBUTTONUP,640,430);phase=2;return;}
 if(phase==2){
  if(!ReviewButtonWanted()&&tries++<7){if(tries==2){probeShots=0;SendMessageW(Game(),WM_KEYDOWN,VK_F9,0);SendMessageW(Game(),WM_KEYUP,VK_F9,0);}if(logFile){fprintf(logFile,"config_probe_wait mx=%d my=%d left=%d focus=%p\n",*(int*)0x4e980c,*(int*)0x4e9808,*(unsigned char*)(0x4e9afc+0x82),GetFocus());fflush(logFile);}return;}
  check(ReviewButtonWanted(),"real_config_script_sets_flag");
  check(reviewButton&&(GetWindowLongW(reviewButton,GWL_STYLE)&WS_VISIBLE),"config_button_exists_visible_style");
  if(!reviewButton){phase=5;return;}
  RECT rect{};GetClientRect(reviewButton,&rect);POINT pt{rect.right/2,rect.bottom/2};
  SetReview(false);int flags=*(unsigned char*)(0x4e9afc+0x82),mx=*(int*)0x4e980c,my=*(int*)0x4e9808;
  SendMessageW(reviewButton,WM_LBUTTONDOWN,MK_LBUTTON,MAKELPARAM(pt.x,pt.y));SendMessageW(reviewButton,WM_LBUTTONUP,0,MAKELPARAM(pt.x,pt.y));
  check(reviewEnabled,"child_mouse_click_enables");check(flags==*(unsigned char*)(0x4e9afc+0x82)&&mx==*(int*)0x4e980c&&my==*(int*)0x4e9808,"child_click_not_delivered_to_game_input");
  SendMessageW(reviewButton,WM_LBUTTONDOWN,MK_LBUTTON,MAKELPARAM(pt.x,pt.y));SendMessageW(reviewButton,WM_MOUSEMOVE,MK_LBUTTON,MAKELPARAM(rect.right+20,rect.bottom+20));SendMessageW(reviewButton,WM_LBUTTONUP,0,MAKELPARAM(rect.right+20,rect.bottom+20));check(reviewEnabled,"drag_release_outside_does_not_toggle");check(GetFocus()!=reviewButton,"drag_cancel_focus_returned");
  SendMessageW(reviewButton,WM_KEYDOWN,VK_SPACE,0);SendMessageW(reviewButton,WM_KEYUP,VK_SPACE,0);check(!reviewEnabled,"child_keyboard_space_disables");
  HDC dc=GetDC(reviewButton);HGDIOBJ f=SelectObject(dc,reviewFont);SIZE size{};const wchar_t* text=L"모든 콘텐츠 개방  ·  현재 꺼짐";GetTextExtentPoint32W(dc,text,(int)wcslen(text),&size);SelectObject(dc,f);ReleaseDC(reviewButton,dc);check(size.cx<rect.right-12&&size.cy<rect.bottom,"korean_label_fits_button");
  mouse(WM_MOUSEMOVE,760,580);mouse(WM_RBUTTONDOWN,760,580,MK_RBUTTON);phase=3;return;
 }
 if(phase==3){mouse(WM_RBUTTONUP,760,580);phase=4;tries=0;return;}
 if(phase==4){if(ReviewButtonWanted()&&tries++<5)return;check(!ReviewButtonWanted(),"config_exit_clears_flag");check(!(GetWindowLongW(reviewButton,GWL_STYLE)&WS_VISIBLE),"button_hidden_after_config");phase=5;}
 if(phase==5){SetReview(false);if(logFile){fprintf(logFile,"config_probe_result checks=%d failures=%d\n",checks,failures);fflush(logFile);}phase=6;}
}

static BOOL WINAPI WindowShow(HWND h,int cmd){if(probe&&h==Game())cmd=SW_HIDE;return ShowWindow(h,cmd);}
#include "scaled_present.inc"
#include "defer.inc"
static int WINAPI Present(HDC dc,int dx,int dy,int dw,int dh,int sx,int sy,int sw,int sh,const void* bits,const BITMAPINFO* info,UINT usage,DWORD rop){Init();Bitmap* b=*(Bitmap**)0x56a6a8;HWND hwnd=WindowFromDC(dc);if(probe&&logFile){fprintf(logFile,"present attempt hwnd=%p game=%p bits=%p main=%p valid=%d\n",hwnd,Game(),bits,b?b->pixels:nullptr,Valid(b));fflush(logFile);}if(!Valid(b)||bits!=b->pixels||hwnd!=Game())return StretchDIBits(dc,dx,dy,dw,dh,sx,sy,sw,sh,bits,info,usage,rop);
 HitchFrame();FinishFrame();if(cproto::Covered()){frames++;return dh;}   // the new 연표 is over it: nothing of it shows
 LARGE_INTEGER t0,t1;QueryPerformanceCounter(&t0);nesting++;Shadow*s=nullptr;try{s=Get(b,{0,0,b->w,b->h},true);}catch(const std::bad_alloc&){}nesting--;auto tget=Now();auto v=Viewport(hwnd);RECT cr{};GetClientRect(hwnd,&cr);HBRUSH black=(HBRUSH)GetStockObject(BLACK_BRUSH);RECT bars[4]={{0,0,v.x,cr.bottom},{v.x+v.w,0,cr.right,cr.bottom},{0,0,cr.right,v.y},{0,v.y+v.h,cr.right,cr.bottom}};for(auto& r:bars)if(r.right>r.left&&r.bottom>r.top)FillRect(dc,&r,black);
 SetStretchBltMode(dc,HALFTONE);SetBrushOrgEx(dc,0,0,nullptr);int result;
 // Source/crop coordinates and screen shake stay in logical units until this boundary.
 int x=v.x+MulDiv(dx,v.w,800),y=v.y+MulDiv(dy,v.h,600),w=MulDiv(dw,v.w,800),h=MulDiv(dh,v.h,600);
 if(s&&ScaledPresent(dc,x,y,w,h,sx,sy,sw,sh,s,usage,rop,&result)){}else if(s)result=StretchDIBits(dc,x,y,w,h,sx*4,sy*4,sw*4,sh*4,s->pixels.data(),&s->info,usage,rop);else result=StretchDIBits(dc,x,y,w,h,sx,sy,sw,sh,bits,info,usage,rop);
 QueryPerformanceCounter(&t1);if(hitch)hGdiMs+=1000.0*(t1.QuadPart-tget)/freq.QuadPart;if(perf&&logFile){fprintf(logFile,"perf_present seq=%u total_ms=%.3f sync_ms=%.3f gdi_ms=%.3f nearest_ms=%.3f decode_ms=%.3f compose_ms=%.3f assets=%llu blits=%llu\n",++pPresent,1000.0*(t1.QuadPart-t0.QuadPart)/freq.QuadPart,1000.0*(tget-t0.QuadPart)/freq.QuadPart,1000.0*(t1.QuadPart-tget)/freq.QuadPart,pNearest,pDecode,pCompose,loads,blits);
   {double by[5]{};int n[5]{};const char*kinds="CSAMT";for(auto&e:blitStats){int k=int(strchr(kinds,e.kind)-kinds);by[k]+=e.ms;n[k]++;}std::sort(blitStats.begin(),blitStats.end(),[](const BlitStat&p,const BlitStat&q){return p.ms>q.ms;});
    fprintf(logFile,"perf_blits C=%d/%.2f S=%d/%.2f A=%d/%.2f M=%d/%.2f T=%d/%.2f top=",n[0],by[0],n[1],by[1],n[2],by[2],n[3],by[3],n[4],by[4]);for(size_t i=0;i<blitStats.size()&&i<6;i++)fprintf(logFile,"%c:%dx%d:%.2f ",blitStats[i].kind,blitStats[i].w,blitStats[i].h,blitStats[i].ms);fprintf(logFile,"\n");blitStats.clear();}
   fflush(logFile);hDecodeDone+=pDecode;hNearestDone+=pNearest;hComposeDone+=pCompose;pNearest=pDecode=pCompose=0;}if(frames==1||frames%600==0)CrashlogInstall();frames++;if(logFile&&(frames==1||frames%300==0)){fprintf(logFile,"frame=%llu assets=%llu blits=%llu memory=%llu fallback_pixels=%llu present_ms=%.2f physical=%dx%d\n",frames,loads,blits,used,fallbackPixels,1000.0*(t1.QuadPart-t0.QuadPart)/freq.QuadPart,cr.right,cr.bottom);fflush(logFile);}
 // LRU eviction is only between operations; live local Shadow pointers are never evicted.
 while(used>768ull*1024*1024&&shadows.size()>1){auto victim=shadows.end();for(auto it=shadows.begin();it!=shadows.end();++it)if(it->first!=b&&it->second->alternate.empty()&&!it->second->job&&(victim==shadows.end()||it->second->age<victim->second->age))victim=it;if(victim==shadows.end())break;ForgetShadow(victim->first);}return result;}
static void DumpProbe(Bitmap*b){if(perf)return;if(GetEnvironmentVariableW(L"RECON_FLOW_PROBE",nullptr,0)&&(flowMark.value<=0||probeShots>=1||GetTickCount64()-flowArriveTick<2500))return;if(!probe||(loads==0&&!GetEnvironmentVariableW(L"RECON_FLOW_PROBE",nullptr,0))||probeShots>=12||GetTickCount64()-probeTime<2000)return;probeTime=GetTickCount64();SettleAll();auto s=Get(b,{0,0,b->w,b->h},true);if(!s)return;wchar_t dir[MAX_PATH],path[MAX_PATH];swprintf_s(dir,L"%s\\qa",root);CreateDirectoryW(dir,nullptr);swprintf_s(path,L"%s\\probe-%02u.bmp",dir,probeShots++);FILE*f=nullptr;if(_wfopen_s(&f,path,L"wb")||!f)return;BITMAPFILEHEADER head{};head.bfType=0x4d42;head.bfOffBits=sizeof(head)+sizeof(BITMAPINFOHEADER);head.bfSize=head.bfOffBits+DWORD(s->pixels.size());fwrite(&head,sizeof(head),1,f);fwrite(&s->info.bmiHeader,sizeof(BITMAPINFOHEADER),1,f);fwrite(s->pixels.data(),1,s->pixels.size(),f);fclose(f);if(logFile){fprintf(logFile,"probe shot=%u assets=%llu blits=%llu memory=%llu\n",probeShots,loads,blits,used);fflush(logFile);}}
using RenderFn=void(__cdecl*)();static RenderFn oldRender;static void __cdecl Render(){ApplyCG();oldRender();SyncReviewButton();SyncQualityButton();SyncConfigButtons();if(probe){Bitmap*b=*(Bitmap**)0x56a6a8;if(Valid(b)){nesting++;try{DumpProbe(b);}catch(const std::bad_alloc&){}nesting--;}}}
static void ProbeCoordinates(){ int failures=0;for(int x=0;x<800;x++){POINT p{x,200};ToScreen(Game(),&p);ToClient(Game(),&p);if(p.x!=x||p.y!=200)failures++;}for(int y=0;y<600;y++){POINT p{200,y};ToScreen(Game(),&p);ToClient(Game(),&p);if(p.x!=200||p.y!=y)failures++;}if(logFile){auto v=Viewport(Game());fprintf(logFile,"probe coordinates samples=1400 failures=%d viewport=%d,%d,%d,%d\n",failures,v.x,v.y,v.w,v.h);fflush(logFile);}
 // the chronicle's drag box exactly as the engine builds it (0x42ccca): ClientToScreen(0,0) + (800-1, 600-1)
 {POINT o{0,0};ToScreen(Game(),&o);RECT e{o.x,o.y,o.x+799,o.y+599};ClipToGame(&e);auto v=Viewport(Game());POINT s{v.x,v.y};ClientToScreen(Game(),&s);if(logFile){fprintf(logFile,"probe clip expected=%ld,%ld,%ld,%ld\n",s.x,s.y,s.x+v.w,s.y+v.h);fflush(logFile);}}
}
static void ProbeAssets(){
 const char* names[]={"title1_off.rct","title1_on.rct","title1_push.rct","title2_off.rct","title2_on.rct","title2_push.rct","title3_off.rct","title3_on.rct","title3_push.rct","bg_140b.rct","bg_240d.rct","bg_431a.rct","ev114.rct"};
 if(!probeNative)for(auto n:names){Bitmap*a=LoadDirect(n);Bitmap*b=((Bitmap*(__cdecl*)(int,int,int))0x43b140)(a->w,a->h,0);Box box{0,0,a->w,a->h};Copy(a,&box,b,&box);auto sa=shadows.find(a),sb=shadows.find(b);bool ok=sa!=shadows.end()&&sb!=shadows.end()&&sa->second->pixels==sb->second->pixels;if(logFile){fprintf(logFile,"probe asset_copy %s %s\n",n,ok?"PASS":"FAIL");fflush(logFile);}Free(b,0);Free(a,0);}
 if(probeNative){Mode(0);ProbeCoordinates();Mode(1);}ProbeCoordinates();
}
static void CALLBACK ProbeTimer(HWND hwnd,UINT,UINT_PTR,DWORD){if(perf)return;SettleAll();ProbeExactCompare();Bitmap*b=*(Bitmap**)0x56a6a8;if(!Valid(b)||(!loads&&!GetEnvironmentVariableW(L"RECON_FLOW_PROBE",nullptr,0)))return;if(reviewProbe)ProbeReview();if(inputProbe)ProbeInput();if(configProbe)ProbeConfig();static bool assetTested=false;if(!assetTested){assetTested=true;if(!GetEnvironmentVariableW(L"RECON_FLOW_PROBE",nullptr,0)&&!reviewProbe&&!inputProbe&&!configProbe)ProbeAssets();}nesting++;try{DumpProbe(b);}catch(const std::bad_alloc&){}nesting--;HDC dc=GetDC(hwnd);if(dc){Present(dc,0,0,800,600,0,0,800,600,b->pixels,b->info,DIB_RGB_COLORS,SRCCOPY);ReleaseDC(hwnd,dc);}if(probeShots>=12&&!configProbe)KillTimer(hwnd,0x4844);}
#include "quality_probe.inc"
// perf op 7, tests only (the opening's thin dark box lines, 10-25): every 24-bit shadow scored for thin dark lines its 1x
// bitmap does not have (4x luma 48 below the 1x pixel under it and 24 below the pixels two rows or columns away); the three
// worst are saved as qa\lines-<n>.bmp (4x) with their 1x bitmap widened (qa\lines-<n>-1x.bmp).
static void ShadowLineAudit(){
 SettleAll();struct Hit{Bitmap*b;Shadow*s;uint64_t n;int x0,y0,x1,y1;};std::vector<Hit> hits;
 for(auto& [b,sp]:shadows){Shadow*s=sp.get();if(!Valid(b)||b->format||s->pixels.empty()||s->b.w!=b->w*4||s->b.h!=b->h*4)continue;
  Hit h{b,s,0,INT_MAX,INT_MAX,-1,-1};const int W=s->b.w,H=s->b.h,P=s->b.pitch;auto L=[&](const unsigned char*p){return (p[0]*29+p[1]*150+p[2]*77)>>8;};
  for(int y=2;y<H-2;y++){const unsigned char*r=s->pixels.data()+size_t(y)*P;const unsigned char*r1=b->pixels+size_t(y>>2)*b->pitch;
   for(int x=2;x<W-2;x++){int l4=L(r+x*3),l1=L(r1+(x>>2)*3);if(l4>l1-48)continue;
    int up=L(r-2*P+x*3),dn=L(r+2*P+x*3),lf=L(r+(x-2)*3),rt=L(r+(x+2)*3);
    if((l4<std::min(up,dn)-24)||(l4<std::min(lf,rt)-24)){h.n++;h.x0=std::min(h.x0,x);h.y0=std::min(h.y0,y);h.x1=std::max(h.x1,x);h.y1=std::max(h.y1,y);}}}
  if(h.n)hits.push_back(h);}
 std::sort(hits.begin(),hits.end(),[](const Hit&a,const Hit&b){return a.n>b.n;});
 Bitmap*screen=*(Bitmap**)0x56a6a8;
 for(size_t i=0;i<hits.size();i++){auto&h=hits[i];auto a=assets.find(h.b);
  if(logFile){fprintf(logFile,"lines_audit rank=%zu bitmap=%p %dx%d screen=%d asset=%s hd=%d blank=%d mask=%d lines=%llu box=%d,%d,%d,%d\n",i,(void*)h.b,h.b->w,h.b->h,int(h.b==screen),a!=assets.end()?a->second.name.c_str():"-",a!=assets.end()?int(a->second.hd):-1,int(h.s->blank),int(h.b->mask!=nullptr),(unsigned long long)h.n,h.x0,h.y0,h.x1,h.y1);fflush(logFile);}
  if(i<3){wchar_t path[MAX_PATH];auto save=[&](const wchar_t*suffix,const unsigned char*p,int w,int hh,int pitch){swprintf_s(path,L"%s\\qa\\lines-%zu%s.bmp",root,i,suffix);FILE*f=nullptr;if(_wfopen_s(&f,path,L"wb")||!f)return;
    int stride=(w*3+3)&~3;BITMAPFILEHEADER fh{0x4d42,DWORD(54+size_t(stride)*hh),0,0,54};BITMAPINFOHEADER ih{sizeof(BITMAPINFOHEADER),w,-hh,1,24,BI_RGB};fwrite(&fh,sizeof fh,1,f);fwrite(&ih,sizeof ih,1,f);
    std::vector<unsigned char> row(stride,0);for(int y=0;y<hh;y++){memcpy(row.data(),p+size_t(y)*pitch,size_t(w)*3);fwrite(row.data(),1,stride,f);}fclose(f);};
   save(L"",h.s->pixels.data(),h.s->b.w,h.s->b.h,h.s->b.pitch);save(L"-1x",h.b->pixels,h.b->w,h.b->h,h.b->pitch);}}
 if(logFile){fprintf(logFile,"lines_audit done shadows=%zu with_lines=%zu\n",shadows.size(),hits.size());fflush(logFile);}}
// perf only (10-27, the new 연표 reads the 연표 script's arrays): a VM variable's record and the memory its value points at
static bool Readable(const void*p,size_t n){MEMORY_BASIC_INFORMATION mi{};if(!p||!VirtualQuery(p,&mi,sizeof(mi))||mi.State!=MEM_COMMIT||(mi.Protect&(PAGE_NOACCESS|PAGE_GUARD)))return false;
 return (const char*)p+n<=(const char*)mi.BaseAddress+mi.RegionSize;}
static void DumpMem(const char*tag,const void*p,int n){if(!Readable(p,size_t(n)))return;const unsigned char*b=(const unsigned char*)p;char line[700];int k=0;
 for(int i=0;i<n;i++)k+=sprintf_s(line+k,sizeof(line)-k,"%02x%s",b[i],i%4==3?" ":"");fprintf(logFile,"  %s %p %s\n",tag,p,line);}
static void DumpVar(uint32_t h){if(!logFile)return;Variable*v=oldVarHash?oldVarHash(h&0xffffffffu):nullptr;if(!v){fprintf(logFile,"var %08x none\n",h);fflush(logFile);return;}
 fprintf(logFile,"var %08x at=%p type=%u scope=%u value=%08x\n",h,(void*)v,v->type,v->scope,(unsigned)v->value);
 const void* p=(const void*)(uintptr_t)(unsigned)v->value;if(Readable(p,96)){DumpMem("value",p,96);for(int i=5;i<8;i++){const void* q=((const void*const*)p)[i];char t[16];sprintf_s(t,"elem%d",i-5);DumpMem(t,q,96);}}
 fflush(logFile);}
// perf only: element (r, c) of a VM array (header: 5 dwords, dims at 3 and 4, then the elements row by row) and, for a
// string array, the string object it points at
static void DumpElem(uint32_t h,int r,int c){if(!logFile||!oldVarHash)return;Variable*v=oldVarHash(h);const int*p=v?(const int*)(uintptr_t)(unsigned)v->value:nullptr;
 if(!Readable(p,20)){fprintf(logFile,"elem %08x unreadable\n",h);fflush(logFile);return;}int d0=p[3],d1=p[4];size_t i=size_t(r)*size_t(d1)+size_t(c);
 fprintf(logFile,"elem %08x [%d][%d] dims=%d,%d type=%u\n",h,r,c,d0,d1,v->type);if(!Readable(p+5+i,4)){fflush(logFile);return;}fprintf(logFile,"  raw=%08x\n",unsigned(p[5+i]));
 if(v->type==5){const void*s=(const void*)(uintptr_t)unsigned(p[5+i]);DumpMem("str",s,96);if(Readable(s,16)){for(int k=0;k<4;k++){const void*q=((const void*const*)s)[k];char t[16];sprintf_s(t,"str.ptr%d",k);DumpMem(t,q,64);}}}
 fflush(logFile);}
static void PerfCommand(HWND hwnd,WPARAM op){
 if(op==7){ShadowLineAudit();return;}
 if(op==6){ProbeVariantMask();return;}
 if(op==5||op==4){dumpLayers=true;dumpLayers4k=op==4;return;}   // defer.inc: the next frame's sources at 1x (4: and their 4x)
 if(op>=100&&op<200){if(logFile){fprintf(logFile,"hitch_mark %d frame=%u\n",int(op)-100,hFrames);fflush(logFile);}return;}   // tests: phase marks for hitch.inc
 if(op>=10&&op<100){CaptureQuality(unsigned(op)-10);return;}
 if(op==1||op==2){Mode(op==1);return;}
 Bitmap*b=*(Bitmap**)0x56a6a8;if(!Valid(b))return;
 if(op==3){HDC screen=GetDC(hwnd);HDC dc=CreateCompatibleDC(screen);BITMAPINFO bi{};bi.bmiHeader={sizeof(BITMAPINFOHEADER),4096,-2160,1,32,BI_RGB};void* p=nullptr;HBITMAP bm=CreateDIBSection(dc,&bi,DIB_RGB_COLORS,&p,nullptr,0);auto prev=SelectObject(dc,bm);
 auto v=Viewport(hwnd);auto s=Get(b,{0,0,b->w,b->h},true);for(int i=0;i<8;i++){auto t=Now();Get(b,{0,0,b->w,b->h},true);double sync=Ms(t);t=Now();SetStretchBltMode(dc,HALFTONE);int result=0;ScaledPresent(dc,0,0,v.w,v.h,0,0,b->w,b->h,s,DIB_RGB_COLORS,SRCCOPY,&result);GdiFlush();fprintf(logFile,"perf_dib full=%d sync_ms=%.3f gdi_ms=%.3f\n",fullscreen,sync,Ms(t));}SelectObject(dc,prev);DeleteObject(bm);DeleteDC(dc);ReleaseDC(hwnd,screen);fflush(logFile);}
}
#include "text4k.inc"
#include "chronicle_proto.inc"
#include "backlog.inc"
struct Hook {uintptr_t addr;unsigned len;const unsigned char* expected;void* replacement;void** original;};
#include "hooks.inc"
static bool Install(){
 for(auto& h:hooks)if(memcmp((void*)h.addr,h.expected,h.len))return false;
 void* allocated[64]{};unsigned count=0;uintptr_t pages[64]{};DWORD protections[64]{};unsigned pageCount=0;
 for(auto& h:hooks){if(h.original){auto t=(unsigned char*)VirtualAlloc(nullptr,h.len+5,MEM_COMMIT|MEM_RESERVE,PAGE_EXECUTE_READWRITE);if(!t){for(unsigned i=0;i<count;i++)VirtualFree(allocated[i],0,MEM_RELEASE);return false;}allocated[count++]=t;memcpy(t,(void*)h.addr,h.len);if(h.addr==0x437ad0)*(int32_t*)(t+3)=int32_t(0x43b400-uintptr_t(t+7));t[h.len]=0xe9;*(int32_t*)(t+h.len+1)=int32_t(h.addr+h.len-uintptr_t(t+h.len+5));*h.original=t;}}
 auto protect=[&](uintptr_t addr){uintptr_t p=addr&~uintptr_t(4095);for(unsigned i=0;i<pageCount;i++)if(pages[i]==p)return true;DWORD old;if(!VirtualProtect((void*)p,4096,PAGE_EXECUTE_READWRITE,&old))return false;pages[pageCount]=p;protections[pageCount++]=old;return true;};
 bool ok=true;for(auto& h:hooks){if(!protect(h.addr)||!protect(h.addr+h.len-1)){ok=false;break;}}if(ok)ok=protect(0x47406c)&&protect(0x412015)&&protect(0x412019)&&*(unsigned char*)0x412015==0xe8&&*(int32_t*)0x412016==int32_t(0x415b70-0x41201a);
 if(!ok){for(unsigned i=0;i<pageCount;i++){DWORD ignored;VirtualProtect((void*)pages[i],4096,protections[i],&ignored);}for(unsigned i=0;i<count;i++)VirtualFree(allocated[i],0,MEM_RELEASE);return false;}
 for(auto& h:hooks){memset((void*)h.addr,0x90,h.len);*(unsigned char*)h.addr=0xe9;*(int32_t*)(h.addr+1)=int32_t(uintptr_t(h.replacement)-h.addr-5);FlushInstructionCache(GetCurrentProcess(),(void*)h.addr,h.len);}
 *(int32_t*)0x412016=int32_t(uintptr_t(HistPos)-0x41201a);   // backlog.inc: $console_hist_pos's call in the syscall switch
 *(void**)0x474150=(void*)FCCreateFile;*(void**)0x474130=(void*)FCDeleteFile;*(void**)0x474134=(void*)FCCopyFile;*(void**)0x47419c=(void*)FCFindFirst;
 oldMciCreate=*(decltype(oldMciCreate)*)0x474214;*(void**)0x474214=(void*)MovieCreate;*(void**)0x474318=(void*)MovieMove;   // movie.inc: MCIWndCreateA·MoveWindow
 *(void**)0x47406c=(void*)Present;*(void**)0x474374=(void*)ToClient;*(void**)0x47425c=(void*)ToScreen;*(void**)0x474270=(void*)ClipToGame;*(void**)0x474260=(void*)Invalidate;*(void**)0x4742d0=(void*)WindowShow;
 if(GetEnvironmentVariableW(L"RECON_HITCH",nullptr,0)>0){*(void**)0x4740b0=(void*)HitchSleep;*(void**)0x4740e8=(void*)HitchRead;}   // hitch.inc: the game thread's sleeps and file reads
 for(unsigned i=0;i<pageCount;i++){DWORD ignored;VirtualProtect((void*)pages[i],4096,protections[i],&ignored);}return true;}
BOOL WINAPI DllMain(HINSTANCE, DWORD reason,LPVOID reserved){if(reason==DLL_PROCESS_ATTACH){if(!Install())return FALSE;}
 if(reason==DLL_PROCESS_DETACH&&reserved)cproto::Abandon();   // the game is closing: the prototype's objects are kept, not released under the loader lock
 return TRUE;}



