@echo off
set TEMP=P:\AI\Codex\projects\reconquista_flowchart_20261024\build\temp
set TMP=%TEMP%
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars32.bat" >nul
cl /nologo /std:c++17 /O2 /MT /EHsc /utf-8 membench.cpp /link /OUT:membench.exe
