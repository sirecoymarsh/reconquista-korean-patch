// What the 4K layer's per-load memory work costs on this PC (32-bit, like the game): a fresh 4x shadow (allocation, page
// faults, zero fill), the same on a recycled buffer, a 23 MB copy, and the asset fingerprint (byte FNV-1a vs. wider ones).
// membench.exe -> one line per measurement, median of 15 runs.
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <intrin.h>
#include <nmmintrin.h>
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <vector>
#include <algorithm>
#include <functional>
static LARGE_INTEGER freq;
static double Now(){LARGE_INTEGER t;QueryPerformanceCounter(&t);return 1000.0*t.QuadPart/freq.QuadPart;}
static double Median(std::function<void()> f,int runs=15){std::vector<double> t;for(int i=0;i<runs;i++){double a=Now();f();t.push_back(Now()-a);}std::sort(t.begin(),t.end());return t[t.size()/2];}
static volatile uint64_t sink;
static uint64_t Fnv(const unsigned char*p,int w,int h,int pitch){uint64_t x=1469598103934665603ull;for(int y=0;y<h;y++)for(int i=0;i<w;i++){x^=p[y*pitch+i];x*=1099511628211ull;}return x;}
// four 32-bit FNV-1a lanes over 4-byte words, then a 64-bit mix of the lanes and the row tails
static uint64_t Fnv4(const unsigned char*p,int w,int h,int pitch){uint32_t a=2166136261u,b=a^1,c=a^2,d=a^3;uint64_t tail=1469598103934665603ull;
 for(int y=0;y<h;y++){const unsigned char*r=p+size_t(y)*pitch;int i=0;for(;i+16<=w;i+=16){uint32_t v[4];memcpy(v,r+i,16);a=(a^v[0])*16777619u;b=(b^v[1])*16777619u;c=(c^v[2])*16777619u;d=(d^v[3])*16777619u;}
  for(;i<w;i++){tail^=r[i];tail*=1099511628211ull;}}
 uint64_t x=tail;for(uint32_t v:{a,b,c,d}){x^=v;x*=1099511628211ull;}return x;}
static uint64_t Crc(const unsigned char*p,int w,int h,int pitch){uint32_t a=~0u,b=~1u,c=~2u;uint64_t tail=1469598103934665603ull;
 for(int y=0;y<h;y++){const unsigned char*r=p+size_t(y)*pitch;int i=0;for(;i+12<=w;i+=12){uint32_t v[3];memcpy(v,r+i,12);a=_mm_crc32_u32(a,v[0]);b=_mm_crc32_u32(b,v[1]);c=_mm_crc32_u32(c,v[2]);}
  for(;i<w;i++){tail^=r[i];tail*=1099511628211ull;}}
 return tail^(uint64_t(a)<<32|b)^(uint64_t(c)*0x9e3779b97f4a7c15ull);}
int main(){QueryPerformanceFrequency(&freq);SetThreadAffinityMask(GetCurrentThread(),2);
 const size_t shadow=size_t(9600)*2400;   // an 800x600 RGB bitmap at 4x
 printf("fresh_vector_zero_ms=%.2f\n",Median([&]{std::vector<unsigned char> v(shadow);sink+=v[shadow/2];}));
 printf("fresh_new_touch_ms=%.2f\n",Median([&]{auto*p=new unsigned char[shadow];for(size_t i=0;i<shadow;i+=4096)p[i]=1;sink+=p[shadow/3];delete[] p;}));
 std::vector<unsigned char> a(shadow,1),b(shadow,2);
 printf("reused_memset_ms=%.2f\n",Median([&]{memset(a.data(),0,shadow);sink+=a[7];}));
 printf("reused_memcpy_ms=%.2f\n",Median([&]{memcpy(b.data(),a.data(),shadow);sink+=b[9];}));
 printf("fresh_vector_copy_ms=%.2f\n",Median([&]{std::vector<unsigned char> v=a;sink+=v[11];}));
 std::vector<unsigned char> low(size_t(2400)*600);for(size_t i=0;i<low.size();i++)low[i]=(unsigned char)(i*2654435761u>>13);
 printf("fingerprint_fnv_byte_ms=%.2f\n",Median([&]{sink+=Fnv(low.data(),2400,600,2400);}));
 printf("fingerprint_fnv4_ms=%.2f\n",Median([&]{sink+=Fnv4(low.data(),2400,600,2400);}));
 printf("fingerprint_crc32c_ms=%.2f\n",Median([&]{sink+=Crc(low.data(),2400,600,2400);}));
 return 0;}
