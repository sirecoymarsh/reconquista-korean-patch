"""Other ways to make the 4x art, on a few pictures (the user, 10-25: 「흐린 외곽선에 강제로 검은 색 경계를 만드는게
업스케일 문제야」「다른 방식을 찾아 해결해보자」).
  python upscale_compare.py sources            source PNGs of the sample pictures (system Python: Codex's decoder, read-only)
  <forge venv python> upscale_compare.py torch  SwinIR-M classical x4 and Real-ESRGAN general x4v3 on them (CPU: since the
                                               driver resets at 07:21 on 10-25 every CUDA and Vulkan job crashes)
  python upscale_compare.py hybrid             the current art kept on crisp edges only, the soft rest from SwinIR / Lanczos
  python upscale_compare.py ncnn               Upscayl models on them (upscayl-bin, local GPU)
  python upscale_compare.py sheets             crops of the trouble spots, one column per method -> qa/upscale-compare/*.png
Models are the ones already on this PC (official sources, see the BRS project's models.json); nothing is downloaded.
"""
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parents[1]
OUT = HERE / 'qa' / 'upscale-compare'
SRC = OUT / 'src'
MODELS = Path(r'P:\AI\Codex\projects\black-rock-shooter-hd-ui-fonts\workspace\local-sr\models')
UPSCAYL = Path(r'P:\AI\Codex\projects\image-upscaling-tools\apps\Upscayl-2.15.0\resources')
SAMPLES = ['ev113a.rct', 'img107.rct', 'ev102_04.rct', 'bg_340a.rct', 'ev116_01.rct', 'netu101a.rct']
# trouble spots in source pixels: name, x, y, w, h, what to look at
SPOTS = [('ev113a.rct', 0, 0, 160, 120, 'blurred background'), ('ev113a.rct', 470, 300, 160, 120, 'phone edge on blur'),
         ('img107.rct', 230, 350, 160, 80, 'bus plate text'), ('img107.rct', 430, 130, 160, 120, 'bus side'),
         ('ev102_04.rct', 330, 110, 160, 120, 'face'), ('bg_340a.rct', 60, 60, 160, 120, 'building signs'),
         ('ev116_01.rct', 300, 150, 160, 120, 'soft light'), ('netu101a.rct', 80, 140, 160, 120, 'soft ground')]


def stem(n):
    return n.split('.')[0]


def sources():
    import upscale_review as U
    SRC.mkdir(parents=True, exist_ok=True)
    for n in SAMPLES:
        U.source(n).save(SRC / f'{stem(n)}.png')
        U.art(n).save(OUT / f'{stem(n)}.current.png')


def torch_models():
    import numpy as np
    import torch
    from PIL import Image
    from spandrel import ModelLoader
    dev = torch.device('cpu')
    torch.set_num_threads(12)
    for model_file, tag in [('001_classicalSR_DF2K_s64w8_SwinIR-M_x4.pth', 'swinir'), ('realesr-general-x4v3.pth', 'general')]:
        model = ModelLoader().load_from_file(str(MODELS / model_file)).to(dev).eval()
        for n in SAMPLES:
            img = np.asarray(Image.open(SRC / f'{stem(n)}.png').convert('RGB')).astype(np.float32) / 255
            x = torch.from_numpy(img).permute(2, 0, 1)[None].to(dev)
            out = np.zeros((img.shape[0] * 4, img.shape[1] * 4, 3), np.float32)
            t, pad = 200, 16                                    # tiles with an overlap, cropped back
            with torch.no_grad():
                for y0 in range(0, img.shape[0], t):
                    for x0 in range(0, img.shape[1], t):
                        ya, xa = max(0, y0 - pad), max(0, x0 - pad)
                        yb, xb = min(img.shape[0], y0 + t + pad), min(img.shape[1], x0 + t + pad)
                        r = model(x[:, :, ya:yb, xa:xb]).clamp(0, 1)[0].permute(1, 2, 0).cpu().numpy()
                        oy, ox = (y0 - ya) * 4, (x0 - xa) * 4
                        hh, ww = min(t, img.shape[0] - y0) * 4, min(t, img.shape[1] - x0) * 4
                        out[y0 * 4:y0 * 4 + hh, x0 * 4:x0 * 4 + ww] = r[oy:oy + hh, ox:ox + ww]
            Image.fromarray((out * 255 + .5).astype(np.uint8)).save(OUT / f'{stem(n)}.{tag}.png')
            print(tag, n, flush=True)


