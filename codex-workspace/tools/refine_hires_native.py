from pathlib import Path
p=Path('candidates/hires-v1/native/ReconquistaHD.cpp');s=p.read_text('utf-8-sig')
s=s.replace('#include <cmath>','#include <cmath>\n#include <new>')
s=s.replace('static std::unordered_set<uint32_t> missing;', 'static std::unordered_set<uint32_t> missing;\nstruct AssetTag {std::string name;uint64_t hash;}; static std::unordered_map<Bitmap*,AssetTag> assets;\nstatic uint64_t Fingerprint(Bitmap*b){uint64_t h=1469598103934665603ull;for(int y=0;y<b->h;y++)for(int x=0;x<b->w*(b->format?1:3);x++){h^=b->pixels[y*b->pitch+x];h*=1099511628211ull;}return h;}\nstatic void LoadHD(Bitmap*,const char*);')
s=s.replace('Shadow* s=nullptr;','Shadow* s=nullptr;bool created=false;')
s=s.replace('used+=n+s->snapshot.size();shadows[b]=std::move(u);','shadows[b]=std::move(u);used+=n+s->snapshot.size();created=true;')
s=s.replace('else return nullptr;}return s;}','else return nullptr;}if(created){auto tag=assets.find(b);if(tag!=assets.end()&&Fingerprint(b)==tag->second.hash)LoadHD(b,tag->second.name.c_str());}return s;}')
s=s.replace('if(!nesting){nesting++;LoadHD(b,n);nesting--;}return b;', 'if(!nesting){nesting++;try{LoadHD(b,n);if(shadows.count(b))assets[b]={n,Fingerprint(b)};}catch(const std::bad_alloc&){if(logFile)fprintf(logFile,"asset allocation fallback\\n");}nesting--;}return b;')
s=s.replace('if(b && !force && b->keep)return oldFree(b,force);auto i=', 'if(b && !force && b->keep)return oldFree(b,force);assets.erase(b);auto i=')
s=s.replace('Shadow *sa,*sb;bool hd=Pair(a,ar,b,br,sa,sb);if(hd)', 'Shadow *sa=nullptr,*sb=nullptr;bool hd=false;try{hd=Pair(a,ar,b,br,sa,sb);}catch(const std::bad_alloc&){}if(hd)')
s=s.replace('Shadow *sa,*sb;bool hd=Pair(a,x,b,y,sa,sb);if(hd)', 'Shadow *sa=nullptr,*sb=nullptr;bool hd=false;try{hd=Pair(a,x,b,y,sa,sb);}catch(const std::bad_alloc&){}if(hd)')
s=s.replace('nesting++;auto s=Get(b,{0,0,b->w,b->h},true);nesting--;','nesting++;Shadow*s=nullptr;try{s=Get(b,{0,0,b->w,b->h},true);}catch(const std::bad_alloc&){}nesting--;')
s=s.replace('static BOOL WINAPI ToClient', '''static BOOL WINAPI Invalidate(HWND h,const RECT* r,BOOL erase){if(r&&h==Game()){auto v=Viewport(h);RECT z{v.x+MulDiv(r->left,v.w,800),v.y+MulDiv(r->top,v.h,600),v.x+(int)ceil(double(r->right)*v.w/800),v.y+(int)ceil(double(r->bottom)*v.h/600)};return InvalidateRect(h,&z,erase);}return InvalidateRect(h,r,erase);}\nstatic BOOL WINAPI ToClient''')
s=s.replace('s->b.w!=b->w*4||s->b.h!=b->h*4','s->b.w!=b->w*4||s->b.h!=b->h*4||s->b.format!=b->format||s->snapshot.size()!=size_t(b->pitch)*b->h')
a=s.index('static bool Install(){');b=s.index('BOOL WINAPI DllMain',a)
s=s[:a]+'''static bool Install(){
 for(auto& h:hooks)if(memcmp((void*)h.addr,h.expected,h.len))return false;
 void* allocated[32]{};unsigned count=0;uintptr_t pages[32]{};DWORD protections[32]{};unsigned pageCount=0;
 for(auto& h:hooks){if(h.original){auto t=(unsigned char*)VirtualAlloc(nullptr,h.len+5,MEM_COMMIT|MEM_RESERVE,PAGE_EXECUTE_READWRITE);if(!t){for(unsigned i=0;i<count;i++)VirtualFree(allocated[i],0,MEM_RELEASE);return false;}allocated[count++]=t;memcpy(t,(void*)h.addr,h.len);t[h.len]=0xe9;*(int32_t*)(t+h.len+1)=int32_t(h.addr+h.len-uintptr_t(t+h.len+5));*h.original=t;}}
 auto protect=[&](uintptr_t addr){uintptr_t p=addr&~uintptr_t(4095);for(unsigned i=0;i<pageCount;i++)if(pages[i]==p)return true;DWORD old;if(!VirtualProtect((void*)p,4096,PAGE_EXECUTE_READWRITE,&old))return false;pages[pageCount]=p;protections[pageCount++]=old;return true;};
 bool ok=true;for(auto& h:hooks){if(!protect(h.addr)||!protect(h.addr+h.len-1)){ok=false;break;}}if(ok)ok=protect(0x47406c);
 if(!ok){for(unsigned i=0;i<pageCount;i++){DWORD ignored;VirtualProtect((void*)pages[i],4096,protections[i],&ignored);}for(unsigned i=0;i<count;i++)VirtualFree(allocated[i],0,MEM_RELEASE);return false;}
 for(auto& h:hooks){memset((void*)h.addr,0x90,h.len);*(unsigned char*)h.addr=0xe9;*(int32_t*)(h.addr+1)=int32_t(uintptr_t(h.replacement)-h.addr-5);FlushInstructionCache(GetCurrentProcess(),(void*)h.addr,h.len);}
 *(void**)0x47406c=(void*)Present;*(void**)0x474374=(void*)ToClient;*(void**)0x47425c=(void*)ToScreen;*(void**)0x474260=(void*)Invalidate;
 for(unsigned i=0;i<pageCount;i++){DWORD ignored;VirtualProtect((void*)pages[i],4096,protections[i],&ignored);}return true;}
''' + s[b:]
p.write_text(s,encoding='utf-8-sig');print('patched failure handling, geometry invalidation, and source-aware cache reloading')
