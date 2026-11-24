// ------------------------------------------------------------------------------------------------ screen batch
// The chronicle restamps its whole screen from its timeline layers every frame (~340 blits: per tile a Copy of the base
// layer, Masks of the overlay layers on the same box, then the frame art; one overlay's level pulses, so no two frames are
// alike), and since v19 every blit runs twice, on the screen and on its other-quality copy. One blit at a time that is
// ~40 ms a frame. Story scenes do the same while anything moves: the engine redraws the screen as 75 cells of 160x40, each
// a Copy, a Mask and an Alpha of its layers (250 blits, ~21 ms of 4x work a frame at 34 ms; hitch-read-trace2). So 4x
// Copy/Mask/Alpha blits onto the screen wait in a queue and settle at the next present, split into row bands: each band
// worker runs the whole queue in order, clipped to its own rows, so every pixel sees the same blits in the same order as
// before and there is one hand-off a frame.
// The queue settles first, in order, before anything changes what it reads or writes: a low-res sync of a queued shadow,
// a load, free, CG swap, alternate made or dropped, mode switch, capture or any other 4x blit. storymap-defer.off beside
// the DLL turns this off; RECON_DEFER_VERIFY=1 also runs every queue one blit at a time on copies and compares both buffers.
// mask1: a Mask's 1x mask (SparseMask); src1: the engine's source (DumpLayers)
struct Queued {char kind;Bitmap srcB,altB;Box x,y;int t;bool alt;bool covered=false;const Bitmap*mask1=nullptr,*src1=nullptr;};
static std::vector<Queued> queued;static std::unordered_set<Shadow*> queuedRefs;static Shadow*queueScreen=nullptr;
static bool deferOn=false,deferOff=false,deferChecked=false,deferVerify=false,chronicleSeen=false;
static uint64_t dFrames=0,dOps=0,dSettles=0,dMismatch=0,dCovered=0;
// An op whose box lies inside a later Copy's box is overwritten before anything reads it: the first frame of the engine's
// crossfade paints each cell's new background and sprites and then lays the old picture over them with an opaque Copy
// (hitch-read-parnear-trace, frame 988: 75 cells of Copy, Mask, Copy). Every queued op writes and reads the screen only
// inside its own box, so a covered op is skipped; RECON_DEFER_VERIFY still runs every op for its reference.
static void MarkCovered(){if(Off(OFF_COVER))return;std::vector<Box> copies;for(size_t i=queued.size();i-->0;){auto&q=queued[i];
 for(auto&c:copies)if(q.y.x>=c.x&&q.y.y>=c.y&&q.y.x+q.y.w<=c.x+c.w&&q.y.y+q.y.h<=c.y+c.h){q.covered=true;dCovered++;break;}if(!q.covered&&q.kind=='C')copies.push_back(q.y);}}
static const char kChronicleArt[]="\x83\x4e\x83\x8d\x83\x6a\x83\x4e\x83\x8b\x98\x67";   // クロニクル枠 in Shift-JIS
static bool IsChronicleArt(Bitmap*a){auto it=assets.find(a);return it!=assets.end()&&it->second.name.find(kChronicleArt)!=std::string::npos;}
static void RunOne(const Queued&q,Bitmap*dst,Bitmap*alt){
 for(int v=0;v<(q.alt&&alt?2:1);v++){Bitmap a=v?q.altB:q.srcB;Bitmap*d=v?alt:dst;if(q.kind=='C')Banded(oldCopy,nullptr,&a,q.x,d,q.y,0);else Banded(nullptr,q.kind=='A'?oldAlpha:oldMask,&a,q.x,d,q.y,q.t);}}
