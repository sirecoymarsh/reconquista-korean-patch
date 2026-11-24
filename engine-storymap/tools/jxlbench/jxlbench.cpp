// 32-bit decode timing for the HD layer's 4x art: JPEG XL through the same static libjxl as ReconquistaHD.dll (rows
// written as BGR from the worker threads, as the DLL does), PNG through WIC. Each file is read into memory first, so this
// is decode only; every case runs once to warm up and then `reps` times, and the best and median times are printed.
// jxlbench.exe <threads,threads,...> <reps> <file>...      threads 0 = no runner (single thread)
// jxlbench.exe --csv <threads> <reps> <jxl dir> <png dir>   every <key>.jxl against <key>.png: key,png_bytes,jxl_bytes,png_ms,jxl_ms (best)
#define JXL_STATIC_DEFINE
#define JXL_THREADS_STATIC_DEFINE
#define NOMINMAX
#include <windows.h>
#include <wincodec.h>
#include <psapi.h>
#include <wrl/client.h>
#include <jxl/decode.h>
#include <jxl/thread_parallel_runner.h>
#include "hwy/targets.h"
#include <algorithm>
#include <cstdio>
#include <functional>
#include <string>
#include <vector>

static LARGE_INTEGER freq;
static double Now() {LARGE_INTEGER t;QueryPerformanceCounter(&t);return 1000.0*t.QuadPart/freq.QuadPart;}
static std::vector<uint8_t> ReadAll(const wchar_t* path) {std::vector<uint8_t> d;HANDLE f=CreateFileW(path,GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,0,nullptr);if(f==INVALID_HANDLE_VALUE)return d;
 LARGE_INTEGER n{};GetFileSizeEx(f,&n);d.resize(size_t(n.QuadPart));DWORD got=0;ReadFile(f,d.data(),DWORD(d.size()),&got,nullptr);CloseHandle(f);d.resize(got);return d;}

struct Out {uint8_t* dst;size_t pitch;};
// header = create + basic info; total = header + full decode
static bool Jxl(const std::vector<uint8_t>& data,void* runner,std::vector<uint8_t>& px,double& header,double& total) {double t0=Now();JxlDecoder* dec=JxlDecoderCreate(nullptr);bool ok=dec!=nullptr;
 if(ok&&runner)ok=JxlDecoderSetParallelRunner(dec,JxlThreadParallelRunner,runner)==JXL_DEC_SUCCESS;
 if(ok)ok=JxlDecoderSubscribeEvents(dec,JXL_DEC_BASIC_INFO|JXL_DEC_FULL_IMAGE)==JXL_DEC_SUCCESS&&JxlDecoderSetInput(dec,data.data(),data.size())==JXL_DEC_SUCCESS;
 if(ok)JxlDecoderCloseInput(dec);JxlBasicInfo bi{};if(ok)ok=JxlDecoderProcessInput(dec)==JXL_DEC_BASIC_INFO&&JxlDecoderGetBasicInfo(dec,&bi)==JXL_DEC_SUCCESS;header=Now()-t0;
 Out out{nullptr,0};JxlPixelFormat fmt{3,JXL_TYPE_UINT8,JXL_NATIVE_ENDIAN,0};bool full=false;
 if(ok){out.pitch=(bi.xsize*3+3)&~size_t(3);px.resize(out.pitch*bi.ysize);out.dst=px.data();}
 auto row=[](void*o,size_t x,size_t y,size_t n,const void*p){auto&t=*(Out*)o;auto s=(const uint8_t*)p;auto d=t.dst+y*t.pitch+x*3;for(size_t i=0;i<n;i++,s+=3,d+=3){d[0]=s[2];d[1]=s[1];d[2]=s[0];}};
 while(ok){JxlDecoderStatus st=JxlDecoderProcessInput(dec);if(st==JXL_DEC_NEED_IMAGE_OUT_BUFFER)ok=JxlDecoderSetImageOutCallback(dec,&fmt,row,&out)==JXL_DEC_SUCCESS;
  else if(st==JXL_DEC_FULL_IMAGE)full=true;else if(st==JXL_DEC_SUCCESS)break;else ok=false;}
 if(dec)JxlDecoderDestroy(dec);total=Now()-t0;return ok&&full;}

static bool Png(IWICImagingFactory* wic,const std::vector<uint8_t>& data,std::vector<uint8_t>& px,double& total) {double t0=Now();Microsoft::WRL::ComPtr<IWICStream> s;Microsoft::WRL::ComPtr<IWICBitmapDecoder> dec;
 Microsoft::WRL::ComPtr<IWICBitmapFrameDecode> fr;Microsoft::WRL::ComPtr<IWICFormatConverter> cv;UINT w=0,h=0;HRESULT hr=wic->CreateStream(&s);
 if(SUCCEEDED(hr))hr=s->InitializeFromMemory(const_cast<BYTE*>(data.data()),DWORD(data.size()));if(SUCCEEDED(hr))hr=wic->CreateDecoderFromStream(s.Get(),nullptr,WICDecodeMetadataCacheOnLoad,&dec);
 if(SUCCEEDED(hr))hr=dec->GetFrame(0,&fr);if(SUCCEEDED(hr))hr=fr->GetSize(&w,&h);if(SUCCEEDED(hr))hr=wic->CreateFormatConverter(&cv);
 if(SUCCEEDED(hr))hr=cv->Initialize(fr.Get(),GUID_WICPixelFormat24bppBGR,WICBitmapDitherTypeNone,nullptr,0,WICBitmapPaletteTypeCustom);
 UINT pitch=(w*3+3)&~3u;if(SUCCEEDED(hr)){px.resize(size_t(pitch)*h);hr=cv->CopyPixels(nullptr,pitch,UINT(px.size()),px.data());}total=Now()-t0;return SUCCEEDED(hr);}

