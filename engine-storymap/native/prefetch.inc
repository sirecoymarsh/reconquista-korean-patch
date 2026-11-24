// ------------------------------------------------------------------------------------------------ reading ahead
// prefetch.bin (tools/build_prefetch.py): the 4x pictures the scripts show by name ($disp_back, $disp_char), in script
// order, with their low-res size. After a load of one of them the next two are decoded on a low-priority thread into the
// decode cache, so the load that follows is a cache copy (~1 ms) instead of a 20-50 ms decode while the scene changes.
// Where the table has the picture several times, the first occurrence shortly after the last match is taken; after a jump
// (no such occurrence, and not a picture the table has once) nothing is read until the next picture places the reading.
// At most three pictures wait unasked in the cache or on the thread, so reading ahead cannot push out the pictures the
// scene keeps reloading (a jump-heavy test route read 24 ahead and used 2). A load whose picture is still being read ahead
// waits for it; one still queued is taken back and decoded as usual. RECON_OFF=ahead turns this off.
struct PfEntry {uint32_t key;uint16_t w,h;};
static std::vector<PfEntry> pfSeq;static std::unordered_map<uint32_t,std::vector<uint32_t>> pfPos;static int64_t pfCursor=-1;static bool pfTried=false;
struct PrefetchJob {uint32_t key=0;int w=0,h=0,pitch=0;bool jxl=false,png=false,started=false,done=false,jxlFailed=false;wchar_t path[MAX_PATH]{},jpath[MAX_PATH]{};std::vector<unsigned char> pixels;HRESULT hr=E_PENDING;double ms=0;};
static SRWLOCK pfLock=SRWLOCK_INIT;static CONDITION_VARIABLE pfWake=CONDITION_VARIABLE_INIT,pfFinished=CONDITION_VARIABLE_INIT;
static std::vector<PrefetchJob*> pfQueue,pfDone;static std::unordered_map<uint32_t,PrefetchJob*> pfLive;static uint64_t pfQueued=0,pfWaits=0,pfTaken=0;   // pfLive: main thread
// A JPEG XL runner on threads of lower priority, so decoding never takes cores from the game's frames: the background
// decodes (below normal) and reading ahead (lowest) run in the gaps the band workers leave.
struct LowPool {PTP_POOL pool=nullptr;TP_CALLBACK_ENVIRON env{};int n=0,priority=THREAD_PRIORITY_BELOW_NORMAL;struct Slot{LowPool*p;int i;PTP_WORK work;} slots[16]{};void*opaque=nullptr;JxlParallelRunFunction fn=nullptr;std::atomic<uint32_t> next{0};uint32_t end=0;};
static LowPool lowPool;
static void CALLBACK LowWork(PTP_CALLBACK_INSTANCE,void*ctx,PTP_WORK){auto*s=(LowPool::Slot*)ctx;auto*p=s->p;SetThreadPriority(GetCurrentThread(),p->priority);for(uint32_t v;(v=p->next.fetch_add(1))<p->end;)p->fn(p->opaque,v,size_t(s->i));}
static JxlParallelRetCode LowRun(void*runner,void*opaque,JxlParallelRunInit init,JxlParallelRunFunction fn,uint32_t start,uint32_t end){auto*p=(LowPool*)runner;if(init(opaque,size_t(p->n))!=0)return -1;if(start>=end)return 0;
 p->opaque=opaque;p->fn=fn;p->next=start;p->end=end;for(int i=0;i<p->n;i++)SubmitThreadpoolWork(p->slots[i].work);for(int i=0;i<p->n;i++)WaitForThreadpoolWorkCallbacks(p->slots[i].work,FALSE);return 0;}
static bool LowStart(LowPool&p,int n,int priority){n=std::clamp(n,1,16);p.priority=priority;if(!(p.pool=CreateThreadpool(nullptr)))return false;SetThreadpoolThreadMaximum(p.pool,DWORD(n));SetThreadpoolThreadMinimum(p.pool,1);InitializeThreadpoolEnvironment(&p.env);SetThreadpoolCallbackPool(&p.env,p.pool);
 for(int i=0;i<n;i++){p.slots[i]={&p,i,CreateThreadpoolWork(LowWork,&p.slots[i],&p.env)};if(!p.slots[i].work)return false;p.n=i+1;}return true;}
static DWORD WINAPI PrefetchWorker(void*){SetThreadPriority(GetCurrentThread(),THREAD_PRIORITY_LOWEST);CoInitializeEx(nullptr,COINIT_MULTITHREADED);bool low=LowStart(lowPool,8,THREAD_PRIORITY_LOWEST);
 for(;;){AcquireSRWLockExclusive(&pfLock);while(pfQueue.empty())SleepConditionVariableSRW(&pfWake,&pfLock,INFINITE,0);PrefetchJob*j=pfQueue.front();pfQueue.erase(pfQueue.begin());j->started=true;ReleaseSRWLockExclusive(&pfLock);
  LONGLONG t=Now();HRESULT hr=E_FAIL;try{j->pixels.resize(size_t(j->pitch)*j->h);}catch(const std::bad_alloc&){j->pixels.clear();}
  if(!j->pixels.empty()&&j->jxl){JxlArt art;if(art.Open(j->jpath,j->w,j->h,3,low?LowRun:nullptr,low?&lowPool:nullptr))hr=art.Finish(j->pixels.data(),j->pitch);if(FAILED(hr))j->jxlFailed=true;}
  if(!j->pixels.empty()&&FAILED(hr)&&j->png){PngArt art;hr=art.Open(j->path,UINT(j->w),UINT(j->h),0);if(SUCCEEDED(hr))hr=art.CopyTo(j->pixels.data(),j->pitch,j->pixels.size());}
  j->hr=hr;j->ms=Ms(t);AcquireSRWLockExclusive(&pfLock);j->done=true;pfDone.push_back(j);ReleaseSRWLockExclusive(&pfLock);WakeAllConditionVariable(&pfFinished);}}
