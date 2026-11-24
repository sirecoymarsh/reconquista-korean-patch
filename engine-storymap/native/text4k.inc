// ------------------------------------------------------------------------------------------------ 4x text
// The engine draws text (dialogue, 연표, ...) with GDI in 0x413ab0: each new glyph is TextOutA'd at four times its size into
// an 8-bit DIB ([0x4e95e0]; 0xff = clear), averaged down to 1x at the pen position of the line bitmap ([0x4e85ac]) by a
// 20-tap 4x4 kernel (centre 2x2 counted twice), and, for fonts that use it, kept in the engine's glyph cache (0x4146e0;
// the 연표 font does not); a glyph already cached is copied into the line bitmap (0x4147e0). New glyphs are caught right
// after the average (0x4141d8). The finished line is laid on the page with a colour (0x440840 -> 0x448570,
// the Mask formula with a solid colour; shadow styles lay it several times, offset). The HD layer used to see only the
// result and widen it pixel by pixel. Here every 4x glyph is kept when the engine's own kernel turns it back into exactly
// the engine's 1x glyph (else that glyph stays widened, as before), laid at four times the engine's pen positions in a 4x
// line, and laid on the page's 4x shadow (and its other-quality copy and mask) with the same formula. 4x text only runs
// on the engine's 4x path (0x4146b0 true, the default font smoothing).
struct Glyph4 {int w=0,h=0;std::vector<unsigned char> px;};
static std::unordered_map<uint64_t,Glyph4> glyphs4;static size_t glyphBytes=0;
static uint64_t renderFails=0,placeMisses=0;   // the two ways a glyph ends up widened (perf: the first 30 of each are logged)
static uint64_t store1xSkipped=0,lines1x=0;    // GlyphStore below; lines the engine drew on its 1x path
// Diagnostics (perf): new 4x glyphs GlyphRendered let go before keeping them, by reason (0 not active, 1 bitmaps, 2 pen,
// 3 size), text lines entered while nested or inside another text line, and 4x glyphs the engine cached with no 4x copy here.
static uint64_t glyphEarly[4]{},linesNested=0,linesInner=0,storeUnknown=0;static int textDepth=0,lastEarlyCode=-1,lastEarlyWhy=-1;
static std::vector<unsigned char> line4;static int line4w=0,line4h=0;static bool textActive=false,line4Ready=false;static void* textStyle=nullptr;
static uint64_t textStats[4]{};   // glyphs kept, glyphs widened, lines laid in 4x, lines left to the 1x path
static Bitmap* LineBitmap(){return *(Bitmap**)0x4e85ac;}
static Bitmap* GlyphDib(){return *(Bitmap**)0x4e95e0;}
// The 4x glyph depends on the font in the engine's DC and on the style's thickening passes (+0x24).
static uint32_t TextFontKey(){HDC dc=*(HDC*)0x4e95dc;LOGFONTA lf{};HGDIOBJ f=dc?GetCurrentObject(dc,OBJ_FONT):nullptr;if(!f||!GetObjectA(f,sizeof lf,&lf))return 0;
 uint32_t h=2166136261u;auto p=(const unsigned char*)&lf;for(size_t i=0;i<sizeof lf;i++){h^=p[i];h*=16777619u;}if(textStyle&&*(int*)((char*)textStyle+0x24))h^=0x9e3779b9u;return h;}
static void Line4Begin(){Bitmap*l=LineBitmap();if(!l||l->w<=0||l->h<=0)return;if(!line4Ready||line4w!=l->w*4||line4h!=l->h*4){line4w=l->w*4;line4h=l->h*4;}line4.assign(size_t(line4w)*line4h,0xff);line4Ready=true;}
static void Line4Put(int x,int y,int w,int h,const unsigned char* src,int pitch){   // 4x coverage rows into the 4x line
 for(int r=0;r<h;r++){int yy=y+r;if(yy<0||yy>=line4h)continue;int x0=std::max(x,0),x1=std::min(x+w,line4w);if(x1>x0)memcpy(line4.data()+size_t(yy)*line4w+x0,src+size_t(r)*pitch+(x0-x),size_t(x1-x0));}}
static void Line4Widen(int x,int y,int w,int h){Bitmap*l=LineBitmap();   // the 1x glyph at (x,y) of the line bitmap, pixel by pixel
 for(int r=0;r<h;r++){if(y+r<0||y+r>=l->h)continue;auto s=l->pixels+size_t(y+r)*l->pitch;for(int yy=0;yy<4;yy++){int ry=(y+r)*4+yy;for(int c=0;c<w;c++){int x4=(x+c)*4;if(x+c<0||x+c>=l->w)continue;memset(line4.data()+size_t(ry)*line4w+x4,s[x+c],4);}}}}
