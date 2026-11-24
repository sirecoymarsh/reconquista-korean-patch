@echo off
rem 32-bit static libjxl 0.11.2, decoder and thread runner only, /MT like ReconquistaHD.dll.
rem Source: build\src-libjxl\libjxl (tag v0.11.2; highway, brotli c/, skcms src/ at the tag's submodule commits).
rem   build_libjxl.cmd       -> build\libjxl-x86      (SSE2: 32-bit MSVC gives Highway only its static target)
rem   build_libjxl.cmd avx   -> build\libjxl-x86-avx  (/arch:AVX, so Highway's static target becomes SSE4; needs an AVX CPU)
set TEMP=P:\AI\Codex\projects\reconquista_flowchart_20261024\build\temp
set TMP=%TEMP%
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars32.bat" >nul
set SRC=P:\AI\Codex\projects\reconquista_flowchart_20261024\build\src-libjxl\libjxl
set OUT=P:\AI\Codex\projects\reconquista_flowchart_20261024\build\libjxl-x86
set ARCH=
if /i "%1"=="avx" (set OUT=%OUT%-avx& set ARCH=/arch:AVX)
cmake -G Ninja -S "%SRC%" -B "%OUT%" -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=cl -DCMAKE_CXX_COMPILER=cl ^
 "-DCMAKE_C_FLAGS=/DWIN32 /D_WINDOWS %ARCH%" "-DCMAKE_CXX_FLAGS=/DWIN32 /D_WINDOWS /GR /EHsc %ARCH%" ^
 -DJPEGXL_STATIC=ON -DBUILD_SHARED_LIBS=OFF -DBUILD_TESTING=OFF -DJPEGXL_ENABLE_TOOLS=OFF -DJPEGXL_ENABLE_JPEGLI=OFF ^
 -DJPEGXL_ENABLE_DOXYGEN=OFF -DJPEGXL_ENABLE_MANPAGES=OFF -DJPEGXL_ENABLE_BENCHMARK=OFF -DJPEGXL_ENABLE_EXAMPLES=OFF ^
 -DJPEGXL_ENABLE_JNI=OFF -DJPEGXL_ENABLE_SJPEG=OFF -DJPEGXL_ENABLE_OPENEXR=OFF -DJPEGXL_ENABLE_TRANSCODE_JPEG=OFF ^
 -DJPEGXL_BUNDLE_LIBPNG=OFF -DJPEGXL_ENABLE_SKCMS=ON -DJPEGXL_ENABLE_TCMALLOC=OFF -DJPEGXL_ENABLE_FUZZERS=OFF ^
 -DJPEGXL_ENABLE_DEVTOOLS=OFF -DJPEGXL_ENABLE_PLUGINS=OFF -DJPEGXL_ENABLE_VIEWERS=OFF
if errorlevel 1 exit /b 1
cmake --build "%OUT%" --target jxl_dec jxl_threads
