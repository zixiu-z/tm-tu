#!/usr/bin/env python3
"""timg_core — Temu 商品图公共层：读图、测量、判定、保存。

性能要点：
- 白底检测基于灰度通道，只转一次 L 模式，避免 RGB 三通道掩码开销
- 大图按步长抽稀到 ≤1024，精度足够且计算量减半
- bbox 用 flatnonzero 取投影，不展开全部真值像素坐标
- 判定与读写只做必要 IO，避免重复 stat
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

# 分析用降采样上限。JPEG 在解码阶段直接 draft 到该尺寸，避免先解完整大图。
_ANALYZE_MAX = 1024
# 快速估算距离覆盖率阈值小于该值时，以全精度复核，防止边界误判。
_COVERAGE_RECHECK_MARGIN = 0.006


def font(preferred, size):
    for cand in (preferred,) + _FALLBACKS:
        try:
            return ImageFont.truetype(cand, size)
        except OSError:
            continue
    return ImageFont.load_default()


def load(path):
    """打开并强制解码，返回 (RGB Image, 格式名)。"""
    im = Image.open(path)
    im.load()
    return im.convert("RGB"), (im.format or "").upper()


def load_gray(path, draft_limit=None):
    """打开并转灰度；JPEG 可在解码阶段缩到 draft_limit 附近。

    Pillow 的 JPEG ``draft`` 使用解码器原生 1/2、1/4、1/8 缩放，避免先解
    完整大图再抽样。PNG/WebP 不支持时会自动维持原尺寸，语义不变。
    返回 (灰度图, 格式名, 原始尺寸)。
    """
    im = Image.open(path)
    fmt = (im.format or "").upper()
    original_size = im.size
    if draft_limit and max(original_size) > draft_limit:
        im.draft("L", (draft_limit, draft_limit))
    im.load()
    return im.convert("L"), fmt, original_size


def mask_of(gray, tol=3):
    """非白前景掩码。gray 为 u8 的 (H, W)。"""
    return gray < (255 - tol)


def bbox(mask):
    """掩码包围盒 (x0, y0, x1, y1)，空则 None。"""
    rows = np.flatnonzero(mask.any(axis=1))
    cols = np.flatnonzero(mask.any(axis=0))
    if rows.size == 0 or cols.size == 0:
        return None
    return int(cols[0]), int(rows[0]), int(cols[-1]) + 1, int(rows[-1]) + 1


def _sample(arr, limit=_ANALYZE_MAX):
    h, w = arr.shape[:2]
    step = max(1, int(np.ceil(max(h, w) / limit)))
    return arr[::step, ::step], step


def _measure(gray, tol, white_thr):
    """测量已解码灰度图，返回白边占比、主体占比和风险标记。"""
    s, _ = _sample(np.asarray(gray))
    sh, sw = s.shape
    by, bx = max(1, int(sh * 0.02)), max(1, int(sw * 0.02))

    # 分别计数四条边，避免 concatenate 产生额外数组和内存拷贝。
    white = (np.count_nonzero(s[:by] >= white_thr)
             + np.count_nonzero(s[-by:] >= white_thr)
             + np.count_nonzero(s[:, :bx] >= white_thr)
             + np.count_nonzero(s[:, -bx:] >= white_thr))
    border_pixels = by * sw * 2 + bx * sh * 2
    white_share = float(white / border_pixels)

    mask = mask_of(s, tol)
    bb = bbox(mask)
    coverage, risk = 0.0, False
    if bb:
        x0, y0, x1, y1 = bb
        coverage = max(x1 - x0, y1 - y0) / max(sw, sh)
        if white_share >= 0.9:
            outside = int(mask.sum()) - int(mask[y0:y1, x0:x1].sum())
            risk = outside / mask.size > 0.002
    return white_share, coverage, risk


def analyse(path, tol=3, white_thr=245, coverage_bounds=None):
    """快速分析一张图；阈值附近自动全精度复核，避免降采样误判。"""
    gray, fmt, (w, h) = load_gray(path, _ANALYZE_MAX)
    white_share, coverage, risk = _measure(gray, tol, white_thr)

    if coverage_bounds and fmt in ("JPEG", "JPG"):
        near_boundary = any(abs(coverage - bound) < _COVERAGE_RECHECK_MARGIN
                            for bound in coverage_bounds)
        if near_boundary and gray.size != (w, h):
            full, _, _ = load_gray(path)
            white_share, coverage, risk = _measure(full, tol, white_thr)

    square = abs(w - h) / max(w, h) <= 0.02
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
    r = analyse(path, args.tolerance,
                coverage_bounds=(args.min_coverage, args.max_coverage))
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