// The engine's kernel: one 1x pixel from the 4x4 cell at (bx,by).
static int Kernel(const unsigned char* p,int pitch,int bx,int by){auto q=[&](int x,int y){return int(p[size_t(by+y)*pitch+bx+x]);};
 int s=2*(q(1,1)+q(2,1)+q(1,2)+q(2,2))+q(0,0)+q(1,0)+q(2,0)+q(3,0)+q(0,3)+q(1,3)+q(2,3)+q(3,3)+q(0,1)+q(3,1)+q(0,2)+q(3,2);return s/20;}
using TextLineFn=int(__cdecl*)(void*,void*,void*,void*,void*,void*,void*,void*);static TextLineFn oldTextLine;
static int __cdecl TextLine(void*a,void*b,void*c,void*d,void*e,void*f,void*g,void*h){   // 0x413ab0 takes 5; the rest are the caller's
 static const bool force1x=GetEnvironmentVariableW(L"RECON_TEXT_1X",nullptr,0)>0;if(force1x)*(int*)0x47af3c=0;   // tests: the engine's 1x path, as while skipping
 bool scale4=((int(__cdecl*)())0x4146b0)()!=0;textActive=scale4&&!nesting;textStyle=a;line4Ready=false;if(!scale4&&!nesting)lines1x++;
 if(nesting)linesNested++;if(textDepth)linesInner++;textDepth++;
 int r=oldTextLine(a,b,c,d,e,f,g,h);textDepth--;textActive=false;return r;}
// Right after 0x413ab0's 4x path has averaged a new glyph into the line bitmap (0x4141d8, before it decides whether this
// font uses the glyph cache: the 연표 font does not): its frame holds the pen x (+0x10), the width written (+0x44) and the
// code (+0x8c); the 4x DIB still holds the glyph.
static void __stdcall GlyphRendered(unsigned char* frame){
 Bitmap*l=LineBitmap(),*d=GlyphDib();int code=*(int*)(frame+0x8c);
 auto early=[&](int why){glyphEarly[why]++;lastEarlyCode=code;lastEarlyWhy=why;
  if(perf&&logFile&&glyphEarly[0]+glyphEarly[1]+glyphEarly[2]+glyphEarly[3]<=30){fprintf(logFile,"text4k glyph_early code=%04x why=%d nesting=%d depth=%d l=%dx%d/%d d=%dx%d/%d pen=%d width=%d\n",code,why,nesting,textDepth,l?l->w:-1,l?l->h:-1,l?l->format:-1,d?d->w:-1,d?d->h:-1,d?d->format:-1,*(int*)(frame+0x10),*(int*)(frame+0x44));fflush(logFile);}};
 if(!textActive){early(0);return;}if(!l||!d||!l->pixels||!d->pixels||!d->format||!l->format){early(1);return;}   // both 8-bit
 int x=*(int*)(frame+0x10),width=*(int*)(frame+0x44),y=0;if(width<=0||x<0||x>=l->w){early(2);return;}
 if(!line4Ready)Line4Begin();int h=l->h,w=std::min(width,l->w-x);if(textStyle)h=std::min(h,*(int*)((char*)textStyle+0x28));if(h<=0||w<=0){early(3);return;}
 // The glyph is TextOutA'd centred at 4*advance+1 and averaged from column 2*advance: try that first, then look around.
 auto matches=[&](int c0){if(c0<0||c0+4*w>d->w||4*h>d->h)return false;for(int r=0;r<h;r++)for(int i=0;i<w;i++)if(Kernel(d->pixels,d->pitch,c0+4*i,4*r)!=l->pixels[size_t(y+r)*l->pitch+x+i])return false;return true;};
 int found=matches(2*width)?2*width:-1;for(int c0=0;found<0&&c0<=192;c0++)if(c0!=2*width&&matches(c0))found=c0;
 if(perf&&logFile&&textStats[0]+textStats[1]<40){fprintf(logFile,"text4k glyph code=%04x w=%d h=%d at=%d,%d dib=%dx%d column=%d\n",code,w,h,x,y,d->w,d->h,found);fflush(logFile);}
 if(found<0){textStats[1]++;renderFails++;
  if(perf&&logFile&&renderFails<=30){int best=1<<30,bestc=-1;for(int c0=0;c0<=192;c0++){if(c0+4*w>d->w||4*h>d->h)break;int bad=0;for(int r=0;r<h;r++)for(int i=0;i<w;i++)bad+=Kernel(d->pixels,d->pitch,c0+4*i,4*r)!=l->pixels[size_t(y+r)*l->pitch+x+i];if(bad<best){best=bad;bestc=c0;}}
   fprintf(logFile,"text4k render_miss code=%04x w=%d h=%d x=%d nearest_column=%d pixels_off=%d of %d\n",code,w,h,x,bestc,best,w*h);fflush(logFile);}
  Line4Widen(x,y,w,h);return;}
 Glyph4 g4;g4.w=4*w;g4.h=4*h;g4.px.resize(size_t(g4.w)*g4.h);for(int r=0;r<g4.h;r++)memcpy(g4.px.data()+size_t(r)*g4.w,d->pixels+size_t(r)*d->pitch+found,size_t(g4.w));
 Line4Put(4*x,4*y,g4.w,g4.h,g4.px.data(),g4.w);textStats[0]++;
 uint64_t key=(uint64_t(TextFontKey())<<32)|uint32_t(code);if(glyphBytes>(64u<<20)){glyphs4.clear();glyphBytes=0;}
 if(perf&&logFile){static std::unordered_map<uint32_t,int> seenKeys;if(seenKeys.emplace(uint32_t(key>>32),0).second){HDC dc=*(HDC*)0x4e95dc;LOGFONTA lf{};HGDIOBJ f=dc?GetCurrentObject(dc,OBJ_FONT):nullptr;if(f)GetObjectA(f,sizeof lf,&lf);
  fprintf(logFile,"text4k font_key key=%08x h=%ld w=%ld weight=%ld q=%d cs=%d face=%s style=%p thick=%d rows=%d first_code=%04x\n",unsigned(key>>32),lf.lfHeight,lf.lfWidth,lf.lfWeight,lf.lfQuality,lf.lfCharSet,lf.lfFaceName,textStyle,textStyle?*(int*)((char*)textStyle+0x24):-1,textStyle?*(int*)((char*)textStyle+0x28):-1,code);fflush(logFile);}}
 if(auto old=glyphs4.find(key);old!=glyphs4.end())glyphBytes-=old->second.px.size();glyphBytes+=g4.px.size();glyphs4[key]=std::move(g4);}
