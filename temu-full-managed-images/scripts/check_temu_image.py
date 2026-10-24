#!/usr/bin/env python3
"""Check (and optionally fix) Temu listing images.

Every Temu image produced by this skill must be 1:1 square.

  python check_temu_image.py out/01-main.jpg
  python check_temu_image.py out/ --batch
  python check_temu_image.py out/01-main.jpg --fix out/01-main-fixed.jpg
  python check_temu_image.py out/ --batch --min-coverage 0.70 --max-coverage 0.85 --max-mb 2

Checks
  aspect_ratio : |w - h| / max(w, h) <= 0.02        (1:1 required)
  size         : longest side >= --min-size (800)
  format       : JPG / JPEG / PNG
  file_size    : <= --max-mb MB
  white_bg     : white share of the outer 2% border band
  coverage     : product bounding box / canvas side, target range
  risk         : non-white clusters inside a white-background image
                 (leftover text / watermark / badge heuristic)

--fix : centre-crop to a square, snap near-white border pixels to pure
        #FFFFFF, re-crop/pad to the target coverage on a square canvas,
        and re-compress to stay under --max-mb.

Requires: pillow, numpy
"""
import argparse
import json
import os
import sys

try:
    import numpy as np
    from PIL import Image
except ImportError:
    sys.exit("pip install pillow numpy")

SUPPORTED = (".jpg", ".jpeg", ".png")


def _product_mask(rgb, tolerance=3):
    """Boolean mask of pixels that are not near-white background."""
    near_white = np.all(np.abs(rgb - 255) <= tolerance, axis=-1)
    return ~near_white


def analyse(path, tolerance=3, white_threshold=245):
    img = Image.open(path)
    fmt = (img.format or "").upper()
    w, h = img.size
    rgb = np.asarray(img.convert("RGB")).astype(np.int16)

    # aspect
    ratio_dev = abs(w - h) / max(w, h)
    is_square = ratio_dev <= 0.02

    # border whiteness (outer 2% band)
    band_y = max(1, int(round(h * 0.02)))
    band_x = max(1, int(round(w * 0.02)))
    border = np.concatenate([
        rgb[:band_y, :, :].reshape(-1, 3),
        rgb[-band_y:, :, :].reshape(-1, 3),
        rgb[:, :band_x, :].reshape(-1, 3),
        rgb[:, -band_x:, :].reshape(-1, 3),
    ])
    white_px = np.all(border >= white_threshold, axis=-1)
    white_share = float(white_px.mean())

    # coverage from product bounding box
    mask = _product_mask(rgb, tolerance)
    coverage = 0.0
    if mask.any():
        ys, xs = np.where(mask)
        bw = xs.max() - xs.min() + 1
        bh = ys.max() - ys.min() + 1
        coverage = float(max(bw, bh) / max(w, h))

    # risk: dense non-white cluster well inside a white-background image
    risk = False
    if white_share >= 0.9 and mask.any():
        inner_y, inner_x = int(h * 0.1), int(w * 0.1)
        inner = mask[inner_y:h - inner_y, inner_x:w - inner_x]
        if inner.size:
            # count columns/rows fully outside the main object's bbox
            ys, xs = np.where(mask)
            y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
            outside = mask.copy()
            outside[max(0, y0):y1 + 1, max(0, x0):x1 + 1] = False
            risk = float(outside.mean()) > 0.002

    size_mb = os.path.getsize(path) / (1024 * 1024)

    return {
        "file": os.path.basename(path),
        "format": fmt,
        "width": w,
        "height": h,
        "aspect_ratio": "1:1" if is_square else f"{w}:{h} ({ratio_dev:.1%} off square)",
        "is_square": is_square,
        "longest_side": max(w, h),
        "white_border_share": round(white_share, 4),
        "coverage": round(coverage, 4),
        "file_size_mb": round(size_mb, 2),
        "risk_needs_review": risk,
    }


