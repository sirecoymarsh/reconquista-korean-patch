"""How the 연표 「원래 크기로」 button looks: the window printed (PrintWindow, child windows included) while zoomed in and
while the whole table is shown, cut to the top bar (page y 0..70) so no chronicle entry is in the picture.
python probe_zoom_button.py   -> qa/zoom_button_in.png, qa/zoom_button_out.png (look, then delete)
"""
import ctypes as c
import time
from ctypes import wintypes as w

import numpy as np
from PIL import Image

import qa
import test_chronicle_perf as T

WM_MOUSEWHEEL = 0x20A
g32 = c.WinDLL('gdi32')
u = qa.u
u.PrintWindow.argtypes = [w.HWND, w.HDC, w.UINT]


def print_window(hwnd, cw, ch):
    hdc = u.GetDC(hwnd)
    mem = g32.CreateCompatibleDC(hdc)
    bmp = g32.CreateCompatibleBitmap(hdc, cw, ch)
    old = g32.SelectObject(mem, bmp)
    u.PrintWindow(hwnd, mem, 3)                       # PW_CLIENTONLY | PW_RENDERFULLCONTENT

    class BIH(c.Structure):
        _fields_ = [('biSize', w.DWORD), ('biWidth', w.LONG), ('biHeight', w.LONG), ('biPlanes', w.WORD), ('biBitCount', w.WORD), ('biCompression', w.DWORD),
                    ('biSizeImage', w.DWORD), ('biXPelsPerMeter', w.LONG), ('biYPelsPerMeter', w.LONG), ('biClrUsed', w.DWORD), ('biClrImportant', w.DWORD)]
    bih = BIH(c.sizeof(BIH), cw, -ch, 1, 32, 0, 0, 0, 0, 0, 0)
    buf = (c.c_ubyte * (cw * ch * 4))()
    g32.GetDIBits(mem, bmp, 0, ch, buf, c.byref(bih), 0)
    g32.SelectObject(mem, old)
    g32.DeleteObject(bmp)
    g32.DeleteDC(mem)
    u.ReleaseDC(hwnd, hdc)
    return np.frombuffer(buf, np.uint8).reshape(ch, cw, 4)[:, :, 2::-1]


g = qa.Game(run=T.RUN, extra_env={'RECON_PERF': '2'})
try:
    frame = T.keys('クロニクル枠')
    g.until(lambda: any(f'asset {k} ' in g.log() for k in frame), 60, 'chronicle frame')
    g.hwnd = next(x['h'] for x in g.windows() if x['class'] == 'MAJIRO_EXEC_CLASS')
    if not u.IsWindowVisible(g.hwnd):
        u.ShowWindow(g.hwnd, 4)
    time.sleep(4)
    cr = qa.w.RECT()
    u.GetClientRect(g.hwnd, c.byref(cr))
    cw, ch = cr.right, cr.bottom
    vw, vh = (ch * 4 // 3, ch) if cw * 3 > ch * 4 else (cw, cw * 3 // 4)
    vx, vy = (cw - vw) // 2, (ch - vh) // 2
    p = qa.w.POINT(vx + vw // 2, vy + vh // 2)
    u.ClientToScreen(g.hwnd, c.byref(p))

    def wheel(n):
        for _ in range(abs(n)):
            g.post(g.hwnd, WM_MOUSEWHEEL, ((120 if n > 0 else -120) & 0xffff) << 16, ((p.y & 0xffff) << 16) | (p.x & 0xffff))
            time.sleep(.3)

    def top_bar(name):
        img = print_window(g.hwnd, cw, ch)[vy:vy + vh * 70 // 600, vx:vx + vw]
        Image.fromarray(np.ascontiguousarray(img)).save(qa.QA / name)

    wheel(2)
    time.sleep(1)
    top_bar('zoom_button_in.png')
    wheel(-6)
    g.until(lambda: 'overview capture done' in g.log(), 60, 'capture done')
    time.sleep(1.5)
    top_bar('zoom_button_out.png')
finally:
    print('normal_exit', g.close_normally())