static void* glyphDoneBack=nullptr;   // trampoline: the displaced mov eax,[esp+5c] / test eax,eax, then back to 0x4141de
__declspec(naked) static void GlyphDoneStub(){__asm{
 pushad
 pushfd
 lea eax,[esp+36]
 push eax
 call GlyphRendered
 popfd
 popad
 jmp dword ptr [glyphDoneBack]}}
using GlyphPlaceFn=void(__cdecl*)(int,unsigned char*,int);static GlyphPlaceFn oldGlyphPlace;
static void __cdecl GlyphPlace(int code,unsigned char* dst,int pitch){
 oldGlyphPlace(code,dst,pitch);
 Bitmap*l=LineBitmap();if(!textActive||!l||!l->pixels)return;if(!line4Ready)Line4Begin();ptrdiff_t off=dst-l->pixels;if(off<0||off>=ptrdiff_t(l->pitch)*l->h)return;
 int x=int(off%l->pitch),y=int(off/l->pitch);auto it=glyphs4.find((uint64_t(TextFontKey())<<32)|uint32_t(code));
 if(it!=glyphs4.end()){Line4Put(4*x,4*y,it->second.w,it->second.h,it->second.px.data(),it->second.w);return;}
 int w=*(unsigned char*)(0x49859c+(code&0xffff));
 // A miss is a glyph the engine first drew in a 1x line (0x413ab0 takes the 1x branch when 0x4146b0 is false: its TextOutA
 // and row copy at 0x413d06..0x413dd4 never reach 0x4141d8) and cached there. All 275 widened glyphs of a long reading
 // run were such (render_misses=0; mostly 「 」 … ・, codes 8175 8176 8163 8145). Its cache entry, the pool offset at
 // [0x4a859c+code*4] (0 reads as not cached; the width byte stays for layout), is cleared, so the next time a 4x line
 // meets it the engine draws it on its 4x path and the 4x glyph is kept. Only this placement stays widened.
 *(uint32_t*)(0x4a859cu+uint32_t(code&0xffff)*4)=0;textStats[1]++;placeMisses++;
 if(perf&&logFile&&placeMisses<=30){fprintf(logFile,"text4k place_miss code=%04x w=%d at=%d,%d\n",code,w,x,y);
  HDC dc=*(HDC*)0x4e95dc;LOGFONTA lf{};HGDIOBJ f=dc?GetCurrentObject(dc,OBJ_FONT):nullptr;if(f)GetObjectA(f,sizeof lf,&lf);
  fprintf(logFile,"text4k place_miss_font key=%08x h=%ld w=%ld weight=%ld q=%d cs=%d face=%s style=%p thick=%d rows=%d\n",TextFontKey(),lf.lfHeight,lf.lfWidth,lf.lfWeight,lf.lfQuality,lf.lfCharSet,lf.lfFaceName,textStyle,textStyle?*(int*)((char*)textStyle+0x24):-1,textStyle?*(int*)((char*)textStyle+0x28):-1);
  for(auto& [k,g]:glyphs4)if(uint32_t(k)==uint32_t(code))fprintf(logFile,"text4k place_miss_have key=%08x %dx%d\n",unsigned(k>>32),g.w,g.h);fflush(logFile);}
 Line4Widen(x,y,std::min(w,l->w-x),l->h-y);}
