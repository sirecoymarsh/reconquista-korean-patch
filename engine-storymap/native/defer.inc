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
// mask1: a Mask's 1x mask (SparseMask); src1, sa, maskLow, ma: the engine's source, its shadow, its 1x mask and that mask's
// shadow (low-res mode; ma as queued: a later Get of the source without its mask drops sa->maskShadow)
struct Queued {char kind;Bitmap srcB,altB;Box x,y;int t;bool alt;bool covered=false;const Bitmap*mask1=nullptr,*src1=nullptr,*maskLow=nullptr;Shadow*sa=nullptr,*ma=nullptr;};
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
// ------------------------------------------------------------------------------------------------ 연표 low-res mode
// The user, 10-25: 「여기 고해상도가 있을 필요가 없는데 눈에 보이는 글자들과 아이콘만 해상도 높이고 나머진 선만 선명한
// 저해상도」. While the 연표 is up, a screen pixel whose 4x would come out as its widened 1x pixel is not drawn at 4x: it is
// widened from the engine's 1x screen, which has drawn it already. Only where something 4x reaches (the frame art's lettering
// and ornament edges, buttons, name plates, 4x text) does the queue run at 4x. That follows each source's hi (Shadow): 1 where
// its 4x block is more than hiT from its 1x pixel. Blits carry hi to the screen at 1x: an opaque pixel takes its source's, a
// see-through one adds it. The 연표's own layers are mostly the engine's 1x drawing widened (its event layer ~97% Nearest), so
// ~93% of the screen is widened. Only the shown copy is drawn; the other-quality copy is brought up to it when the mode ends
// (LowResFixAlt). RECON_OFF=lowres draws at 4x as before; RECON_DEFER_VERIFY=1 also draws the old way and logs the difference.
static int hiT=24;   // RECON_HI_T; 10-25 locked 연표: above 24 are 5.6% of the frame art, 17.8% of the name plates, 0 of the events
static int lrRows=8,lrGap=4;   // RECON_LOWRES_ROWS, RECON_LOWRES_GAP: a 4x run is up to lrRows 1x rows tall and runs through gaps under lrGap
static uint64_t lrFrames=0,lrReplay=0,lrFill=0,lrDiff=0,lrOver=0,lrChecked=0,hiBuilt=0;static int lrWorst=0;
struct HiJob {Shadow*s;Box r;int w1,pitch1,ch,bands;};static std::unordered_map<const Shadow*,uint64_t> hiBuiltBy;   // perf: who is compared most
static void HiBand(void*p,int k){auto&j=*(HiJob*)p;Shadow*s=j.s;int y0=j.r.y+MulDiv(j.r.h,k,j.bands),y1=j.r.y+MulDiv(j.r.h,k+1,j.bands),ch=j.ch,n=4*ch;
 for(int y=y0;y<y1;y++){const unsigned char*one=s->snapshot.data()+size_t(y)*j.pitch1;unsigned char*h=s->hi.data()+size_t(y)*j.w1;
  for(int x=j.r.x;x<j.r.x+j.r.w;x++){const unsigned char*q=one+size_t(x)*ch;bool apart=false;   // (far is a Windows macro)
   for(int r=0;r<4&&!apart;r++){const unsigned char*d=s->pixels.data()+size_t(y*4+r)*s->b.pitch+size_t(x)*n;for(int i=0;i<n;i++)if(abs(int(d[i])-int(q[i%ch]))>hiT){apart=true;break;}}
   h[x]=apart;}}}
// hi made (all of it the first time) or brought up to date over hiDirty, against the 1x the 4x was made from (the snapshot)
static void HiEnsure(Shadow*s){if(!s)return;int w1=s->b.w/4,h1=s->b.h/4;if(w1<=0||h1<=0||s->snapshot.size()<size_t(h1)*w1*(s->b.format?1:3))return;
 if(s->hi.size()!=size_t(w1)*h1){s->hi.assign(size_t(w1)*h1,0);s->hiDirty.assign(1,{0,0,w1,h1});}
 if(s->blank){s->hiDirty.clear();return;}   // a blank 4x is widened from its 1x before anything reads it (Unblank), which keeps hi 0
 std::vector<Box> boxes;boxes.swap(s->hiDirty);
 for(auto&r:boxes){int x0=std::max(0,r.x),y0=std::max(0,r.y),x1=std::min(w1,r.x+r.w),y1=std::min(h1,r.y+r.h);if(x1<=x0||y1<=y0)continue;
  HiJob j{s,{x0,y0,x1-x0,y1-y0},w1,int(s->snapshot.size()/h1),s->b.format?1:3,std::clamp((y1-y0)*(x1-x0)/20000,1,32)};BandsRun(j.bands,HiBand,&j);hiBuilt+=uint64_t(x1-x0)*(y1-y0);
  if(perf)hiBuiltBy[s]+=uint64_t(x1-x0)*(y1-y0);}}