def ncnn():
    for model in ['upscayl-standard-4x', 'ultramix-balanced-4x', 'digital-art-4x']:
        dst = OUT / model
        dst.mkdir(exist_ok=True)
        subprocess.run([str(UPSCAYL / 'bin' / 'upscayl-bin.exe'), '-i', str(SRC), '-o', str(dst), '-n', model, '-m', str(UPSCAYL / 'models'),
                        '-s', '4', '-t', '256', '-f', 'png'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=0x08000000)
        for n in SAMPLES:
            f = dst / f'{stem(n)}.png'
            if f.exists():
                f.replace(OUT / f'{stem(n)}.{model}.png')
        print(model, flush=True)


def hybrid():
    """Crisp edges of the source (Sobel magnitude, blurred) keep the current AI art; soft areas (out of focus, smooth
    surfaces) take the faithful upscale, so no outline is drawn where the source has none."""
    import cv2
    import numpy as np
    for n in SAMPLES:
        src = cv2.imread(str(SRC / f'{stem(n)}.png'))
        h, w = src.shape[:2]
        g = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY).astype(np.float32)
        edge = cv2.GaussianBlur(cv2.magnitude(cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1)), (3, 3), 0)
        m = np.clip((edge - 40) / 80, 0, 1)                      # 0 below 40 (soft), 1 above 120 (a drawn line)
        m = cv2.GaussianBlur(cv2.resize(m, (w * 4, h * 4), interpolation=cv2.INTER_LINEAR), (9, 9), 0)[:, :, None]
        ai = cv2.imread(str(OUT / f'{stem(n)}.current.png')).astype(np.float32)
        for base, tag in [('swinir', 'hybrid-swinir'), ('lanczos', 'hybrid-lanczos')]:
            f = OUT / f'{stem(n)}.{base}.png'
            soft = cv2.resize(src, (w * 4, h * 4), interpolation=cv2.INTER_LANCZOS4).astype(np.float32) if base == 'lanczos' else cv2.imread(str(f)).astype(np.float32)
            cv2.imwrite(str(OUT / f'{stem(n)}.{tag}.png'), np.clip(m * ai + (1 - m) * soft + .5, 0, 255).astype(np.uint8))
        print('hybrid', n, 'crisp share', round(float(m.mean()) * 100, 1), '%', flush=True)


def sheets(methods):
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.truetype(r'C:\Windows\Fonts\malgun.ttf', 18)
    for k, (n, x, y, w, h, what) in enumerate(SPOTS):
        cols = []
        for tag, label in methods:
            f = SRC / f'{stem(n)}.png' if tag == 'lanczos' else OUT / f'{stem(n)}.{tag}.png'
            if not f.exists():
                continue
            im = Image.open(f).convert('RGB')
            c = im.crop((x, y, x + w, y + h)).resize((w * 4, h * 4), Image.LANCZOS) if tag == 'lanczos' else im.crop((x * 4, y * 4, (x + w) * 4, (y + h) * 4))
            cols.append((label, c))
        sheet = Image.new('RGB', (len(cols) * (w * 4 + 6), h * 4 + 28), (30, 30, 30))
        d = ImageDraw.Draw(sheet)
        for i, (label, c) in enumerate(cols):
            sheet.paste(c, (i * (w * 4 + 6), 28))
            d.text((i * (w * 4 + 6) + 4, 4), label, fill=(235, 235, 235), font=font)
        sheet.save(OUT / f'spot{k + 1}-{stem(n)}.png')


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    {'sources': sources, 'torch': torch_models, 'ncnn': ncnn, 'hybrid': hybrid}.get(sys.argv[1], lambda: sheets([
        ('lanczos', '원본 부드럽게(AI 없음)'), ('current', '지금(high-fidelity)'), ('swinir', 'SwinIR 충실형'), ('general', 'Real-ESRGAN 일반 v3'),
        ('hybrid-swinir', '섞기: 선은 지금, 나머지 SwinIR'), ('hybrid-lanczos', '섞기: 선은 지금, 나머지 부드럽게')]))()