// Where those 1x glyphs come from: the engine's 'auto' smoothing ([0x47af3c]=2) turns the 4x path off while skipping
// (0x40b110), and the 1x branch stores its plain 1x glyphs in the same cache (the call at 0x413e30). One skip left 「 」 … ・
// as 1x glyphs that the next 4x line copied. The 1x branch's store is skipped (it returns nothing; its caller only pops
// the four arguments): such a glyph is TextOutA'd afresh at 1x each time (layout measures it as for any new glyph), and
// only the 4x path fills the cache. 1x lines themselves are drawn as before; their count is lines_1x.
// The cache also outlives the run, in savedata\fc_<face>_<w>x<h>.fcd (0x47af70). The font command (0x412e00) saves the
// cache it leaves (fopen at 0x412e72; the close at 0x412c50 saves at 0x412cb5) and loads the new font's file (0x412f69);
// two script commands (0x427be0, 0x428380) build a file from a character list (0x47d6c4) with their own renderer when none
// exists (existence check 0x427ca1/0x428441, write 0x427ddf/0x42857f). Glyphs from such a file were never drawn in front of
// this layer, so they have no 4x copy: the play copy's dialogue font file held 2,642 from Codex's 10-23 runs and the user's,
// and as the font had changed since, three of them were other characters (爬 睫 緘 where 떠 차 애 are now) and 「 」 … ・
// had old widths. All were widened wherever the engine took them from the cache; the test copy's file gave the 14 place
// misses of a long reading run (render_misses, early returns and unknown stores all 0). So the font command loads only a
// file its own saves wrote in this run; any other gives NULL, and the engine starts that font's cache empty as on a first
// run (0x412fd0), drawing each glyph afresh on its 4x path. The builders keep their real existence check, so an existing
// file is not rebuilt at every start. The files are left as they are.
static std::unordered_set<std::string> fcdWritten;static uint64_t fcdSkipped=0,fcdLoaded=0,fcdBuilt=0;
static bool GlyphCacheOpen(const std::string& path,const char* mode,void* caller){
 size_t n=path.size();if(!mode||n<4||_stricmp(path.c_str()+n-4,".fcd"))return true;
 std::string key=path;for(auto& ch:key)if(ch>='A'&&ch<='Z')ch=char(ch-'A'+'a');
 uintptr_t at=uintptr_t(caller);
 if(at==0x412e77||at==0x412cba){fcdWritten.insert(key);return true;}   // the cache's own saves
 if(at==0x427de4||at==0x428584){fcdBuilt++;if(logFile){fprintf(logFile,"text4k fcd_built path=%s\n",path.c_str());fflush(logFile);}return true;}
 if(at!=0x412f6e)return true;                                         // the builders' existence checks, anything else
 if(fcdWritten.count(key)){fcdLoaded++;return true;}
 fcdSkipped++;if(logFile){fprintf(logFile,"text4k fcd_skip path=%s\n",path.c_str());fflush(logFile);}return false;}
using GlyphStoreFn=void(__cdecl*)(int,int,const unsigned char*,int);static GlyphStoreFn oldGlyphStore;
static void __cdecl GlyphStore(int code,int width,const unsigned char* src,int pitch){
 if(_ReturnAddress()==(void*)0x413e35){store1xSkipped++;return;}
 if(perf&&_ReturnAddress()==(void*)0x414230&&!glyphs4.count((uint64_t(TextFontKey())<<32)|uint32_t(code))){storeUnknown++;
  if(logFile&&storeUnknown<=30){fprintf(logFile,"text4k store_unknown code=%04x width=%d active=%d nesting=%d depth=%d last_early=%04x/%d font=%08x style=%p\n",code,width,int(textActive),nesting,textDepth,lastEarlyCode,lastEarlyWhy,TextFontKey(),textStyle);fflush(logFile);}}
 oldGlyphStore(code,width,src,pitch);}
