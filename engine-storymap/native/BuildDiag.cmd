@echo off
set TEMP=P:\AI\Codex\projects\reconquista_flowchart_20261024\build\temp
set TMP=%TEMP%
if not exist "%TEMP%" mkdir "%TEMP%"
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars32.bat" >nul
rem libjxl 0.11.2, 32-bit static decoder: tools\build_libjxl.cmd
set JXL=P:\AI\Codex\projects\reconquista_flowchart_20261024\build\libjxl-x86
cl /nologo /std:c++17 /O2 /MT /EHsc /W4 /LD /utf-8 /DRECON_CRASHLOG /Zi /Fd"diag\\" /I "%JXL%\lib\include" ReconquistaHD.cpp /link /DEBUG /OPT:REF /OPT:ICF /PDB:"diag\ReconquistaHD.pdb" /OUT:"diag\ReconquistaHD.dll" user32.lib gdi32.lib ole32.lib windowscodecs.lib msimg32.lib synchronization.lib "%JXL%\lib\jxl_dec.lib" "%JXL%\lib\jxl_threads.lib" "%JXL%\third_party\highway\hwy.lib" "%JXL%\third_party\brotli\brotlidec.lib" "%JXL%\third_party\brotli\brotlicommon.lib"
