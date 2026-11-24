// Reading one 4x art file. hires-jxl\<key>.jxl (tools/convert_jxl.py, select_jxl.py) is the JPEG XL copy of
// hires\<key>.png: colour art lossy at distance 0.5 (about 48 dB) with decoding speed tier 3, kept only where it decodes
// sooner than the PNG (1,811 of 2,059, 1.75 GB against 12.8 GB; small art and the gray masks stay PNG). libjxl 0.11.2
// (static, decoder only, SSE2 in 32-bit MSVC) writes rows straight into the shadow from its worker threads, R and B
// swapped for the engine's BGR. A PNG newer than its .jxl wins (the art was rebuilt after the conversion); a .jxl that
// fails falls back to the PNG for the run.
#define JXL_STATIC_DEFINE
#define JXL_THREADS_STATIC_DEFINE
#include <jxl/decode.h>
#include <jxl/thread_parallel_runner.h>
static void* jxlRunner=nullptr;static std::unordered_set<uint32_t> jxlSkip;static int jxlParity=0;
struct PngArt {Microsoft::WRL::ComPtr<IWICBitmapDecoder> dec;Microsoft::WRL::ComPtr<IWICBitmapFrameDecode> frame;Microsoft::WRL::ComPtr<IWICFormatConverter> cv;
 HRESULT Open(const wchar_t*path,UINT w,UINT h,int format){UINT fw=0,fh=0;HRESULT hr=wic->CreateDecoderFromFilename(path,nullptr,GENERIC_READ,WICDecodeMetadataCacheOnLoad,&dec);
  if(SUCCEEDED(hr))hr=dec->GetFrame(0,&frame);if(SUCCEEDED(hr))hr=frame->GetSize(&fw,&fh);if(SUCCEEDED(hr)&&(fw!=w||fh!=h))hr=E_INVALIDARG;
  if(SUCCEEDED(hr))hr=wic->CreateFormatConverter(&cv);if(SUCCEEDED(hr))hr=cv->Initialize(frame.Get(),format?GUID_WICPixelFormat8bppGray:GUID_WICPixelFormat24bppBGR,WICBitmapDitherTypeNone,nullptr,0,WICBitmapPaletteTypeCustom);return hr;}
 HRESULT Copy(std::vector<unsigned char>&target,int pitch){return cv->CopyPixels(nullptr,UINT(pitch),UINT(target.size()),target.data());}
 HRESULT CopyTo(unsigned char*target,int pitch,size_t size){return cv->CopyPixels(nullptr,UINT(pitch),UINT(size),target);}};