// A Mask leaves the screen as it was wherever its mask is clear (255: m=256 keeps dst), yet it read and blended every 4x
// pixel of its box. The chronicle's frame art is three quarters clear (69% of its 16-px tiles) and its text layers mostly so
// (10-25: 「연표가 아직도 느린데 연표 자체를 효율화하는게 어떨까?」). Where the source's 1x mask is clear its 4x mask is
// clear too: a loaded 4x mask is clipped to its 1x mask (ClipMaskToBase), and a 4x glyph averages down to its 1x pixel, so
// a clear 1x pixel had 16 clear subpixels. So each band runs a Mask only on the column runs of 8-row blocks of the 1x mask
// that hold anything; gaps under 4 columns are run through. RECON_OFF=sparse runs every Mask whole; the defer verify
// compares with whole blits.
static std::atomic<uint64_t> dSparseTotal{0},dSparseSkipped{0};   // 4x pixels of Masks, and of those skipped
static void SparseMask(const Queued&q,Bitmap*a,Bitmap*d,const Box&sx,const Box&dx){
 // outside the source bitmap the engine's clip draws nothing, so only its columns and rows are read
 const Bitmap*m=q.mask1;int c0=std::max(0,sx.x>>2),c1=std::min({(sx.x+sx.w+3)>>2,m->w,c0+2048});int64_t drawn=0;unsigned char any[2048];
 for(int r4=sx.y;r4<sx.y+sx.h;){int e4=std::min(sx.y+sx.h,(((r4>>2)&~7)+8)*4),rA=std::max(0,r4>>2),rB=std::min(((e4-1)>>2)+1,m->h);
  if(c1>c0)memset(any,0,size_t(c1-c0));
  for(int r=rA;r<rB;r++){const unsigned char*row=m->pixels+size_t(r)*m->pitch;for(int c=c0;c<c1;c++)any[c-c0]|=row[c]!=255;}
  for(int c=c0;c<c1;c++){if(!any[c-c0])continue;int last=c;for(int k=c+1;k<c1&&k-last<=4;k++)if(any[k-c0])last=k;   // up to 3 clear columns between are run through
   int w=(last+1-c)*4;Box s{c*4,r4,w,e4-r4},t{dx.x+(c*4-sx.x),dx.y+(r4-sx.y),w,e4-r4};oldMask(a,&s,d,&t,q.t);drawn+=int64_t(w)*(e4-r4);c=last;}
  r4=e4;}
 int64_t all=int64_t(sx.w)*sx.h;dSparseTotal+=uint64_t(all);dSparseSkipped+=uint64_t(std::max<int64_t>(0,all-drawn));}
// perf op 5: the next queue's sources as the engine has them (qa\layer-<n>.bmp, layer-<n>-mask.bmp), and a line each: size,
// name, its blits, and how much of its mask is not clear, in all and inside the boxes this frame shows
static bool dumpLayers=false,dumpLayers4k=false;   // op 4: the sources' 4x and 4x masks as well (layer-<n>-4k.bmp, -4kmask.bmp)
static void SaveLayer(const wchar_t*path,const Bitmap*b){FILE*f=nullptr;if(!b||!b->pixels||_wfopen_s(&f,path,L"wb")||!f)return;int ch=b->format?1:3,stride=(b->w*3+3)&~3;
 BITMAPFILEHEADER fh{0x4d42,DWORD(54+size_t(stride)*b->h),0,0,54};BITMAPINFOHEADER ih{sizeof(BITMAPINFOHEADER),b->w,-b->h,1,24,BI_RGB};fwrite(&fh,sizeof fh,1,f);fwrite(&ih,sizeof ih,1,f);
 std::vector<unsigned char> row(stride,0);for(int y=0;y<b->h;y++){const unsigned char*p=b->pixels+size_t(y)*b->pitch;
  if(ch==3)memcpy(row.data(),p,size_t(b->w)*3);else for(int x=0;x<b->w;x++){unsigned char v=p[x];if(b->palette){auto&c=b->palette[v];row[x*3]=c.rgbBlue;row[x*3+1]=c.rgbGreen;row[x*3+2]=c.rgbRed;}else row[x*3]=row[x*3+1]=row[x*3+2]=v;}
  fwrite(row.data(),1,stride,f);}fclose(f);}
