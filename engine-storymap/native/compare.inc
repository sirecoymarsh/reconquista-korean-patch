// The legacy CRT rejects some CP932 sequences under ACP 949 even when both byte strings are identical.
// Preserve the legacy case-insensitive comparison for every nonidentical pair.
using ExactCompareFn=int(__cdecl*)(const unsigned char*,const unsigned char*);
static ExactCompareFn oldExactCompare=nullptr;
static int __cdecl ExactCompare(const unsigned char*a,const unsigned char*b){
 if(a&&b){auto p=a,q=b;while(*p==*q){if(!*p)return 0;p++;q++;}}
 return oldExactCompare(a,b);
}
static void ProbeExactCompare(){
 static bool done=false;if(done||!probe||!oldExactCompare)return;done=true;
 const unsigned char jp[]={0x90,0x5e,0x94,0xbf,0x8e,0x71,0};
 const unsigned char kr[]={0xe0,0xc8,0xe2,0x4c,0xe1,0xe2,0};
 const unsigned char* a[]={jp,kr,(const unsigned char*)"",(const unsigned char*)"same",(const unsigned char*)"AbC",(const unsigned char*)"ABC",jp};
 const unsigned char* b[]={jp,kr,(const unsigned char*)"",(const unsigned char*)"same",(const unsigned char*)"aBc",(const unsigned char*)"xyz",kr};
 int failures=0;for(unsigned i=0;i<7;i++){int old=oldExactCompare(a[i],b[i]),value=ExactCompare(a[i],b[i]);bool ok=i<4?value==0:value==old;if(!ok)failures++;if(logFile)fprintf(logFile,"exact_compare sample=%u old=%d result=%d pass=%d\n",i,old,value,ok);}
 if(logFile){fprintf(logFile,"exact_compare_result checks=7 failures=%d\n",failures);fflush(logFile);}
}