struct JxlArt {std::vector<uint8_t> data;JxlDecoder*dec=nullptr;int ch=3;
 ~JxlArt(){if(dec)JxlDecoderDestroy(dec);}
 // Reads the file and its header: true when it holds a w x h image that can be taken with this many channels. run/ctx: a
 // parallel runner other than the shared 16-thread one (prefetch.inc reads ahead on low-priority threads).
 bool Open(const wchar_t*path,int w,int h,int channels,JxlParallelRunner run=nullptr,void*ctx=nullptr){ch=channels;HANDLE f=CreateFileW(path,GENERIC_READ,FILE_SHARE_READ|FILE_SHARE_DELETE,nullptr,OPEN_EXISTING,FILE_FLAG_SEQUENTIAL_SCAN,nullptr);if(f==INVALID_HANDLE_VALUE)return false;
  LARGE_INTEGER size{};DWORD got=0;bool ok=GetFileSizeEx(f,&size)&&size.QuadPart>0&&size.QuadPart<(256ll<<20);if(ok){try{data.resize(size_t(size.QuadPart));}catch(const std::bad_alloc&){ok=false;}}
  if(ok)ok=ReadFile(f,data.data(),DWORD(data.size()),&got,nullptr)&&got==data.size();CloseHandle(f);if(!ok)return false;
  if(!run){if(!jxlRunner)jxlRunner=JxlThreadParallelRunnerCreate(nullptr,size_t(std::clamp(int(std::thread::hardware_concurrency())-1,1,16)));run=JxlThreadParallelRunner;ctx=jxlRunner;}
  if(!(dec=JxlDecoderCreate(nullptr)))return false;if(ctx&&JxlDecoderSetParallelRunner(dec,run,ctx)!=JXL_DEC_SUCCESS)return false;
  if(JxlDecoderSubscribeEvents(dec,JXL_DEC_BASIC_INFO|JXL_DEC_FULL_IMAGE)!=JXL_DEC_SUCCESS||JxlDecoderSetInput(dec,data.data(),data.size())!=JXL_DEC_SUCCESS)return false;JxlDecoderCloseInput(dec);
  JxlBasicInfo bi{};if(JxlDecoderProcessInput(dec)!=JXL_DEC_BASIC_INFO||JxlDecoderGetBasicInfo(dec,&bi)!=JXL_DEC_SUCCESS)return false;
  return bi.xsize==uint32_t(w)&&bi.ysize==uint32_t(h)&&(channels==3||bi.num_color_channels==1);}
 HRESULT Finish(unsigned char*dst,int pitch){if(!dec)return E_FAIL;struct Out{unsigned char*dst;size_t pitch,ch;} out{dst,size_t(pitch),size_t(ch)};JxlPixelFormat fmt{uint32_t(ch),JXL_TYPE_UINT8,JXL_NATIVE_ENDIAN,0};bool full=false;
  auto row=[](void*o,size_t x,size_t y,size_t n,const void*px){auto&t=*(Out*)o;auto s=(const unsigned char*)px;auto d=t.dst+y*t.pitch+x*t.ch;if(t.ch==1){memcpy(d,s,n);return;}for(size_t i=0;i<n;i++,s+=3,d+=3){d[0]=s[2];d[1]=s[1];d[2]=s[0];}};
  for(;;){JxlDecoderStatus st=JxlDecoderProcessInput(dec);if(st==JXL_DEC_NEED_IMAGE_OUT_BUFFER){if(JxlDecoderSetImageOutCallback(dec,&fmt,row,&out)!=JXL_DEC_SUCCESS)return E_FAIL;}
   else if(st==JXL_DEC_FULL_IMAGE)full=true;else if(st==JXL_DEC_SUCCESS)return full?S_OK:E_FAIL;else return E_FAIL;}}};
// The .jxl is current when it exists and the PNG (if any) is not newer.
static bool JxlCurrent(uint32_t key,const wchar_t*jxl,const wchar_t*png,bool&pngExists){WIN32_FILE_ATTRIBUTE_DATA j{},p{};pngExists=GetFileAttributesExW(png,GetFileExInfoStandard,&p)!=0;
 if(jxlSkip.count(key)||!GetFileAttributesExW(jxl,GetFileExInfoStandard,&j))return false;if(pngExists&&CompareFileTime(&p.ftLastWriteTime,&j.ftLastWriteTime)>0){jxlSkip.insert(key);if(logFile){fprintf(logFile,"jxl_stale key=%08x (png is newer)\n",key);fflush(logFile);}return false;}return true;}
static void JxlFailed(uint32_t key,const char*stage){jxlSkip.insert(key);if(logFile){fprintf(logFile,"jxl_error key=%08x stage=%s\n",key,stage);fflush(logFile);}}
// perf only, first eight loads: the same art through the PNG, so a colour or row mistake shows up as a low score
static void JxlParity(uint32_t key,const wchar_t*png,UINT w,UINT h,int format,const std::vector<unsigned char>&got,int pitch){if(!parity||!logFile||jxlParity>=8)return;jxlParity++;
 PngArt ref;std::vector<unsigned char> want(got.size());if(FAILED(ref.Open(png,w,h,format))||FAILED(ref.Copy(want,pitch)))return;double se=0;int worst=0;size_t span=size_t(w)*(format?1:3);
 for(UINT y=0;y<h;y++)for(size_t x=0;x<span;x++){int d=int(got[y*size_t(pitch)+x])-int(want[y*size_t(pitch)+x]);se+=double(d)*d;worst=std::max(worst,std::abs(d));}
 double mse=se/(double(span)*h);fprintf(logFile,"perf_jxl_parity key=%08x psnr=%.2f max_diff=%d\n",key,mse>0?10*log10(65025.0/mse):99.0,worst);fflush(logFile);}