// A blit onto a page that keeps hi (the screen's is LowResBand's): hi carried through it at 1x by the same rule, instead of
// comparing the box again. A scrolled 연표 restamps its four 675x503 layers whole every step (10-25: 93M pixels compared a run).
// False when the source's hi cannot be had: the box is then compared later (hiDirty).
static uint64_t hiCarried=0,hiCarryTried=0;
static bool HiCarry(char kind,Bitmap*a,const Box&ar,Bitmap*b,const Box&br,Shadow*sa,Shadow*sb,int t){
 // only while the 연표 is up: elsewhere a source would get its hi made for nothing, a stutter in a story scene
 if(!(chronicleOpen||chronicleSeen)||!sa||!sb||(sa==sb&&kind!='C')||Off(OFF_LOWRES))return false;hiCarryTried++;if(sb->hi.empty()||sb->hi.size()!=size_t(b->w)*b->h)return false;
 HiEnsure(sa);if(kind=='M')HiEnsure(sa->maskShadow);int sw=a->w,sh=a->h,dw=b->w,dh=b->h;if(sa->hi.size()!=size_t(sw)*sh)return false;
 const unsigned char*hm0=kind=='M'&&sa->maskShadow&&sa->maskShadow->hi.size()==size_t(sw)*sh?sa->maskShadow->hi.data():nullptr;
 bool masked=kind=='M'&&a->mask&&a->mask!=a&&a->mask->pixels&&a->mask->w==sw&&a->mask->h==sh;if(masked&&!hm0)return false;   // its 4x mask unknown
 const Bitmap*m=masked&&!a->format?a->mask:nullptr;int add=t+1;
 int r0=std::max({0,br.y,br.y-ar.y}),r1=std::min({dh,br.y+ar.h,br.y-ar.y+sh}),c0=std::max({0,br.x,br.x-ar.x}),c1=std::min({dw,br.x+ar.w,br.x-ar.x+sw});
 // a layer scrolled onto itself (the 연표 moves its layers in place): rows in the order that reads each before it is written
 if(kind=='C'){bool up=sa==sb&&br.y>ar.y;for(int i=r0;i<r1;i++){int r=up?r1-1-(i-r0):i;memmove(sb->hi.data()+size_t(r)*dw+c0,sa->hi.data()+size_t(ar.y+(r-br.y))*sw+ar.x+(c0-br.x),size_t(std::max(0,c1-c0)));}hiCarried++;return true;}
 for(int r=r0;r<r1;r++){unsigned char*f=sb->hi.data()+size_t(r)*dw;size_t srow=size_t(ar.y+(r-br.y));const unsigned char*hc=sa->hi.data()+srow*sw,*hm=hm0?hm0+srow*sw:nullptr,*mr=m?m->pixels+srow*m->pitch:nullptr;
  for(int c=c0;c<c1;c++){int sc=ar.x+(c-br.x);unsigned char hs=hc[sc];
   if(kind=='M'&&mr&&!(hm&&hm[sc])){int mm=mr[sc]+add;if(mm<=2)f[c]=hs;else if(mm<255)f[c]|=hs;}else f[c]|=hs|(hm?hm[sc]:0);}}
 hiCarried++;return true;}
static bool LowResOn(Shadow*s){Bitmap*one=*(Bitmap**)0x56a6a8;
 // zoomed in, the present magnifies a part of the same 4x screen; the whole-table view's collection draws at 4x as before
 return (chronicleOpen||chronicleSeen)&&zoomLevel>=1&&!ovCapturing&&!Off(OFF_LOWRES)&&s&&!s->b.format&&Valid(one)&&!one->format&&one->w*4==s->b.w&&one->h*4==s->b.h&&one->w<=2048;}