def judge(result, min_size, min_cov, max_cov, max_mb):
    checks = []

    def add(name, ok, detail):
        checks.append({"check": name, "pass": bool(ok), "detail": detail})

    add("aspect_ratio", result["is_square"], result["aspect_ratio"])
    add("size", result["longest_side"] >= min_size,
        f"{result['longest_side']}px (min {min_size})")
    add("format", result["format"] in ("JPEG", "JPG", "PNG"), result["format"] or "unknown")
    add("file_size", result["file_size_mb"] <= max_mb,
        f"{result['file_size_mb']}MB (max {max_mb})")
    add("coverage", min_cov <= result["coverage"] <= max_cov,
        f"{result['coverage']} (target {min_cov}-{max_cov})")
    return checks


def fix(path, out_path, tolerance=3, target_coverage=0.78, max_mb=2.0):
    img = Image.open(path).convert("RGB")
    w, h = img.size

    # 1) centre square crop
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    img = img.crop((left, top, left + side, top + side))

    arr = np.asarray(img).astype(np.int16)

    # 2) snap near-white border pixels to pure white
    mask = ~_product_mask(arr, tolerance)
    pure = arr.copy()
    pure[mask] = 255
    img = Image.fromarray(pure.astype(np.uint8))

    # 3) re-frame to target coverage on a white square canvas
    m = _product_mask(np.asarray(img).astype(np.int16), tolerance)
    if m.any():
        ys, xs = np.where(m)
        y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
        obj = img.crop((x0, y0, x1 + 1, y1 + 1))
        ow, oh = obj.size
        canvas_side = int(round(max(ow, oh) / target_coverage))
        canvas = Image.new("RGB", (canvas_side, canvas_side), (255, 255, 255))
        canvas.paste(obj, ((canvas_side - ow) // 2, (canvas_side - oh) // 2))
        img = canvas

    # 4) compress under the size limit
    ext = os.path.splitext(out_path)[1].lower()
    quality = 95
    while True:
        if ext == ".png":
            img.save(out_path, "PNG", optimize=True)
        else:
            img.save(out_path, "JPEG", quality=quality, subsampling=0)
        if os.path.getsize(out_path) / (1024 * 1024) <= max_mb or quality <= 60:
            break
        quality -= 5
    return out_path


def run_one(path, args):
    if not os.path.isfile(path):
        print(f"SKIP {path}: not a file")
        return True
    if os.path.splitext(path)[1].lower() not in SUPPORTED:
        return True
    res = analyse(path, args.tolerance)
    checks = judge(res, args.min_size, args.min_coverage, args.max_coverage, args.max_mb)
    passed = all(c["pass"] for c in checks) and not res["risk_needs_review"]
    if args.json:
        print(json.dumps({"result": res, "checks": checks, "pass": passed}, ensure_ascii=False))
        return passed

    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {res['file']}  {res['width']}x{res['height']}  "
          f"{res['file_size_mb']}MB  coverage={res['coverage']}  "
          f"border_white={res['white_border_share']}")
    for c in checks:
        if not c["pass"]:
            print(f"   x {c['check']}: {c['detail']}")
    if res["risk_needs_review"]:
        print("   x risk: non-white cluster outside the product area — check leftover text/watermark")
    return passed


def main():
    p = argparse.ArgumentParser(description="Check / fix Temu 1:1 listing images")
    p.add_argument("target", help="image file or directory")
    p.add_argument("--batch", action="store_true", help="treat target as a directory")
    p.add_argument("--fix", metavar="OUT", help="write a corrected 1:1 image")
    p.add_argument("--min-size", type=int, default=800)
    p.add_argument("--min-coverage", type=float, default=0.70)
    p.add_argument("--max-coverage", type=float, default=0.85)
    p.add_argument("--max-mb", type=float, default=2.0)
    p.add_argument("--tolerance", type=int, default=3)
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    if args.fix:
        out = fix(args.target, args.fix, args.tolerance, max_mb=args.max_mb)
        print(f"fixed -> {out}")
        run_one(out, args)
        return 0

    if args.batch or os.path.isdir(args.target):
        files = sorted(
            os.path.join(args.target, f) for f in os.listdir(args.target)
            if os.path.splitext(f)[1].lower() in SUPPORTED
        )
        if not files:
            print("no images found")
            return 1
        results = [run_one(f, args) for f in files]
        ok = sum(results)
        print(f"\n{ok}/{len(results)} passed")
        return 0 if ok == len(results) else 1

    return 0 if run_one(args.target, args) else 1


if __name__ == "__main__":
    sys.exit(main())
