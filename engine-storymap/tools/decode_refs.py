"""Decode selected original UI rasters to PNG (read-only use of Codex's GARbro-based decoder)."""
import sys
from pathlib import Path
import numpy as np
from PIL import Image

TOOLS = Path(r'P:\AI\Codex\projects\migrated-from-c\onedrive-chatgpt\레콘퀴스타\ui-opening-ending\tools')
sys.path.insert(0, str(TOOLS))
from decode_ui import decode, SRC  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / 'ref' / 'ui'
OUT.mkdir(parents=True, exist_ok=True)

NAMES = sys.argv[1:] or [
    'クロニクル青バー', 'クロニクル灰バー', '情報隠蔽', '選択肢台', 'askyesno_base', 'サブエピソード用の枠',
    'バックログ画面', 'ヒストリボタン', 'ボタン説明', 'レイアウトサンプル', 'momiba1', 'momiba5', 'momiba8',
    '右上▲_ダーク', '右上▲_ライト', 'wink_▽', '薄い黒シード', 'ラスター用パターン', 'submenu_下敷き', 'submenu_マーク',
    '名前プレート_？？？', '名前プレート_槙野', '名前プレート_信哉', 'コンフィグボタン', 'perfectcircle',
]


def alpha_for(stem):
    mask = SRC / f'{stem}_.rc8'
    if not mask.exists():
        return None
    m = np.asarray(decode(mask.name)[0].convert('L')).astype('uint8')
    return 255 - m


for stem in NAMES:
    for ext in ('.rct', '.rc8'):
        p = SRC / (stem + ext)
        if not p.exists():
            continue
        im, meta = decode(p.name)
        a = alpha_for(stem) if ext == '.rct' else None
        if a is not None and a.shape == (im.height, im.width):
            rgba = im.convert('RGBA')
            rgba.putalpha(Image.fromarray(a))
            rgba.save(OUT / f'{stem}.png')
        else:
            im.convert('RGBA' if im.mode == 'P' else im.mode).save(OUT / f'{stem}{ext.replace(".", "_")}.png')
        print(stem + ext, im.size, im.mode, 'alpha' if a is not None else '')
        break
    else:
        print('missing', stem)