static void LowResFixAlt(){lowResAltStale=false;auto it=shadows.find(*(Bitmap**)0x56a6a8);if(it==shadows.end())return;Shadow*s=it->second.get();
 if(!s->alternate.empty()&&s->alternate.size()==s->pixels.size())ParallelCopy(s->alternate.data(),s->pixels.data(),s->pixels.size());}
static void FillWide(Shadow*s,const Bitmap*one,int c0,int c1,int r0,int r1){if(c1<=c0)return;size_t span=size_t(c1-c0)*12;
 for(int r=r0;r<r1;r++){unsigned char*d0=s->pixels.data()+size_t(r)*4*s->b.pitch+size_t(c0)*12;Widen(d0,one->pixels+size_t(r)*one->pitch+size_t(c0)*3,c1-c0,3);for(int k=1;k<4;k++)memcpy(d0+size_t(k)*s->b.pitch,d0,span);}}
static void ReplayIn(const Queued&q,Bitmap*d,const Box&R){int x0=std::max(q.y.x,R.x),y0=std::max(q.y.y,R.y),x1=std::min(q.y.x+q.y.w,R.x+R.w),y1=std::min(q.y.y+q.y.h,R.y+R.h);if(x1<=x0||y1<=y0)return;
 Box sx{q.x.x+(x0-q.y.x),q.x.y+(y0-q.y.y),x1-x0,y1-y0},dx{x0,y0,x1-x0,y1-y0};Bitmap a=q.srcB;
 if(q.kind=='C')oldCopy(&a,&sx,d,&dx);else if(q.kind=='A')oldAlpha(&a,&sx,d,&dx,q.t);else if(q.mask1&&!Off(OFF_SPARSE))SparseMask(q,&a,d,sx,dx);else oldMask(&a,&sx,d,&dx,q.t);}
struct LowResJob {Shadow*s;const Bitmap*one;int bands;std::atomic<uint64_t> replay{0},fill{0};};
static void LowResBand(void*p,int k){auto&j=*(LowResJob*)p;Shadow*s=j.s;const Bitmap*one=j.one;int w1=one->w,h1=one->h;int y0=MulDiv(h1,k,j.bands),y1=MulDiv(h1,k+1,j.bands);if(y1<=y0)return;
 unsigned char*F=s->hi.data();
 // only what this queue drew is redone: a settle mid-frame queues a part of the frame (the opened-up 연표 settles often)
 std::vector<unsigned char> T(size_t(y1-y0)*w1,0);
 // 1: the screen's hi through the queue at 1x, on this band's rows
 for(auto&q:queued){if(q.covered||!q.sa||!q.src1)continue;const Bitmap*src=q.src1;int dx=q.y.x/4,dy=q.y.y/4,w=q.y.w/4,h=q.y.h/4,sx=q.x.x/4,sy=q.x.y/4;
  int r0=std::max({y0,dy,dy-sy}),r1=std::min({y1,dy+h,dy-sy+src->h}),c0=std::max({0,dx,dx-sx}),c1=std::min({w1,dx+w,dx-sx+src->w});if(r1<=r0||c1<=c0)continue;
  for(int r=r0;r<r1;r++)memset(T.data()+size_t(r-y0)*w1+c0,1,size_t(c1-c0));
  const auto&hcv=q.sa->hi;bool known=hcv.size()==size_t(src->w)*src->h;const Shadow*ms=q.ma;const unsigned char*hm0=q.kind=='M'&&ms&&ms->hi.size()==size_t(src->w)*src->h?ms->hi.data():nullptr;
  // a masked source whose 4x mask is not known could differ anywhere it reaches: high-res throughout its box
  if(q.kind=='M'&&q.maskLow&&!hm0){for(int r=r0;r<r1;r++)memset(F+size_t(r)*w1+c0,1,size_t(c1-c0));continue;}
  const Bitmap*m=q.kind=='M'&&!src->format?q.maskLow:nullptr;int add=q.t+1;
  for(int r=r0;r<r1;r++){unsigned char*f=F+size_t(r)*w1;size_t srow=size_t(sy+(r-dy));const unsigned char*hc=known?hcv.data()+srow*src->w:nullptr,*hm=hm0?hm0+srow*src->w:nullptr,*mr=m?m->pixels+srow*m->pitch:nullptr;
   for(int c=c0;c<c1;c++){int sc=sx+(c-dx);unsigned char hs=hc?hc[sc]:1;
    if(q.kind=='C')f[c]=hs;
    else if(q.kind=='M'&&mr&&!(hm&&hm[sc])){int mm=mr[sc]+add;if(mm<=2)f[c]=hs;else if(mm<255)f[c]|=hs;}   // m=mask+t+1: <=2 copies, >=255 keeps
    else f[c]|=hs|(hm?hm[sc]:0);}}}
 // 2: per lrRows rows, the columns with any drawn high-res pixel as runs (short gaps run through), drawn at 4x through the
 // whole queue; 3: the other drawn pixels widened from the 1x screen
 Bitmap d=s->b;unsigned char any[2048];uint64_t replay=0,fill=0;
 for(int g=y0;g<y1;){int ge=std::min(y1,g+lrRows);memset(any,0,size_t(w1));
  for(int r=g;r<ge;r++){const unsigned char*f=F+size_t(r)*w1,*t=T.data()+size_t(r-y0)*w1;for(int c=0;c<w1;c++)any[c]|=f[c]&t[c];}
  for(int c=0;c<w1;){if(!any[c]){int e=c;while(e<w1&&!any[e])e++;
    for(int r=g;r<ge;r++){const unsigned char*t=T.data()+size_t(r-y0)*w1;for(int x=c;x<e;){if(!t[x]){x++;continue;}int xe=x;while(xe<e&&t[xe])xe++;FillWide(s,one,x,xe,r,r+1);fill+=uint64_t(xe-x);x=xe;}}
    c=e;continue;}
   int last=c;for(int k2=c+1;k2<w1&&k2-last<=lrGap;k2++)if(any[k2])last=k2;Box R{c*4,g*4,(last+1-c)*4,(ge-g)*4};for(auto&q:queued)if(!q.covered)ReplayIn(q,&d,R);replay+=uint64_t(last+1-c)*(ge-g);c=last+1;}
  g=ge;}
 j.replay+=replay;j.fill+=fill;}
