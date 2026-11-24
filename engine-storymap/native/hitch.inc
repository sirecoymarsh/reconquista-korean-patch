// Stutter profiler (RECON_HITCH=1, run with RECON_PERF=2 so the layer's own timers count): for every gap between two
// presents, what the game thread did in it — its CPU time (cycle counter), time asleep in Sleep, time in ReadFile, and the
// 4K layer's share (picture decode, 1x->4x sync, deferred compose, scale+present) — so a long frame can be put down to the
// engine, the layer, the disk or waiting. Gaps over 30 ms are logged one by one with what happened in them; all gaps go
// into a histogram logged every 600 presents. Off unless asked for; the game runs the same either way.
#include <intrin.h>
static DWORD hitchTid=0;static HANDLE hitchThread=nullptr;static double hCyclesPerMs=0;   // hitch, hShadows: next to the perf timers
static double hSleepMs=0,hReadMs=0,hGdiMs=0;static uint64_t hReadBytes=0,hReads=0,hAlphas=0,hTexts=0;
// Per gap, who slept most (caller address, total, calls and the Sleep argument) and the slowest single read (file, offset, size).
struct HitchSleeper {uintptr_t at=0;double ms=0;unsigned calls=0;DWORD arg=0;};static HitchSleeper hSleepers[8];static unsigned hSleeperCount=0;
static double hSlowRead=0;static wchar_t hSlowName[96]{};static uint64_t hSlowOffset=0;static DWORD hSlowBytes=0;
static void WINAPI HitchSleep(DWORD ms){if(GetCurrentThreadId()!=hitchTid){Sleep(ms);return;}uintptr_t at=uintptr_t(_ReturnAddress());LONGLONG t=Now();Sleep(ms);double d=Ms(t);hSleepMs+=d;
 unsigned i=0;while(i<hSleeperCount&&hSleepers[i].at!=at)i++;if(i==hSleeperCount&&hSleeperCount<8)hSleepers[hSleeperCount++].at=at;if(i<8){hSleepers[i].ms+=d;hSleepers[i].calls++;hSleepers[i].arg=ms;}}
static BOOL WINAPI HitchRead(HANDLE f,LPVOID b,DWORD n,LPDWORD got,LPOVERLAPPED o){if(GetCurrentThreadId()!=hitchTid)return ReadFile(f,b,n,got,o);
 LARGE_INTEGER pos{},zero{};SetFilePointerEx(f,zero,&pos,FILE_CURRENT);LONGLONG t=Now();BOOL ok=ReadFile(f,b,n,got,o);double d=Ms(t);hReadMs+=d;hReads++;if(ok&&got)hReadBytes+=*got;
 if(d>hSlowRead){hSlowRead=d;hSlowOffset=uint64_t(pos.QuadPart);hSlowBytes=n;wchar_t full[MAX_PATH]{};DWORD len=GetFinalPathNameByHandleW(f,full,MAX_PATH,0);const wchar_t*name=len?wcsrchr(full,L'\\'):nullptr;wcsncpy_s(hSlowName,name?name+1:L"?",_TRUNCATE);}
 return ok;}
struct HitchSnap {LONGLONG t=0;ULONG64 cycles=0;double sleep=0,read=0,decode=0,nearest=0,compose=0,gdi=0,alt=0,free=0,load=0,engLoad=0,hook=0,engBlit=0,pair=0,snap=0;uint64_t loads=0,bytes=0,reads=0,shadows=0,alphas=0,texts=0,altMade=0,altDropped=0,spareHit=0,spareMiss=0,reuse=0;};
static HitchSnap hPrev;static unsigned hBuckets[8]{};static unsigned hFrames=0;static double hWorst=0;
static HitchSnap HitchNow(){HitchSnap s;s.t=Now();QueryThreadCycleTime(hitchThread,&s.cycles);s.sleep=hSleepMs;s.read=hReadMs;s.decode=hDecodeDone+pDecode;s.nearest=hNearestDone+pNearest;s.compose=hComposeDone+pCompose;s.gdi=hGdiMs;
 s.loads=loads;s.bytes=hReadBytes;s.reads=hReads;s.shadows=hShadows;s.alphas=hAlphas;s.texts=hTexts;
 s.alt=hAltMs;s.free=hFreeMs;s.load=hLoadMs;s.engLoad=hEngLoadMs;s.hook=hHookMs;s.engBlit=hEngBlitMs;s.pair=hPairMs;s.snap=hSnapMs;s.altMade=hAltMade;s.altDropped=hAltDropped;s.spareHit=hSpareHit;s.spareMiss=hSpareMiss;s.reuse=hLoadReuse;return s;}
