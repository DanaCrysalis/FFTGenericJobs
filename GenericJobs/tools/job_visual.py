"""Job sheet artwork (ui/ffto/icon/job_visual/texture/jv_NN_{m,f}_uitx.tex): builds the faded 400x652 portrait the
Equipment & Abilities / Job screens draw behind the job panel, from character art on a white background.

  python tools/job_visual.py <art.png> <x> <y> <width> <out.png> [--corner cx cy rx ry] [--erase x0 y0 x1 y1 ...]

<x> <y> <width> is the crop in the source (its height follows the 400:652 ratio). The optional corner fades the
output toward its lower-right from (cx, cy) over (rx, ry) pixels, to hide a neighbouring figure; --erase clears
source rectangles (a neighbouring figure inside the crop). Then:
  png2bc7 out.png out.dds  (H:/FFT/WotLCharacters/tools/png2bc7, BC7, no mips)
  FF16Tools.CLI img-conv -i out.dds  -> .tex; the .utexpt is jv_21's with the name changed (same length).

Numbering follows the job order: jv_01 Squire .. jv_20 Mime (18 Bard male only, 19 Dancer female only),
jv_21 Dark Knight, jv_22 Onion Knight. Dark Knight's art (separate transparent male / female PNGs, 2026-10-06) is
251.3 wide at (61.7, 8.4) male / (76.8, 119.8) female, the framing of the mod's original jv_21. Onion Knight's: 268
wide at (4, 100) male with --corner 300 350 70 50, (262, 108) female with --erase 240 0 320 240 --erase 240 240 282 380
(the male's plume and sleeve). A transparent PNG's alpha is used as the cutout; otherwise the white background is.

Vanilla's look: the figure cut out of its background, times a fade that is strongest (alpha 207) at the top right
and falls off diagonally to the lower left, plus short ramps at the left and bottom edges (measured over all 38
vanilla jv textures).
"""
import sys
import numpy as np
from PIL import Image, ImageFilter

W, H = 400, 652

def fade_mask():
    y, x = np.mgrid[0:H, 0:W].astype(float)
    m = np.clip(0.49 * x - 0.52 * y + 208, 0, 207)
    m *= np.clip(x / 25, 0, 1) * np.clip((H - 1 - y) / 15, 0, 1)
    return m / 255

def cutout(src):
    """Coverage: everything except the near-white region connected to the image border (so white inside the
    figure stays)."""
    a = np.array(src.convert('RGB')).astype(int)
    white = (a.min(axis=2) > 232) & ((a.max(axis=2) - a.min(axis=2)) < 20)
    bg = np.zeros_like(white)
    bg[0, :], bg[-1, :], bg[:, 0], bg[:, -1] = white[0, :], white[-1, :], white[:, 0], white[:, -1]
    while True:
        g = bg.copy()
        g[1:] |= bg[:-1]; g[:-1] |= bg[1:]; g[:, 1:] |= bg[:, :-1]; g[:, :-1] |= bg[:, 1:]
        g &= white
        if (g == bg).all(): break
        bg = g
    fg = Image.fromarray((~bg).astype(np.uint8) * 255).filter(ImageFilter.GaussianBlur(0.7))
    return fg

def build(src_path, x0, y0, width, out, corner=None, erase=()):
    original = Image.open(src_path)
    box = (x0, y0, x0 + width, y0 + width * H / W)
    if original.mode == 'RGBA' and original.getextrema()[3][0] < 255:
        # transparent background: alpha is the coverage; resize premultiplied so edges keep their colour
        src = original.convert('RGBa')
        rgb = src.resize((W, H), Image.LANCZOS, box=box).convert('RGBA').convert('RGB')
        cut = original.getchannel('A')
    else:
        src = original.convert('RGB')
        rgb = src.resize((W, H), Image.LANCZOS, box=box)
        cut = cutout(src)
    for rect in erase:
        cut.paste(0, tuple(int(v) for v in rect))
    coverage = np.array(cut.resize((W, H), Image.LANCZOS, box=box)).astype(float) / 255
    m = fade_mask()
    if corner:
        cx, cy, rx, ry = corner
        y, x = np.mgrid[0:H, 0:W].astype(float)
        m *= 1 - np.clip((x - cx) / rx, 0, 1) * np.clip((y - cy) / ry, 0, 1)
    im = rgb.convert('RGBA')
    im.putalpha(Image.fromarray((coverage * m * 255).clip(0, 255).astype(np.uint8)))
    im.save(out)

if __name__ == '__main__':
    import argparse
    a = argparse.ArgumentParser(usage=__doc__)
    a.add_argument('art'); a.add_argument('x', type=float); a.add_argument('y', type=float)
    a.add_argument('width', type=float); a.add_argument('out')
    a.add_argument('--corner', type=float, nargs=4)
    a.add_argument('--erase', type=float, nargs=4, action='append', default=[])
    args = a.parse_args()
    build(args.art, args.x, args.y, args.width, args.out, args.corner, args.erase)
    print('wrote', args.out)