static void DumpLayers(){std::vector<const Bitmap*> order;std::unordered_map<const Bitmap*,std::vector<const Queued*>> uses;
 for(auto&q:queued)if(q.src1){if(!uses.count(q.src1))order.push_back(q.src1);uses[q.src1].push_back(&q);}
 for(size_t i=0;i<order.size();i++){const Bitmap*b=order[i];auto&u=uses[b];wchar_t path[MAX_PATH];swprintf_s(path,L"%s\\qa\\layer-%02zu.bmp",root,i);SaveLayer(path,b);
  const Bitmap*m=b->mask&&b->mask!=b&&b->mask->pixels&&b->mask->w==b->w&&b->mask->h==b->h?b->mask:nullptr;uint64_t solid=0,inBox=0,solidInBox=0;
  if(m){swprintf_s(path,L"%s\\qa\\layer-%02zu-mask.bmp",root,i);SaveLayer(path,m);std::vector<unsigned char> seen(size_t(b->w)*b->h,0);
   for(auto*q:u){Box r{q->x.x/4,q->x.y/4,q->x.w/4,q->x.h/4};for(int y=std::max(0,r.y);y<std::min(b->h,r.y+r.h);y++)for(int x=std::max(0,r.x);x<std::min(b->w,r.x+r.w);x++)seen[size_t(y)*b->w+x]=1;}
   for(int y=0;y<b->h;y++){const unsigned char*row=m->pixels+size_t(y)*m->pitch;for(int x=0;x<b->w;x++){bool s=row[x]!=255,v=seen[size_t(y)*b->w+x]!=0;solid+=s;inBox+=v;solidInBox+=s&&v;}}}
  auto a=assets.find(const_cast<Bitmap*>(b));std::vector<int> ts;uint64_t area=0;for(auto*q:u){ts.push_back(q->t);area+=uint64_t(q->x.w/4)*(q->x.h/4);}
  std::sort(ts.begin(),ts.end());ts.erase(std::unique(ts.begin(),ts.end()),ts.end());std::string tl;for(int t:ts)tl+=std::to_string(t)+",";
  auto sh=shadows.find(const_cast<Bitmap*>(b));auto mv=perfMoved.find(b);
  if(dumpLayers4k&&sh!=shadows.end()){Shadow*s4=sh->second.get();Bitmap v=s4->b;v.pixels=s4->pixels.data();swprintf_s(path,L"%s\\qa\\layer-%02zu-4k.bmp",root,i);SaveLayer(path,&v);
   if(s4->maskShadow){Bitmap mv4=s4->maskShadow->b;mv4.pixels=s4->maskShadow->pixels.data();mv4.palette=nullptr;swprintf_s(path,L"%s\\qa\\layer-%02zu-4kmask.bmp",root,i);SaveLayer(path,&mv4);}}
  if(logFile)fprintf(logFile,"layer n=%02zu src=%p %dx%d fmt=%d kind=%c blits=%zu area=%llu t=%s alt=%d mask=%d solid_pct=%.1f shown_px=%llu solid_shown_pct=%.1f rev=%llu synced_px=%llu name=%s\n",i,(void*)b,b->w,b->h,b->format,u[0]->kind,u.size(),(unsigned long long)area,tl.c_str(),int(u[0]->alt),m!=nullptr,
   m?100.0*solid/(double(b->w)*b->h):0.0,(unsigned long long)inBox,inBox?100.0*solidInBox/double(inBox):0.0,sh!=shadows.end()?(unsigned long long)sh->second->revision:0ull,mv!=perfMoved.end()?(unsigned long long)mv->second:0ull,a!=assets.end()?a->second.name.c_str():"");}
 dumpLayers4k=false;if(logFile){fprintf(logFile,"layers done n=%zu ops=%zu\n",order.size(),queued.size());fflush(logFile);}}
