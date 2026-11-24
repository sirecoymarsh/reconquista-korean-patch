// 11-21 diagnostic only (built with /DRECON_CRASHLOG by BuildDiag.cmd): an unhandled exception writes crash-<pid>.dmp and
// a symbolized stack ("CRASH #n addr module!function+off file:line") to hires-runtime.log. The rebuilt DLL crashed now and
// then going from the 연표 to a scene, never under a debugger, so the process has to report it itself.
#ifdef RECON_CRASHLOG
#include <dbghelp.h>
#pragma comment(lib, "dbghelp.lib")
static LPTOP_LEVEL_EXCEPTION_FILTER crashPrev = nullptr;
static LONG WINAPI CrashFilter(EXCEPTION_POINTERS* ep);
static void CrashlogInstall() {
  LPTOP_LEVEL_EXCEPTION_FILTER was = SetUnhandledExceptionFilter(CrashFilter);
  if (was != CrashFilter) crashPrev = was;
  static int calls = 0;   // RECON_CRASHLOG_TEST: the logger's own check, a null write in a worker thread 3 s after the first frame
  if (++calls == 2 && GetEnvironmentVariableW(L"RECON_CRASHLOG_TEST", nullptr, 0) > 0)   // (in a window callback WOW64 swallows it)
    CloseHandle(CreateThread(nullptr, 0, [](LPVOID) -> DWORD { Sleep(3000); *(volatile int*)nullptr = 1; return 0; }, nullptr, 0, nullptr));
}
static LONG WINAPI CrashFilter(EXCEPTION_POINTERS* ep) {
  static volatile LONG once = 0;
  if (InterlockedExchange(&once, 1)) return EXCEPTION_CONTINUE_SEARCH;
  auto* er = ep->ExceptionRecord;
  if (logFile) {
    fprintf(logFile, "CRASH code=%08lx addr=%p info=%p,%p thread=%lu\n", er->ExceptionCode, er->ExceptionAddress,
            (void*)(er->NumberParameters > 0 ? er->ExceptionInformation[0] : 0), (void*)(er->NumberParameters > 1 ? er->ExceptionInformation[1] : 0),
            GetCurrentThreadId());
    fflush(logFile);
  }
  wchar_t path[MAX_PATH];
  swprintf_s(path, L"%s\\crash-%lu.dmp", root, GetCurrentProcessId());
  HANDLE f = CreateFileW(path, GENERIC_WRITE, 0, nullptr, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
  if (f != INVALID_HANDLE_VALUE) {
    MINIDUMP_EXCEPTION_INFORMATION mei{GetCurrentThreadId(), ep, FALSE};
    MiniDumpWriteDump(GetCurrentProcess(), GetCurrentProcessId(), f,
                      (MINIDUMP_TYPE)(MiniDumpWithIndirectlyReferencedMemory | MiniDumpWithThreadInfo | MiniDumpScanMemory), &mei, nullptr, nullptr);
    CloseHandle(f);
  }
  HANDLE proc = GetCurrentProcess();
  SymSetOptions(SYMOPT_UNDNAME | SYMOPT_DEFERRED_LOADS | SYMOPT_LOAD_LINES);
  char sp[MAX_PATH * 2];
  WideCharToMultiByte(CP_ACP, 0, root, -1, sp, sizeof sp, nullptr, nullptr);
  SymInitialize(proc, sp, TRUE);
  CONTEXT ctx = *ep->ContextRecord;
  STACKFRAME64 sf{};
  sf.AddrPC.Offset = ctx.Eip; sf.AddrPC.Mode = AddrModeFlat;
  sf.AddrFrame.Offset = ctx.Ebp; sf.AddrFrame.Mode = AddrModeFlat;
  sf.AddrStack.Offset = ctx.Esp; sf.AddrStack.Mode = AddrModeFlat;
  if (logFile) fprintf(logFile, "CRASH regs eax=%08lx ebx=%08lx ecx=%08lx edx=%08lx esi=%08lx edi=%08lx ebp=%08lx esp=%08lx\n",
                       ctx.Eax, ctx.Ebx, ctx.Ecx, ctx.Edx, ctx.Esi, ctx.Edi, ctx.Ebp, ctx.Esp);
  for (int i = 0; i < 48 && StackWalk64(IMAGE_FILE_MACHINE_I386, proc, GetCurrentThread(), &sf, &ctx, nullptr, SymFunctionTableAccess64, SymGetModuleBase64, nullptr); i++) {
    DWORD64 a = sf.AddrPC.Offset;
    char buf[sizeof(SYMBOL_INFO) + 256]{};
    auto* si = (SYMBOL_INFO*)buf;
    si->SizeOfStruct = sizeof(SYMBOL_INFO); si->MaxNameLen = 255;
    DWORD64 disp = 0; IMAGEHLP_LINE64 ln{}; ln.SizeOfStruct = sizeof(ln); DWORD ld = 0;
    char mod[MAX_PATH] = "?"; HMODULE hm = nullptr;
    if (GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT, (LPCSTR)(uintptr_t)a, &hm))
      GetModuleFileNameA(hm, mod, MAX_PATH);
    const char* m = strrchr(mod, '\\') ? strrchr(mod, '\\') + 1 : mod;
    bool hs = SymFromAddr(proc, a, &disp, si) != FALSE, hl = SymGetLineFromAddr64(proc, a, &ld, &ln) != FALSE;
    if (logFile) fprintf(logFile, "CRASH #%d %p %s!%s+0x%llx %s:%lu\n", i, (void*)(uintptr_t)a, m, hs ? si->Name : "?", disp,
                         hl ? ln.FileName : "", hl ? ln.LineNumber : 0UL);
  }
  // other threads' state is in the dump; the log also lists this DLL's base for offline mapping
  HMODULE self = GetModuleHandleW(L"ReconquistaHD.dll");
  if (logFile) { fprintf(logFile, "CRASH dll_base=%p exe_base=%p\n", (void*)self, (void*)GetModuleHandleW(nullptr)); fflush(logFile); }
  return crashPrev ? crashPrev(ep) : EXCEPTION_CONTINUE_SEARCH;
}
#else
static void CrashlogInstall() {}
#endif
