"""Isolated offscreen GDI font test, never reads or controls a game window."""
from pathlib import Path
import ctypes as C,ctypes.wintypes as W,json,hashlib
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
G=C.WinDLL('gdi32',use_last_error=True)
G.AddFontResourceExW.argtypes=[W.LPCWSTR,W.DWORD,C.c_void_p];G.AddFontResourceExW.restype=C.c_int
G.RemoveFontResourceExW.argtypes=[W.LPCWSTR,W.DWORD,C.c_void_p];G.RemoveFontResourceExW.restype=W.BOOL
G.CreateCompatibleDC.argtypes=[W.HDC];G.CreateCompatibleDC.restype=W.HDC
G.CreateFontW.argtypes=[C.c_int]*5+[W.DWORD]*8+[W.LPCWSTR];G.CreateFontW.restype=W.HANDLE
G.SelectObject.argtypes=[W.HDC,W.HANDLE];G.SelectObject.restype=W.HANDLE
G.DeleteObject.argtypes=[W.HANDLE];G.DeleteDC.argtypes=[W.HDC]
G.SetTextColor.argtypes=[W.HDC,W.DWORD];G.SetBkMode.argtypes=[W.HDC,C.c_int]
G.TextOutA.argtypes=[W.HDC,C.c_int,C.c_int,C.c_char_p,C.c_int];G.TextOutA.restype=W.BOOL
G.TextOutW.argtypes=[W.HDC,C.c_int,C.c_int,W.LPCWSTR,C.c_int];G.TextOutW.restype=W.BOOL
G.GetTextFaceW.argtypes=[W.HDC,C.c_int,W.LPWSTR];G.GetTextFaceW.restype=C.c_int
G.GetTextCharset.argtypes=[W.HDC];G.GetTextCharset.restype=C.c_int
G.GetGlyphIndicesW.argtypes=[W.HDC,W.LPCWSTR,C.c_int,C.POINTER(W.WORD),W.DWORD];G.GetGlyphIndicesW.restype=W.DWORD
class BIH(C.Structure):
 _fields_=[('size',W.DWORD),('width',W.LONG),('height',W.LONG),('planes',W.WORD),('bitcount',W.WORD),('compression',W.DWORD),('sizeimage',W.DWORD),('xppm',W.LONG),('yppm',W.LONG),('colorsused',W.DWORD),('colorsimportant',W.DWORD)]
class BMI(C.Structure):_fields_=[('header',BIH),('colors',W.DWORD*3)]
G.CreateDIBSection.argtypes=[W.HDC,C.POINTER(BMI),W.UINT,C.POINTER(C.c_void_p),W.HANDLE,W.DWORD];G.CreateDIBSection.restype=W.HANDLE

def run(fontpath,family='Reconquista KR',reportname='font-gdi-check.json',mapping_path=None):
 mapping=json.loads(Path(mapping_path).read_text(encoding='utf-8'))['mapping']
 samples=['드디어 만났네','마키노 모미지 마사키 쿠레하 장인','제품 디스크 오류 해결. 한국어 표시 시험']
 # Required samples must use mapped characters only; render every mapped syllable too.
 samples=[s for s in samples if all(not ('가'<=c<='힣') or c in mapping for c in s)]
 glyphs=''.join(sorted(mapping)); samples += [glyphs[i:i+28] for i in range(0,len(glyphs),28)]
 assert G.AddFontResourceExW(str(fontpath),0x10,None)>0
 results=[]
 try:
  for charset in [1,128]:
   dc=G.CreateCompatibleDC(None); width=900;height=max(180,len(samples)*34+30)
   info=BMI();info.header=BIH(C.sizeof(BIH),width,-height,1,32,0,0,0,0,0,0);bits=C.c_void_p()
   bitmap=G.CreateDIBSection(dc,C.byref(info),0,C.byref(bits),None,0);assert bitmap and bits.value
   prevbm=G.SelectObject(dc,bitmap)
   font=G.CreateFontW(23,11,0,0,400,0,0,0,charset,0,0,3,0,family);assert font
   prevfont=G.SelectObject(dc,font);face=C.create_unicode_buffer(128);G.GetTextFaceW(dc,128,face)
   assert face.value==family,face.value
   charset_actual=G.GetTextCharset(dc)
   G.SetBkMode(dc,1);G.SetTextColor(dc,0x202020)
   array=(W.WORD*len(glyphs))();assert G.GetGlyphIndicesW(dc,glyphs,len(glyphs),array,1)!=0xffffffff
   assert 0xffff not in array
   pixels=[]
   for ansi in [True,False]:
    C.memset(bits,255,width*height*4)
    for row,text in enumerate(samples):
     if ansi:
      encoded=''.join(mapping.get(c,c) for c in text).encode('cp932');assert G.TextOutA(dc,20,15+34*row,encoded,len(encoded))
     else:assert G.TextOutW(dc,20,15+34*row,text,len(text))
    G.GdiFlush();pixels.append(C.string_at(bits,width*height*4))
   same=pixels[0]==pixels[1]
   nonwhite=sum(a!=255 for a in pixels[0]);assert nonwhite>1000
   result={'requested_charset':charset,'actual_charset':charset_actual,'font_face':face.value,'hangul_glyphs':len(glyphs),'missing_glyphs':0,'mapped_TextOutA_equals_Hangul_TextOutW':same,'nonwhite_channel_bytes':nonwhite,'pixels_sha256':hashlib.sha256(pixels[0]).hexdigest()}
   results.append(result)
   if not same:
    for kind,pixel in zip(['mapped-ansi','unicode'],pixels):
     image=Image.frombytes('RGBA',(width,height),pixel,'raw','BGRA');image.convert('RGB').save(ROOT/'reports'/f'font-gdi-{charset}-{kind}.png')
   G.SelectObject(dc,prevfont);G.DeleteObject(font);G.SelectObject(dc,prevbm);G.DeleteObject(bitmap);G.DeleteDC(dc)
  report={'test':'isolated offscreen Windows GDI; not a game screenshot or in-game verification','font':str(fontpath),'font_sha256':hashlib.sha256(fontpath.read_bytes()).hexdigest(),'results':results,'pass':all(r['mapped_TextOutA_equals_Hangul_TextOutW'] for r in results)}
  (ROOT/'reports'/reportname).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
  print(json.dumps(report,ensure_ascii=False,indent=2));assert report['pass']
 finally:G.RemoveFontResourceExW(str(fontpath),0x10,None)