static void LowResFrame(Shadow*s){int w1=s->b.w/4,h1=s->b.h/4;
 // the screen's hi: unknown (all high-res) until this mode has drawn it; whatever else changed it since counts as high-res
 if(s->hi.size()!=size_t(w1)*h1){s->hi.assign(size_t(w1)*h1,1);s->hiDirty.clear();}
 else{for(auto&r:s->hiDirty){int x0=std::max(0,r.x),y0=std::max(0,r.y),x1=std::min(w1,r.x+r.w),y1=std::min(h1,r.y+r.h);for(int y=y0;y<y1&&x1>x0;y++)memset(s->hi.data()+size_t(y)*w1+x0,1,size_t(x1-x0));}s->hiDirty.clear();}
 for(auto&q:queued)if(q.sa&&!q.covered){HiEnsure(q.sa);if(q.kind=='M')HiEnsure(q.ma);}
 LowResJob j{s,*(Bitmap**)0x56a6a8,bandPool.workers?std::min(48,(bandPool.workers+1)*4):1};BandsRun(j.bands,LowResBand,&j);lrFrames++;lrReplay+=j.replay;lrFill+=j.fill;
 if(!s->alternate.empty())lowResAltStale=true;}
static void Execute(){if(queued.empty())return;Shadow*s=queueScreen;LONGLONG t0=Now();bool low=LowResOn(s);
 if(!low){if(lowResAltStale)LowResFixAlt();s->hi.clear();s->hiDirty.clear();}   // the screen's hi is kept by the low-res mode alone
 bool hasAlt=!low&&!s->alternate.empty();Bitmap altDst{};if(hasAlt)altDst=AltBitmap(s);
 std::vector<unsigned char> ref,refAlt;if(deferVerify){try{ref=s->pixels;if(hasAlt)refAlt=s->alternate;Bitmap scratch=s->b,scratchAlt=altDst;scratch.pixels=ref.data();if(hasAlt)scratchAlt.pixels=refAlt.data();
  for(auto&q:queued)RunOne(q,&scratch,hasAlt?&scratchAlt:nullptr);}catch(const std::bad_alloc&){ref.clear();refAlt.clear();}}
 MarkCovered();if(!bandPool.started)bandPool.Start();
 if(low)LowResFrame(s);
 else{FrameJob job{s->b,altDst,hasAlt,bandPool.workers?std::min(48,(bandPool.workers+1)*4):1};   // ~4 bands a thread keeps them even (24/48/96 measured: 48 best)
  if(job.bands<2||queued.size()<8){for(auto&q:queued)if(!q.covered)RunOne(q,&s->b,hasAlt?&altDst:nullptr);}else bandPool.Run(job.bands,BandFrame,&job);}
 if(deferVerify&&!ref.empty()&&low){const unsigned char*a=s->pixels.data(),*b=ref.data();uint64_t n=0,over=0;int worst=0;size_t worstAt=0;   // the low-res frame against the 4x one
  for(size_t i=0;i<ref.size();i++){int v=abs(int(a[i])-int(b[i]));if(v){n++;over+=v>hiT;if(v>worst){worst=v;worstAt=i;}}}lrDiff+=n;lrOver+=over;lrWorst=std::max(lrWorst,worst);lrChecked+=ref.size();
  // the first few frames that miss by more than hiT: where, and what the queue drew there (1x screen pixel)
  static int told=0;if(worst>hiT+8&&told<6&&logFile){told++;int px=int((worstAt%size_t(s->b.pitch))/3)/4,py=int(worstAt/size_t(s->b.pitch))/4;
   fprintf(logFile,"lowres_miss frame=%llu worst=%d at=%d,%d hi=%d ops=%zu:",(unsigned long long)dFrames,worst,px,py,s->hi.empty()?-1:s->hi[size_t(py)*(s->b.w/4)+px],queued.size());
   for(auto&q:queued){int dx=q.y.x/4,dy=q.y.y/4;if(px<dx||py<dy||px>=dx+q.y.w/4||py>=dy+q.y.h/4||!q.src1)continue;int sx=q.x.x/4+(px-dx),sy=q.x.y/4+(py-dy);auto an=assets.find(const_cast<Bitmap*>(q.src1));
    int hc=q.sa&&q.sa->hi.size()==size_t(q.src1->w)*q.src1->h?q.sa->hi[size_t(sy)*q.src1->w+sx]:-1,mk=q.maskLow?q.maskLow->pixels[size_t(sy)*q.maskLow->pitch+sx]:-1;
    fprintf(logFile," [%c%s src=%p %dx%d at=%d,%d hi=%d mask=%d t=%d %s]",q.kind,q.covered?"(covered)":"",(void*)q.src1,q.src1->w,q.src1->h,sx,sy,hc,mk,q.t,an!=assets.end()?an->second.name.c_str():"");}
   fprintf(logFile,"\n");fflush(logFile);}}
 else if(deferVerify&&!ref.empty()&&(ref!=s->pixels||(hasAlt&&refAlt!=s->alternate))){dMismatch++;memcpy(s->pixels.data(),ref.data(),ref.size());if(hasAlt&&!refAlt.empty())memcpy(s->alternate.data(),refAlt.data(),refAlt.size());
  if(logFile){fprintf(logFile,"defer_mismatch frame=%llu ops=%zu\n",(unsigned long long)dFrames,queued.size());fflush(logFile);}}
 dOps+=queued.size();pCompose+=Ms(t0);queued.clear();queuedRefs.clear();}
