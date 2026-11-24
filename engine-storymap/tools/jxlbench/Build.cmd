@echo off
rem jxlbench.exe: 32-bit, same static libjxl as native\Build.cmd. Output goes to build\jxlbench.
rem   Build.cmd       -> jxlbench.exe      (build\libjxl-x86)
rem   Build.cmd avx   -> jxlbench-avx.exe  (build\libjxl-x86-avx, /arch:AVX)
set TEMP=P:\AI\Codex\projects\reconquista_flowchart_20261024\build\temp
set TMP=%TEMP%
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars32.bat" >nul
set JXL=P:\AI\Codex\projects\reconquista_flowchart_20261024\build\libjxl-x86
set HWY=P:\AI\Codex\projects\reconquista_flowchart_20261024\build\src-libjxl\libjxl\third_party\highway
set OUT=P:\AI\Codex\projects\reconquista_flowchart_20261024\build\jxlbench
set NAME=jxlbench
set ARCH=
if /i "%1"=="avx" (set JXL=%JXL%-avx& set NAME=jxlbench-avx& set ARCH=/arch:AVX)
if not exist "%OUT%\%NAME%" mkdir "%OUT%\%NAME%"
cl /nologo /std:c++17 /O2 /MT /EHsc /W3 /utf-8 %ARCH% /I "%JXL%\lib\include" /I "%HWY%" /Fo"%OUT%\%NAME%\\" "%~dp0jxlbench.cpp" /link /OUT:"%OUT%\%NAME%.exe" ole32.lib windowscodecs.lib "%JXL%\lib\jxl_dec.lib" "%JXL%\lib\jxl_threads.lib" "%JXL%\third_party\highway\hwy.lib" "%JXL%\third_party\brotli\brotlidec.lib" "%JXL%\third_party\brotli\brotlicommon.lib"