struct FrameJob {Bitmap main,alt;bool hasAlt;int bands;};
// One band: the whole queue in order, each blit clipped to this band's screen rows (the engine's loops are row-local).
static void BandFrame(void*p,int k){auto&j=*(FrameJob*)p;int r0=MulDiv(j.main.h,k,j.bands),r1=MulDiv(j.main.h,k+1,j.bands);
 for(auto&q:queued){int y0=std::max(q.y.y,r0),y1=std::min(q.y.y+q.y.h,r1);if(y1<=y0||q.covered)continue;Box sx{q.x.x,q.x.y+(y0-q.y.y),q.x.w,y1-y0},dx{q.y.x,y0,q.y.w,y1-y0};
  for(int v=0;v<(q.alt&&j.hasAlt?2:1);v++){Bitmap a=v?q.altB:q.srcB;Bitmap*d=v?&j.alt:&j.main;if(q.kind=='C')oldCopy(&a,&sx,d,&dx);else if(q.kind=='A')oldAlpha(&a,&sx,d,&dx,q.t);
   else if(q.mask1&&!Off(OFF_SPARSE))SparseMask(q,&a,d,sx,dx);else oldMask(&a,&sx,d,&dx,q.t);}}}
static void Execute(){if(queued.empty())return;Shadow*s=queueScreen;LONGLONG t0=Now();
 bool hasAlt=!s->alternate.empty();Bitmap altDst{};if(hasAlt)altDst=AltBitmap(s);
 std::vector<unsigned char> ref,refAlt;if(deferVerify){try{ref=s->pixels;if(hasAlt)refAlt=s->alternate;Bitmap scratch=s->b,scratchAlt=altDst;scratch.pixels=ref.data();if(hasAlt)scratchAlt.pixels=refAlt.data();
  for(auto&q:queued)RunOne(q,&scratch,hasAlt?&scratchAlt:nullptr);}catch(const std::bad_alloc&){ref.clear();refAlt.clear();}}
 MarkCovered();if(!bandPool.started)bandPool.Start();
 {FrameJob job{s->b,altDst,hasAlt,bandPool.workers?std::min(48,(bandPool.workers+1)*4):1};   // ~4 bands a thread keeps them even (24/48/96 measured: 48 best)
  if(job.bands<2||queued.size()<8){for(auto&q:queued)if(!q.covered)RunOne(q,&s->b,hasAlt?&altDst:nullptr);}else bandPool.Run(job.bands,BandFrame,&job);}
 if(deferVerify&&!ref.empty()&&(ref!=s->pixels||(hasAlt&&refAlt!=s->alternate))){dMismatch++;memcpy(s->pixels.data(),ref.data(),ref.size());if(hasAlt&&!refAlt.empty())memcpy(s->alternate.data(),refAlt.data(),refAlt.size());
  if(logFile){fprintf(logFile,"defer_mismatch frame=%llu ops=%zu\n",(unsigned long long)dFrames,queued.size());fflush(logFile);}}
 dOps+=queued.size();pCompose+=Ms(t0);queued.clear();queuedRefs.clear();}
static void SettleAll(){if(queued.empty())return;Execute();dSettles++;}
static void SettleFor(Shadow*s){if(s&&!queued.empty()&&(s==queueScreen||queuedRefs.count(s)))SettleAll();}
static bool Defer(char kind,Bitmap*a,Bitmap*b,Shadow*sa,Shadow*sb,const Box&x,const Box&y,int t){Bitmap*screen=*(Bitmap**)0x56a6a8;
 if(b==screen){screenDrawn=true;if(!chronicleSeen&&IsChronicleArt(a))chronicleSeen=true;}
 bool alt=!sa->alternate.empty()||!sb->alternate.empty();
 bool ok=deferOn&&b==screen&&a!=b&&sa!=sb&&!sb->b.mask&&!sb->b.format&&(!alt||!sb->alternate.empty())&&(queued.empty()||queueScreen==sb);
 if(!ok){SettleAll();return false;}   // a blit that reads the screen reads both copies
 if(queued.empty())queueScreen=sb;queued.push_back({kind,sa->b,alt?AltBitmap(sa):sa->b,x,y,t,alt});queued.back().src1=a;queuedRefs.insert(sa);if(sa->maskShadow)queuedRefs.insert(sa->maskShadow);
 if(kind=='M'&&!a->format&&a->mask&&a->mask->format&&a->mask->w==a->w&&a->mask->h==a->h&&a->mask->pixels&&sa->maskShadow)queued.back().mask1=a->mask;
 return true;}