// finished pictures into the decode cache (main thread)
static void PrefetchDrain(){std::vector<PrefetchJob*> done;AcquireSRWLockExclusive(&pfLock);done.swap(pfDone);ReleaseSRWLockExclusive(&pfLock);
 for(auto*j:done){pfLive.erase(j->key);if(j->jxlFailed)JxlFailed(j->key,"ahead");if(SUCCEEDED(j->hr))KeepAhead(j->key,j->w,j->h,0,j->pixels);
  if(perf&&logFile)fprintf(logFile,"prefetch_done key=%08x ok=%d ms=%.1f hits=%llu unused=%llu taken=%llu waits=%llu\n",j->key,SUCCEEDED(j->hr),j->ms,pfHits,pfUnused,pfTaken,pfWaits);delete j;}}
// a load wants key: wait for it if it is being read ahead, take it back if it is still queued
static void PrefetchClaim(uint32_t key){auto it=pfLive.find(key);if(it==pfLive.end())return;PrefetchJob*j=it->second;LONGLONG t=Now();bool waited=false;
 AcquireSRWLockExclusive(&pfLock);if(!j->started){pfQueue.erase(std::remove(pfQueue.begin(),pfQueue.end(),j),pfQueue.end());ReleaseSRWLockExclusive(&pfLock);pfLive.erase(it);delete j;pfTaken++;return;}
 while(!j->done){waited=true;SleepConditionVariableSRW(&pfFinished,&pfLock,INFINITE,0);}ReleaseSRWLockExclusive(&pfLock);pfWaits+=waited;
 PrefetchDrain();if(perf&&logFile&&waited)fprintf(logFile,"prefetch_wait key=%08x ms=%.1f\n",key,Ms(t));}
static void PrefetchLoad(){pfTried=true;wchar_t path[MAX_PATH];swprintf_s(path,L"%s\\prefetch.bin",root);FILE*f=nullptr;if(_wfopen_s(&f,path,L"rb")||!f)return;
 char magic[4]{};uint32_t n=0;if(fread(magic,1,4,f)==4&&!memcmp(magic,"RPF1",4)&&fread(&n,4,1,f)==1&&n<(1u<<20)){pfSeq.resize(n);if(fread(pfSeq.data(),sizeof(PfEntry),n,f)!=n)pfSeq.clear();}fclose(f);
 for(uint32_t i=0;i<pfSeq.size();i++)if(pfSeq[i].key)pfPos[pfSeq[i].key].push_back(i);
 if(logFile){fprintf(logFile,"prefetch table=%zu pictures=%zu\n",pfSeq.size(),pfPos.size());fflush(logFile);}}
static void PrefetchAfter(uint32_t key){if(Off(OFF_AHEAD)||flowWarmStage)return;if(!pfTried)PrefetchLoad();auto it=pfPos.find(key);if(it==pfPos.end())return;const auto&at=it->second;int64_t p=-1;bool sure=false;
 for(auto q:at)if(int64_t(q)>pfCursor&&int64_t(q)<=pfCursor+96){p=q;sure=true;break;}
 if(p<0){p=at[0];sure=at.size()==1;for(auto q:at)if(std::llabs(int64_t(q)-pfCursor)<std::llabs(p-pfCursor))p=q;}
 pfCursor=p;if(!sure)return;static int workers=0;int queued=0;
 for(size_t q=size_t(p)+1;q<pfSeq.size()&&pfSeq[q].key&&queued<2&&pfAhead+int(pfLive.size())<3&&q<=size_t(p)+12;q++){const PfEntry&e=pfSeq[q];uint32_t k=e.key;if(k==key||decodedArt.count(k)||pfLive.count(k)||missing.count(k))continue;
  wchar_t path[MAX_PATH],jpath[MAX_PATH];swprintf_s(path,L"%s\\hires\\%08x.png",root,k);swprintf_s(jpath,L"%s\\hires-jxl\\%08x.jxl",root,k);bool png=false,jx=JxlCurrent(k,jpath,path,png);if(!png&&!jx)continue;
  if(!workers){if(HANDLE t=CreateThread(nullptr,0,PrefetchWorker,nullptr,0,nullptr)){CloseHandle(t);workers=1;}else return;}
  auto*j=new PrefetchJob();j->key=k;j->w=e.w*4;j->h=e.h*4;j->pitch=(j->w*3+3)&~3;j->jxl=jx;j->png=png;wcscpy_s(j->path,path);wcscpy_s(j->jpath,jpath);
  pfLive[k]=j;AcquireSRWLockExclusive(&pfLock);pfQueue.push_back(j);ReleaseSRWLockExclusive(&pfLock);WakeConditionVariable(&pfWake);queued++;pfQueued++;}}