// At the start of each present (the game thread).
static void HitchFrame(){if(!hitch)return;
 if(!hitchThread){hitchTid=GetCurrentThreadId();DuplicateHandle(GetCurrentProcess(),GetCurrentThread(),GetCurrentProcess(),&hitchThread,THREAD_QUERY_INFORMATION|THREAD_QUERY_LIMITED_INFORMATION,FALSE,0);
  ULONG64 c0=0,c1=0;QueryThreadCycleTime(hitchThread,&c0);LONGLONG t0=Now();while(Ms(t0)<20){}QueryThreadCycleTime(hitchThread,&c1);hCyclesPerMs=double(c1-c0)/Ms(t0);hPrev=HitchNow();
  if(logFile){fprintf(logFile,"hitch_start cycles_per_ms=%.0f\n",hCyclesPerMs);fflush(logFile);}return;}
 HitchSnap s=HitchNow();double gap=1000.0*(s.t-hPrev.t)/freq.QuadPart,cpu=hCyclesPerMs>0?double(s.cycles-hPrev.cycles)/hCyclesPerMs:0;
 static int recorded=0;if(traceRecord){if(gap>50&&cpu>gap/2&&recorded<24&&!traceBuffer.empty()&&logFile){recorded++;fprintf(logFile,"trace_frame frame=%u gap=%.1f cpu=%.1f lines=%u\n",hFrames+1,gap,cpu,traceLines);fputs(traceBuffer.c_str(),logFile);fflush(logFile);}traceBuffer.clear();traceLines=0;}
 static int traced=0;if(traceFrames)traceFrames--;else if(traced<6&&s.alphas-hPrev.alphas>=150&&s.compose-hPrev.compose>10&&gap>30){traced++;traceFrames=1;if(logFile){fprintf(logFile,"trace_next frame=%u alphas=%llu\n",hFrames,(unsigned long long)(s.alphas-hPrev.alphas));fflush(logFile);}}   // what a heavy frame draws
 static const double edges[]={17,25,33,50,100,200,400};int b=0;while(b<7&&gap>=edges[b])b++;hBuckets[b]++;hFrames++;hWorst=std::max(hWorst,gap);
 if(gap>30&&logFile){fprintf(logFile,"hitch gap=%.1f cpu=%.1f sleep=%.1f read=%.1f/%lluKB/%llu decode=%.1f nearest=%.1f compose=%.1f gdi=%.1f loads=%llu shadows=%llu alphas=%llu texts=%llu frame=%u\n",
  gap,cpu,s.sleep-hPrev.sleep,s.read-hPrev.read,(unsigned long long)((s.bytes-hPrev.bytes)>>10),(unsigned long long)(s.reads-hPrev.reads),s.decode-hPrev.decode,s.nearest-hPrev.nearest,s.compose-hPrev.compose,s.gdi-hPrev.gdi,
  (unsigned long long)(s.loads-hPrev.loads),(unsigned long long)(s.shadows-hPrev.shadows),(unsigned long long)(s.alphas-hPrev.alphas),(unsigned long long)(s.texts-hPrev.texts),hFrames);
  fprintf(logFile,"hitch_more load=%.1f engine_load=%.1f hooks=%.1f engine_blit=%.1f pair=%.1f snapshot=%.1f alternates=%.1f/%llu+/%llu- free=%.1f reused_loads=%llu spare=%llu/%llu\n",s.load-hPrev.load,s.engLoad-hPrev.engLoad,s.hook-hPrev.hook,s.engBlit-hPrev.engBlit,
   s.pair-hPrev.pair,s.snap-hPrev.snap,s.alt-hPrev.alt,(unsigned long long)(s.altMade-hPrev.altMade),(unsigned long long)(s.altDropped-hPrev.altDropped),s.free-hPrev.free,(unsigned long long)(s.reuse-hPrev.reuse),
   (unsigned long long)(s.spareHit-hPrev.spareHit),(unsigned long long)(s.spareHit-hPrev.spareHit+s.spareMiss-hPrev.spareMiss));
  const HitchSleeper*top=nullptr;for(unsigned i=0;i<hSleeperCount;i++)if(!top||hSleepers[i].ms>top->ms)top=&hSleepers[i];
  if(top&&top->ms>5)fprintf(logFile,"hitch_sleep at=%08x ms=%.1f calls=%u arg=%lu\n",unsigned(top->at),top->ms,top->calls,top->arg);
  if(hSlowRead>5)fprintf(logFile,"hitch_read file=%S offset=%llu bytes=%lu ms=%.1f\n",hSlowName,(unsigned long long)hSlowOffset,hSlowBytes,hSlowRead);fflush(logFile);}
 hSleeperCount=0;for(auto&x:hSleepers)x=HitchSleeper{};hSlowRead=0;
 // every 120 presents, the game thread's mean frame split (the chronicle's frames are short, so no gap gets its own line)
 static HitchSnap hAvg;static unsigned hAvgFrames=0;if(!hAvg.t)hAvg=hPrev;
 if(++hAvgFrames==120&&logFile){double n=hAvgFrames,g=1000.0*(s.t-hAvg.t)/freq.QuadPart/n,c=hCyclesPerMs>0?double(s.cycles-hAvg.cycles)/hCyclesPerMs/n:0;
  fprintf(logFile,"hitch_avg frames=%u gap=%.2f cpu=%.2f sleep=%.2f hooks=%.2f pair=%.2f engine_blit=%.2f snapshot=%.2f nearest=%.2f compose=%.2f gdi=%.2f alternates=%.2f\n",hFrames,g,c,(s.sleep-hAvg.sleep)/n,(s.hook-hAvg.hook)/n,
   (s.pair-hAvg.pair)/n,(s.engBlit-hAvg.engBlit)/n,(s.snap-hAvg.snap)/n,(s.nearest-hAvg.nearest)/n,(s.compose-hAvg.compose)/n,(s.gdi-hAvg.gdi)/n,(s.alt-hAvg.alt)/n);fflush(logFile);hAvg=s;hAvgFrames=0;}
 if(hFrames%600==0&&logFile){fprintf(logFile,"hitch_histogram frames=%u lt17=%u lt25=%u lt33=%u lt50=%u lt100=%u lt200=%u lt400=%u ge400=%u worst=%.1f\n",hFrames,hBuckets[0],hBuckets[1],hBuckets[2],hBuckets[3],hBuckets[4],hBuckets[5],hBuckets[6],hBuckets[7],hWorst);HitchMemory();fflush(logFile);}
 hPrev=s;}