static void Report(const wchar_t* name,const char* what,std::vector<double> t,double header) {std::sort(t.begin(),t.end());
 wprintf(L"%-14s %-10S best %7.1f  median %7.1f ms",name,what,t.front(),t[t.size()/2]);if(header>=0)wprintf(L"  (header %.2f)",header);wprintf(L"\n");}

static double Best(int reps,const std::function<bool(double&)>& run) {double best=1e30,t=0;for(int k=0;k<=reps;k++){if(!run(t))return -1;if(k)best=std::min(best,t);}return best;}

static int Csv(int threads,int reps,const std::wstring& jdir,const std::wstring& pdir) {CoInitializeEx(nullptr,COINIT_MULTITHREADED);Microsoft::WRL::ComPtr<IWICImagingFactory> wic;
 CoCreateInstance(CLSID_WICImagingFactory,nullptr,CLSCTX_INPROC_SERVER,IID_PPV_ARGS(&wic));void* runner=threads>0?JxlThreadParallelRunnerCreate(nullptr,size_t(threads)):nullptr;
 WIN32_FIND_DATAW fd;HANDLE h=FindFirstFileW((jdir+L"\\*.jxl").c_str(),&fd);if(h==INVALID_HANDLE_VALUE)return 1;wprintf(L"key,png_bytes,jxl_bytes,png_ms,jxl_ms\n");
 do{std::wstring key(fd.cFileName,wcslen(fd.cFileName)-4);auto j=ReadAll((jdir+L"\\"+fd.cFileName).c_str()),p=ReadAll((pdir+L"\\"+key+L".png").c_str());if(j.empty()||p.empty())continue;
  std::vector<uint8_t> px;double header=0;double tj=Best(reps,[&](double&t){return Jxl(j,runner,px,header,t);}),tp=Best(reps,[&](double&t){return Png(wic.Get(),p,px,t);});
  wprintf(L"%s,%zu,%zu,%.2f,%.2f\n",key.c_str(),p.size(),j.size(),tp,tj);fflush(stdout);}while(FindNextFileW(h,&fd));FindClose(h);return 0;}

int wmain(int argc,wchar_t** argv) {QueryPerformanceFrequency(&freq);if(argc==6&&wcscmp(argv[1],L"--csv")==0)return Csv(_wtoi(argv[2]),std::max(1,_wtoi(argv[3])),argv[4],argv[5]);if(argc<4){wprintf(L"jxlbench.exe <threads,...> <reps> <file>...\n");return 2;}
 std::vector<int> threads;for(wchar_t* p=argv[1];*p;){threads.push_back(_wtoi(p));while(*p&&*p!=L',')p++;if(*p)p++;}int reps=std::max(1,_wtoi(argv[2]));
 wprintf(L"highway targets:");for(int64_t t:hwy::SupportedAndGeneratedTargets())wprintf(L" %S",hwy::TargetName(t));wprintf(L"\n");
 CoInitializeEx(nullptr,COINIT_MULTITHREADED);Microsoft::WRL::ComPtr<IWICImagingFactory> wic;CoCreateInstance(CLSID_WICImagingFactory,nullptr,CLSCTX_INPROC_SERVER,IID_PPV_ARGS(&wic));
 std::vector<std::pair<int,void*>> runners;for(int n:threads)runners.push_back({n,n>0?JxlThreadParallelRunnerCreate(nullptr,size_t(n)):nullptr});
 for(int i=3;i<argc;i++){std::wstring path=argv[i];const wchar_t* name=wcsrchr(argv[i],L'\\');name=name?name+1:argv[i];auto data=ReadAll(argv[i]);std::vector<uint8_t> px;
  if(data.empty()){wprintf(L"%s: cannot read\n",name);continue;}
  bool jxl=path.size()>4&&_wcsicmp(path.c_str()+path.size()-4,L".jxl")==0;
  if(jxl){for(auto&r:runners){std::vector<double> t;double header=0,h=0,total=0;bool ok=true;for(int k=0;k<=reps&&ok;k++){ok=Jxl(data,r.second,px,h,total);if(k){t.push_back(total);header+=h/reps;}}
    char what[32];sprintf_s(what,"jxl t=%d",r.first);if(ok)Report(name,what,t,header);else wprintf(L"%s: jxl decode failed\n",name);}}
  else{std::vector<double> t;double total=0;bool ok=true;for(int k=0;k<=reps&&ok;k++){ok=Png(wic.Get(),data,px,total);if(k)t.push_back(total);}if(ok)Report(name,"png wic",t,-1);else wprintf(L"%s: png decode failed\n",name);}}
 PROCESS_MEMORY_COUNTERS pm{sizeof(pm)};if(K32GetProcessMemoryInfo(GetCurrentProcess(),&pm,sizeof(pm)))wprintf(L"peak private %.1f MB, now %.1f MB\n",pm.PeakPagefileUsage/1048576.0,pm.PagefileUsage/1048576.0);
 return 0;}