static void SettleAll(){if(queued.empty())return;Execute();dSettles++;}
static void SettleFor(Shadow*s){if(s&&!queued.empty()&&(s==queueScreen||queuedRefs.count(s)))SettleAll();}
static bool Defer(char kind,Bitmap*a,Bitmap*b,Shadow*sa,Shadow*sb,const Box&x,const Box&y,int t){Bitmap*screen=*(Bitmap**)0x56a6a8;
 if(b==screen){screenDrawn=true;if(!chronicleSeen&&IsChronicleArt(a)){chronicleSeen=true;lowResKeep=!Off(OFF_LOWRES);}}
 bool alt=!sa->alternate.empty()||!sb->alternate.empty();
 bool ok=deferOn&&b==screen&&a!=b&&sa!=sb&&!sb->b.mask&&!sb->b.format&&(!alt||!sb->alternate.empty())&&(queued.empty()||queueScreen==sb);
 if(!ok){SettleAll();if(lowResAltStale&&a==screen)LowResFixAlt();return false;}   // a blit that reads the screen reads both copies
 if(queued.empty())queueScreen=sb;queued.push_back({kind,sa->b,alt?AltBitmap(sa):sa->b,x,y,t,alt});auto&nq=queued.back();nq.src1=a;nq.sa=sa;nq.ma=kind=='M'?sa->maskShadow:nullptr;
 if(a->mask&&a->mask!=a&&a->mask->pixels&&a->mask->w==a->w&&a->mask->h==a->h)nq.maskLow=a->mask;queuedRefs.insert(sa);if(sa->maskShadow)queuedRefs.insert(sa->maskShadow);
 if(kind=='M'&&!a->format&&a->mask&&a->mask->format&&a->mask->w==a->w&&a->mask->h==a->h&&a->mask->pixels&&sa->maskShadow)queued.back().mask1=a->mask;
 return true;}
