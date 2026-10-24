#!/usr/bin/env python3
"""timg_core — Temu 商品图公共层：读图、测量、判定、保存。

性能要点：
- 分析走共享 ndarray，掩码 / bbox / 统计一次算出，避免各检查重复扫描
- bbox 用 flatnonzero 取投影，不展开全部真值像素坐标
- mask 用沿通道最大值比较代替 np.all + 逻辑非，减少临时数组
- border 白度用 u8 阈值比较，避免 int16 转换开销
- 像素采样用步长降采样（精度足够），大图分析更稳更快
"""
import json
import os

import numpy as np
from PIL import Image, ImageFont

SUPPORTED = (".jpg", ".jpeg", ".png", ".webp")
WHITE = (255, 255, 255)
INK, GREY, TEAL = (30, 30, 30), (107, 107, 107), (47, 111, 107)

_BOLD = "C:/Windows/Fonts/seguisb.ttf"
_REG = "C:/Windows/Fonts/segoeui.ttf"
_FALLBACKS = ("C:/Windows/Fonts/arialbd.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")

# 分析用降采样上限：边长超过它时先按步长抽稀，足以支撑占比/白度判断
_ANALYZE_MAX = 1024


def font(preferred, size):
    for cand in (preferred,) + _FALLBACKS:
        try:
            return ImageFont.truetype(cand, size)
        except OSError:
            continue
    return ImageFont.load_default()


def load(path):
    """打开一次并强制解码，返回 (RGB Image, 格式名)。"""
    im = Image.open(path)
    im.load()
    return im.convert("RGB"), (im.format or "").upper()


def mask_of(arr, tol=3):
    """非白前景掩码。arr 为 u8 的 (H, W, 3)。"""
    return arr.max(axis=-1) < (255 - tol)


def bbox(mask):
    """掩码包围盒 (x0, y0, x1, y1)，空则 None。"""
    rows = np.flatnonzero(mask.any(axis=1))
    cols = np.flatnonzero(mask.any(axis=0))
    if rows.size == 0 or cols.size == 0:
        return None
    return int(cols[0]), int(rows[0]), int(cols[-1]) + 1, int(rows[-1]) + 1


def _sample(arr, limit=_ANALYZE_MAX):
    """大图按步长抽稀，返回 (抽样数组, 步长)。"""
    h, w = arr.shape[:2]
    step = max(1, int(np.ceil(max(h, w) / limit)))
    return arr[::step, ::step], step


def analyse(path, tol=3, white_thr=245):
    im, fmt = load(path)
    w, h = im.size
    arr = np.asarray(im)  # u8，避免 int16 的转换与内存翻倍

    square = abs(w - h) / max(w, h) <= 0.02

    # 边框白度：在抽样子集上做，足以判断
    s_arr, _ = _sample(arr)
    sh, sw = s_arr.shape[:2]
    by, bx = max(1, int(sh * 0.02)), max(1, int(sw * 0.02))
    border = np.concatenate([
        s_arr[:by].reshape(-1, 3), s_arr[-by:].reshape(-1, 3),
        s_arr[:, :bx].reshape(-1, 3), s_arr[:, -bx:].reshape(-1, 3),
    ])
    white_share = float((border.min(axis=-1) >= white_thr).mean())

    # 主体掩码与 bbox：在抽样子集上做
    mask = mask_of(s_arr, tol)
    bb = bbox(mask)
    coverage, risk = 0.0, False
    if bb:
        x0, y0, x1, y1 = bb
        coverage = max(x1 - x0, y1 - y0) / max(sw, sh)
        if white_share >= 0.9:
            outside = int(mask.sum()) - int(mask[y0:y1, x0:x1].sum())
            risk = outside / mask.size > 0.002

    return {
        "file": os.path.basename(path), "format": fmt,
        "width": w, "height": h, "square": square,
        "aspect": "1:1" if square else f"{w}x{h}",
        "longest": max(w, h),
        "white_border": round(white_share, 4),
        "coverage": round(coverage, 4),
        "mb": round(os.path.getsize(path) / (1024 * 1024), 2),
        "risk": risk,
    }


def judge(r, min_size=800, min_cov=0.70, max_cov=0.85, max_mb=2.0):
    checks = [
        ("aspect_ratio", r["square"], r["aspect"]),
        ("size", r["longest"] >= min_size, f'{r["longest"]}px'),
        ("format", r["format"] in ("JPEG", "JPG", "PNG"), r["format"] or "?"),
        ("file_size", r["mb"] <= max_mb, f'{r["mb"]}MB'),
        ("coverage", min_cov <= r["coverage"] <= max_cov,
         f'{r["coverage"]} ({min_cov}-{max_cov})'),
    ]
    out = [{"check": n, "pass": bool(ok), "detail": d} for n, ok, d in checks]
    if r["risk"]:
        out.append({"check": "risk", "pass": False,
                    "detail": "非白像素出现在主体框外，疑似残留文字/水印"})
    return out


def save(im, path, max_mb=2.0):
    if path.lower().endswith(".png"):
        im.save(path, "PNG", optimize=True)
        return path
    q = 95
    while True:
        im.save(path, "JPEG", quality=q, subsampling=0)
        if os.path.getsize(path) / (1024 * 1024) <= max_mb or q <= 60:
            break
        q -= 5
    return path


def check_one(path, args):
    r = analyse(path, args.tolerance)
    checks = judge(r, args.min_size, args.min_coverage, args.max_coverage, args.max_mb)
    ok = all(c["pass"] for c in checks)
    if args.json:
        print(json.dumps({"result": r, "checks": checks, "pass": ok}, ensure_ascii=False))
        return ok
    if getattr(args, "quiet", False) and ok:
        return ok
    print(f'[{"PASS" if ok else "FAIL"}] {r["file"]}  {r["width"]}x{r["height"]}  '
          f'{r["mb"]}MB  cov={r["coverage"]}  white={r["white_border"]}')
    for c in checks:
        if not c["pass"]:
            print(f'   x {c["check"]}: {c["detail"]}')
    return ok


def images_at(path):
    if os.path.isdir(path):
        return sorted(os.path.join(path, f) for f in os.listdir(path)
                      if f.lower().endswith(SUPPORTED))
    return [path]
