"""timg_ops — 几何修复、画布重排、卖点图合成、拼图与裁切。"""
import os

import numpy as np
from PIL import Image, ImageDraw, ImageOps

from timg_core import (GREY, INK, TEAL, WHITE, _BOLD, _REG,
                       bbox, font, load, mask_of, save)


def fix(path, outp, tol=3, target_cov=0.78, max_mb=2.0):
    """裁成正方形 + 近白归一 + 按目标占比重排 + 压到体积上限。"""
    im, _ = load(path)
    w, h = im.size
    if w != h:
        s = min(w, h)
        im = im.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s))

    arr = np.asarray(im).astype(np.int16)
    bg = np.all(arr >= 255 - tol, axis=-1)
    if bg.any():
        arr[bg] = 255
        im = Image.fromarray(arr.astype(np.uint8))

    bb = bbox(mask_of(np.asarray(im.convert("L")), tol))
    if bb:
        obj = im.crop(bb)
        ow, oh = obj.size
        side = max(1, int(round(max(ow, oh) / target_cov)))
        canvas = Image.new("RGB", (side, side), WHITE)
        canvas.paste(obj, ((side - ow) // 2, (side - oh) // 2))
        im = canvas
    return save(im, outp, max_mb)


def _normalise(subj, ratio):
    """把裁剪块整形到目标长宽比（高/宽）。"""
    sw, sh = subj.size
    if sh / sw > ratio:
        return sh, int(round(sh / ratio))
    return int(round(sw * ratio)), sw


def relayout(src, outp, ratio=1.71, coverage=0.78, side=2048,
             strip_corner=False, tol=3, max_mb=2.0):
    im, _ = load(src)
    w, h = im.size
    m = mask_of(np.asarray(im.convert("L")), tol)
    if strip_corner:
        m[int(h * 0.90):, int(w * 0.80):] = False
    bb = bbox(m)
    if not bb:
        raise SystemExit("图中未找到产品，请确认背景为纯白")
    subj = im.crop(bb)
    nh, nw = _normalise(subj, ratio)
    subj = subj.resize((nw, nh), Image.LANCZOS)

    canvas_side = max(int(round(nh / coverage)), int(round(nw / coverage))) if side is None \
        else max(int(round(nh / coverage)), int(round(nw / coverage)))
    canvas = Image.new("RGB", (canvas_side, canvas_side), WHITE)
    canvas.paste(subj, ((canvas_side - nw) // 2, (canvas_side - nh) // 2))
    return save(canvas, outp, max_mb)


def _wrap(draw, text, fnt, max_w):
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if draw.textlength(trial, font=fnt) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def compose(main, outp, headline, subhead, anchor="spigot", ratio=1.71,
            side=2048, product_cov=0.62, max_mb=2.0):
    """复用主图产品像素 + 文字层，避免重新生成导致产品漂移。"""
    im, _ = load(main)
    bb = bbox(mask_of(np.asarray(im.convert("L")), 3))
    if not bb:
        raise SystemExit("主图中未找到产品")
    subj = im.crop(bb)
    nh, nw = _normalise(subj, ratio)
    subj = subj.resize((nw, nh), Image.LANCZOS)

    ph = int(side * product_cov)
    pw = max(1, int(round(ph / ratio)))
    subj = subj.resize((pw, ph), Image.LANCZOS)

    canvas = Image.new("RGB", (side, side), WHITE)
    px, py = (side - pw) // 2, side - ph - int(side * 0.06)
    canvas.paste(subj, (px, py))

    d = ImageDraw.Draw(canvas)
    fh, fs = font(_BOLD, int(side * 0.062)), font(_REG, int(side * 0.033))
    margin = int(side * 0.075)
    max_w = side - margin * 2

    y = int(side * 0.085)
    for line in _wrap(d, headline, fh, max_w):
        d.text((margin, y), line, font=fh, fill=INK)
        y += int(side * 0.078)
    y += int(side * 0.012)
    for line in _wrap(d, subhead, fs, max_w):
        d.text((margin, y), line, font=fs, fill=GREY)
        y += int(side * 0.046)

    if anchor == "spigot":
        ax, ay = px + pw * 0.486, py + ph * 0.955
    else:
        ax, ay = px + pw * 0.06, py + ph * 0.45

    lw = max(2, side // 900)
    ly = y + int(side * 0.02)
    if anchor == "spigot":
        gx = px + pw + int(side * 0.035)
        d.line([(side - margin, ly), (gx, ly), (gx, ay)], fill=TEAL, width=lw)
        d.line([(gx, ay), (ax + int(side * 0.012), ay)], fill=TEAL, width=lw)
    else:
        lx = margin + int(side * 0.005)
        d.line([(lx, ly), (lx, ay), (ax + int(side * 0.010), ay)],
               fill=TEAL, width=lw)
    r = max(5, side // 260)
    d.ellipse([ax - r, ay - r, ax + r, ay + r], fill=TEAL)
    return save(canvas, outp, max_mb)


def grid(paths, outp, cols=3, cell=800, gap=16, bg="#FFFFFF"):
    rows = -(-len(paths) // cols)
    W = cols * cell + (cols + 1) * gap
    H = rows * cell + (rows + 1) * gap
    canvas = Image.new("RGB", (W, H), bg)
    for i, p in enumerate(paths):
        im, _ = load(p)
        canvas.paste(ImageOps.fit(im, (cell, cell), Image.LANCZOS),
                     (gap + (i % cols) * (cell + gap),
                      gap + (i // cols) * (cell + gap)))
    canvas.save(outp, quality=92, optimize=True)
    return outp


CROP_MODULES = {
    "header": (970, 600), "overlay": (970, 300), "logo": (600, 180),
    "tile300": (300, 300), "tile220": (220, 220), "sidebar-main": (300, 400),
    "sidebar": (350, 175), "comparison": (150, 300), "brand-story": (1464, 625),
    "premium": (1464, 600), "premium-mobile": (600, 450),
}


def crop_to(src, outp, size):
    w, h = size
    im, _ = load(src)
    ImageOps.fit(im, (w, h), Image.LANCZOS).save(outp, quality=90, optimize=True)
    return outp


def stitch(paths, outp, width=750, slice_h=1546, max_mb=2.0):
    ims = []
    for p in sorted(paths):
        im, _ = load(p)
        ims.append(im.resize((width, max(1, round(im.height * width / im.width))),
                             Image.LANCZOS))
    H = sum(i.height for i in ims)
    canvas = Image.new("RGB", (width, H), WHITE)
    y = 0
    for im in ims:
        canvas.paste(im, (0, y))
        y += im.height
    save(canvas, outp, max_mb)
    made = []
    if slice_h:
        d = os.path.splitext(outp)[0] + "-slices"
        os.makedirs(d, exist_ok=True)
        for n, top in enumerate(range(0, H, slice_h), 1):
            piece = canvas.crop((0, top, width, min(top + slice_h, H)))
            p = os.path.join(d, f"{n:02d}.jpg")
            piece.save(p, quality=90, optimize=True)
            made.append(p)
    return outp, H, made