// One 4x row: dst = (dst*m + colour*(257-m))>>8, m = coverage+1; m>=255 keeps dst, m<=2 is the colour (0x448570).
static void Blend4(unsigned char* d,const unsigned char* cov,int n,uint32_t color){int B=(color>>16)&255,G=(color>>8)&255,R=color&255;
 for(int i=0;i<n;i++,d+=3){int m=cov[i]+1;if(m>=255)continue;if(m<=2){d[0]=(unsigned char)B;d[1]=(unsigned char)G;d[2]=(unsigned char)R;continue;}int k=257-m;
  d[0]=(unsigned char)((d[0]*m+B*k)>>8);d[1]=(unsigned char)((d[1]*m+G*k)>>8);d[2]=(unsigned char)((d[2]*m+R*k)>>8);}}
using LineBlendFn=void(__cdecl*)(Bitmap*,Box*,Bitmap*,POINT*,uint32_t);static LineBlendFn oldLineBlend;
static void __cdecl LineBlend(Bitmap* src,Box* rect,Bitmap* dst,POINT* at,uint32_t color){
 bool mine=textActive&&line4Ready&&src==LineBitmap()&&rect&&at&&Valid(dst)&&!dst->format&&!nesting&&flowWarmStage!=2;Shadow*s=nullptr; Box box{at?at->x:0,at?at->y:0,rect?rect->w:0,rect?rect->h:0};
 if(mine){nesting++;try{s=Get(dst,box,true,true);}catch(const std::bad_alloc&){s=nullptr;}nesting--;if(s)SettleFor(s);}   // the page's 4x as it was before this layer
 oldLineBlend(src,rect,dst,at,color);
 if(!mine||!s){if(mine)textStats[3]++;return;}
 int sx=rect->x*4,sy=rect->y*4,w=rect->w*4,h=rect->h*4,dx=at->x*4,dy=at->y*4;
 int x0=std::max({0,-dx,-sx}),y0=std::max({0,-dy,-sy}),x1=std::min({w,s->b.w-dx,line4w-sx}),y1=std::min({h,s->b.h-dy,line4h-sy});
 for(int r=y0;r<y1;r++){auto cov=line4.data()+size_t(sy+r)*line4w+sx+x0;size_t at3=size_t(dy+r)*s->b.pitch+size_t(dx+x0)*3;
  Blend4(s->pixels.data()+at3,cov,x1-x0,color);if(!s->alternate.empty())Blend4(s->alternate.data()+at3,cov,x1-x0,color);
  if(auto m=s->maskShadow){size_t at1=size_t(dy+r)*m->b.pitch+size_t(dx+x0);for(int i=0;i<x1-x0;i++){m->pixels[at1+i]=(unsigned char)(((cov[i]+1)*m->pixels[at1+i])>>8);if(!m->alternate.empty())m->alternate[at1+i]=(unsigned char)(((cov[i]+1)*m->alternate[at1+i])>>8);}}}
 Snapshot(s,dst,box);if(s->maskShadow&&dst->mask)Snapshot(s->maskShadow,dst->mask,box);textStats[2]++;hTexts++;
 if(perf&&logFile&&textStats[2]%50==1){fprintf(logFile,"text4k lines=%llu glyphs_kept=%llu glyphs_widened=%llu left_1x=%llu cache=%zu render_misses=%llu place_misses=%llu lines_1x=%llu store_1x_skipped=%llu early=%llu/%llu/%llu/%llu nested=%llu inner=%llu store_unknown=%llu fcd_skipped=%llu fcd_loaded=%llu fcd_built=%llu\n",(unsigned long long)textStats[2],(unsigned long long)textStats[0],(unsigned long long)textStats[1],(unsigned long long)textStats[3],glyphs4.size(),(unsigned long long)renderFails,(unsigned long long)placeMisses,(unsigned long long)lines1x,(unsigned long long)store1xSkipped,
  (unsigned long long)glyphEarly[0],(unsigned long long)glyphEarly[1],(unsigned long long)glyphEarly[2],(unsigned long long)glyphEarly[3],(unsigned long long)linesNested,(unsigned long long)linesInner,(unsigned long long)storeUnknown,(unsigned long long)fcdSkipped,(unsigned long long)fcdLoaded,(unsigned long long)fcdBuilt);fflush(logFile);}}