// 연표 원래 화면: a 연표 frame's queued 4x blits are not drawn. Where they would have drawn, the screen's 4x becomes its 1x
// widened, so the 4x stays a true (low-res) copy for whatever reads it next: F8 back to 4K, closing the 연표 (that frame
// draws without the 연표 frame and is drawn in full), a capture. Its pages keep their 4x blits as ever.
static void OriginalDrop(){if(queued.empty())return;Shadow*s=queueScreen;Bitmap*b=*(Bitmap**)0x56a6a8;int x0=INT_MAX,y0=INT_MAX,x1=0,y1=0;
 for(auto&q:queued){x0=std::min(x0,q.y.x/4);y0=std::min(y0,q.y.y/4);x1=std::max(x1,(q.y.x+q.y.w+3)/4);y1=std::max(y1,(q.y.y+q.y.h+3)/4);}
 queued.clear();queuedRefs.clear();oDrops++;   // cleared first: Nearest settles a queue that writes s
 auto it=Valid(b)?shadows.find(b):shadows.end();if(it!=shadows.end()&&it->second.get()==s&&x1>x0&&y1>y0)Nearest(s,b,{x0,y0,x1-x0,y1-y0},false);}
// While the new 연표 covers the game's (cproto::Covered), its frames are dropped like the original picture's, but the part
// they touched is only noted, and caught up from the 1x screen once when the cover goes (no 4x work per frame meanwhile).
static int cvX0=INT_MAX,cvY0=INT_MAX,cvX1=0,cvY1=0;static bool cvPending=false;
static void CoveredDrop(){if(queued.empty())return;for(auto&q:queued){cvX0=std::min(cvX0,q.y.x/4);cvY0=std::min(cvY0,q.y.y/4);cvX1=std::max(cvX1,(q.y.x+q.y.w+3)/4);cvY1=std::max(cvY1,(q.y.y+q.y.h+3)/4);}
 queued.clear();queuedRefs.clear();cvPending=true;}
static void CoveredCatchUp(){if(!cvPending)return;cvPending=false;Shadow*s=queueScreen;Bitmap*b=*(Bitmap**)0x56a6a8;auto it=Valid(b)?shadows.find(b):shadows.end();
 if(it!=shadows.end()&&it->second.get()==s&&cvX1>cvX0&&cvY1>cvY0)Nearest(s,b,{cvX0,cvY0,cvX1-cvX0,cvY1-cvY0},false);cvX0=cvY0=INT_MAX;cvX1=cvY1=0;}