// While the 연표 view covers the game's 연표 (cproto::Covered), its frames are dropped, but the part
// they touched is only noted, and caught up from the 1x screen once when the cover goes (no 4x work per frame meanwhile).
static int cvX0=INT_MAX,cvY0=INT_MAX,cvX1=0,cvY1=0;static bool cvPending=false;
static void CoveredDrop(){if(queued.empty())return;for(auto&q:queued){cvX0=std::min(cvX0,q.y.x/4);cvY0=std::min(cvY0,q.y.y/4);cvX1=std::max(cvX1,(q.y.x+q.y.w+3)/4);cvY1=std::max(cvY1,(q.y.y+q.y.h+3)/4);}
 queued.clear();queuedRefs.clear();cvPending=true;}
static void CoveredCatchUp(){if(!cvPending)return;cvPending=false;Shadow*s=queueScreen;Bitmap*b=*(Bitmap**)0x56a6a8;auto it=Valid(b)?shadows.find(b):shadows.end();
 if(it!=shadows.end()&&it->second.get()==s&&cvX1>cvX0&&cvY1>cvY0)Nearest(s,b,{cvX0,cvY0,cvX1-cvX0,cvY1-cvY0},false);cvX0=cvY0=INT_MAX;cvX1=cvY1=0;}
// At the start of each present: draw what this frame queued, then batch the next frame only if this one drew the chronicle.
static void FinishFrame(){
 if(!deferChecked){deferChecked=true;wchar_t f[MAX_PATH];swprintf_s(f,L"%s\\storymap-defer.off",root);deferOff=GetFileAttributesW(f)!=INVALID_FILE_ATTRIBUTES;deferVerify=GetEnvironmentVariableW(L"RECON_DEFER_VERIFY",nullptr,0)>0;
}
 if(dumpLayers&&queued.size()>=100){dumpLayers=false;DumpLayers();}   // a whole frame's queue, not a settle's part
 if(cproto::Covered())CoveredDrop();else{CoveredCatchUp();Execute();}dFrames++;bool on=!deferOff&&!Off(OFF_DEFER);
 // chronicleOpen: a present with nothing newly drawn (a repaint) keeps it; a drawn page without the frame closes it
 bool wasOpen=chronicleOpen;if(chronicleSeen)chronicleOpen=true;else if(screenDrawn&&chronicleOpen)chronicleOpen=false;
 if(wasOpen!=chronicleOpen&&logFile){fprintf(logFile,"chronicle_open=%d frame=%llu\n",chronicleOpen,(unsigned long long)dFrames);fflush(logFile);}
 cproto::Frame();   // the view shown, hidden and its actions stepped on this frame
 lastFrameDrew=screenDrawn;screenDrawn=false;chronicleSeen=false;
 if(on!=deferOn&&logFile){fprintf(logFile,"defer_%s frame=%llu\n",on?"on":"off",(unsigned long long)dFrames);fflush(logFile);}deferOn=on;
 if((perf||deferVerify)&&logFile&&dFrames%60==0){fprintf(logFile,"defer frames=%llu ops=%llu settles=%llu mismatched=%llu covered=%llu on=%d mask_px=%llu mask_skipped_pct=%.1f\n",(unsigned long long)dFrames,(unsigned long long)dOps,(unsigned long long)dSettles,(unsigned long long)dMismatch,(unsigned long long)dCovered,deferOn,
  (unsigned long long)dSparseTotal.load(),dSparseTotal.load()?100.0*double(dSparseSkipped.load())/double(dSparseTotal.load()):0.0);
  fflush(logFile);}}