// At the start of each present: draw what this frame queued, then batch the next frame only if this one drew the chronicle.
static void FinishFrame(){
 if(!deferChecked){deferChecked=true;wchar_t f[MAX_PATH];swprintf_s(f,L"%s\\storymap-defer.off",root);deferOff=GetFileAttributesW(f)!=INVALID_FILE_ATTRIBUTES;deferVerify=GetEnvironmentVariableW(L"RECON_DEFER_VERIFY",nullptr,0)>0;
  wchar_t v[16]{};if(GetEnvironmentVariableW(L"RECON_HI_T",v,16))hiT=std::clamp(_wtoi(v),0,255);
  if(GetEnvironmentVariableW(L"RECON_LOWRES_ROWS",v,16))lrRows=std::clamp(_wtoi(v),1,64);if(GetEnvironmentVariableW(L"RECON_LOWRES_GAP",v,16))lrGap=std::clamp(_wtoi(v),1,64);}
 if(dumpLayers&&queued.size()>=100){dumpLayers=false;DumpLayers();}   // a whole frame's queue, not a settle's part
 if(cproto::Covered()&&!ovCapturing)CoveredDrop();else{CoveredCatchUp();if(chronicleOriginal&&chronicleSeen&&!ovCapturing)OriginalDrop();else Execute();}dFrames++;bool on=!deferOff&&!Off(OFF_DEFER);chronicleShown=chronicleSeen;
 // chronicleOpen (arrows, zoom): a present with nothing newly drawn (a repaint) keeps it; a drawn page without the frame closes it
 bool wasOpen=chronicleOpen;if(chronicleSeen)chronicleOpen=true;else if(screenDrawn&&chronicleOpen){chronicleOpen=false;zoomLevel=1;zoomX=zoomY=0;zoomRest=0;OverviewFree();}
 if(wasOpen!=chronicleOpen&&logFile){fprintf(logFile,"chronicle_open=%d frame=%llu\n",chronicleOpen,(unsigned long long)dFrames);fflush(logFile);}
 if(wasOpen&&!chronicleOpen&&lowResAltStale)LowResFixAlt();
 lastFrameDrew=screenDrawn;screenDrawn=false;chronicleSeen=false;
 if(on!=deferOn&&logFile){fprintf(logFile,"defer_%s frame=%llu\n",on?"on":"off",(unsigned long long)dFrames);fflush(logFile);}deferOn=on;lowResKeep=chronicleOpen&&!Off(OFF_LOWRES);
 if((perf||deferVerify)&&logFile&&dFrames%60==0){fprintf(logFile,"defer frames=%llu ops=%llu settles=%llu mismatched=%llu covered=%llu on=%d mask_px=%llu mask_skipped_pct=%.1f\n",(unsigned long long)dFrames,(unsigned long long)dOps,(unsigned long long)dSettles,(unsigned long long)dMismatch,(unsigned long long)dCovered,deferOn,
  (unsigned long long)dSparseTotal.load(),dSparseTotal.load()?100.0*double(dSparseSkipped.load())/double(dSparseTotal.load()):0.0);
  if(lrFrames)fprintf(logFile,"lowres frames=%llu shadows_made=%llu carried=%llu/%llu hi_t=%d replay_pct=%.1f hi_built=%llu diff_pct=%.3f over_t_pct=%.4f worst=%d\n",(unsigned long long)lrFrames,(unsigned long long)hShadows,
   (unsigned long long)hiCarried,(unsigned long long)hiCarryTried,hiT,lrReplay+lrFill?100.0*double(lrReplay)/double(lrReplay+lrFill):0.0,(unsigned long long)hiBuilt,
   lrChecked?100.0*double(lrDiff)/double(lrChecked):0.0,lrChecked?100.0*double(lrOver)/double(lrChecked):0.0,lrWorst);
  if(oDrops)fprintf(logFile,"original drops=%llu presents=%llu present_ms=%.3f on=%d\n",(unsigned long long)oDrops,(unsigned long long)oPresents,oPresents?oPresentMs/double(oPresents):0.0,chronicleOriginal);
  if(lrFrames&&!hiBuiltBy.empty()){std::vector<std::pair<uint64_t,const Shadow*>> top;for(auto&h:hiBuiltBy)top.push_back({h.second,h.first});std::sort(top.rbegin(),top.rend());
   fprintf(logFile,"hi_built_by");for(size_t i=0;i<top.size()&&i<5;i++){const Bitmap*b1=nullptr;for(auto&sh:shadows)if(sh.second.get()==top[i].second){b1=sh.first;break;}auto a=b1?assets.find(const_cast<Bitmap*>(b1)):assets.end();
    fprintf(logFile," %llu:%dx%d:%s:%s",(unsigned long long)top[i].first,top[i].second->b.w/4,top[i].second->b.h/4,b1==*(Bitmap**)0x56a6a8?"screen":"",a!=assets.end()?a->second.name.c_str():"");}fprintf(logFile,"\n");}
  fflush(logFile);}}
