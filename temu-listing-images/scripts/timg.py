#!/usr/bin/env python3
"""timg — Temu 商品图命令行工具。

  python timg.py check    out/            # 质检单图或目录
  python timg.py fix      a.jpg b.jpg --out-dir fixed/
  python timg.py relayout src.jpg dst.jpg --ratio 1.71 --coverage 0.78
  python timg.py compose  main.jpg dst.jpg --headline "H" --subhead "S" --anchor spigot
  python timg.py grid     a.jpg b.jpg --cols 2 --out grid.jpg
  python timg.py crop     src.png --module premium
  python timg.py stitch   s1.png s2.png --width 750
  python timg.py batch    in/ out/ --headline "H" --subhead "S"
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import timg_core as C
import timg_ops as O

def _utf8_stdout():
    """Windows 控制台默认 cp1252，输出中文会 UnicodeEncodeError。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


_utf8_stdout()


def _check_args(a):
    ns = argparse.Namespace(
        min_size=a.min_size, min_coverage=a.min_coverage,
        max_coverage=a.max_coverage, max_mb=a.max_mb,
        tolerance=a.tolerance, json=a.json)
    return ns


def main():
    p = argparse.ArgumentParser(prog="timg", description="Temu 商品图工具集")
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp):
        sp.add_argument("--min-size", type=int, default=800)
        sp.add_argument("--min-coverage", type=float, default=0.70)
        sp.add_argument("--max-coverage", type=float, default=0.85)
        sp.add_argument("--max-mb", type=float, default=2.0)
        sp.add_argument("--tolerance", type=int, default=3)
        sp.add_argument("--json", action="store_true")

    c = sub.add_parser("check")
    c.add_argument("target")
    common(c)

    f = sub.add_parser("fix")
    f.add_argument("targets", nargs="+")
    f.add_argument("--out-dir", default="fixed")
    common(f)

    r = sub.add_parser("relayout")
    r.add_argument("src")
    r.add_argument("out")
    r.add_argument("--ratio", type=float, default=1.71)
    r.add_argument("--coverage", type=float, default=0.78)
    r.add_argument("--strip-corner", action="store_true")
    r.add_argument("--max-mb", type=float, default=2.0)

    m = sub.add_parser("compose")
    m.add_argument("main")
    m.add_argument("out")
    m.add_argument("--headline", required=True)
    m.add_argument("--subhead", required=True)
    m.add_argument("--anchor", default="spigot", choices=["spigot", "body"])
    m.add_argument("--ratio", type=float, default=1.71)
    m.add_argument("--side", type=int, default=2048)
    m.add_argument("--product-cov", type=float, default=0.62)
    m.add_argument("--max-mb", type=float, default=2.0)

    g = sub.add_parser("grid")
    g.add_argument("images", nargs="+")
    g.add_argument("--cols", type=int, default=3)
    g.add_argument("--cell", type=int, default=800)
    g.add_argument("--gap", type=int, default=16)
    g.add_argument("--out", default="grid.jpg")

    cr = sub.add_parser("crop")
    cr.add_argument("image")
    cr.add_argument("--module", choices=sorted(O.CROP_MODULES))
    cr.add_argument("--size")
    cr.add_argument("--out")

    st = sub.add_parser("stitch")
    st.add_argument("images", nargs="+")
    st.add_argument("--width", type=int, default=750)
    st.add_argument("--slice", dest="slice_h", type=int, default=1546)
    st.add_argument("--out", default="detail-750.jpg")
    st.add_argument("--max-mb", type=float, default=2.0)

    b = sub.add_parser("batch")
    b.add_argument("in_dir")
    b.add_argument("out_dir")
    b.add_argument("--headline", required=True)
    b.add_argument("--subhead", required=True)
    b.add_argument("--anchor", default="body", choices=["spigot", "body"])
    b.add_argument("--max-images", type=int, default=50)

    a = p.parse_args()
    ns = _check_args(a) if hasattr(a, "min_size") else None

    if a.cmd == "check":
        files = C.images_at(a.target)
        if not files:
            print("未找到图片")
            return 1
        oks = [C.check_one(x, ns) for x in files]
        if not a.json:
            print(f"\n{sum(oks)}/{len(oks)} passed")
        return 0 if all(oks) else 1

    if a.cmd == "fix":
        os.makedirs(a.out_dir, exist_ok=True)
        ok = True
        for src in a.targets:
            if not os.path.isfile(src):
                continue
            dst = os.path.join(a.out_dir, os.path.basename(src))
            O.fix(src, dst, max_mb=a.max_mb)
            print(f"  -> {dst}")
            ok &= C.check_one(dst, ns)
        return 0 if ok else 1

    if a.cmd == "relayout":
        O.relayout(a.src, a.out, a.ratio, a.coverage, None, a.strip_corner, max_mb=a.max_mb)
        print(f"  -> {a.out}")
        return 0

    if a.cmd == "compose":
        O.compose(a.main, a.out, a.headline, a.subhead, a.anchor, a.ratio,
                  a.side, a.product_cov, a.max_mb)
        print(f"  -> {a.out}")
        return 0

    if a.cmd == "grid":
        O.grid(a.images, a.out, a.cols, a.cell, a.gap)
        print(f"  -> {a.out}")
        return 0

    if a.cmd == "crop":
        if not a.module and not a.size:
            print("需要 --module 或 --size")
            return 1
        w, h = O.CROP_MODULES[a.module] if a.module else map(int, a.size.lower().split("x"))
        out = a.out or f"{os.path.splitext(a.image)[0]}-{w}x{h}.jpg"
        O.crop_to(a.image, out, (w, h))
        print(f"  -> {out}  {os.path.getsize(out) / 1024:.0f} KB")
        return 0

    if a.cmd == "stitch":
        out, H, made = O.stitch(a.images, a.out, a.width, a.slice_h, a.max_mb)
        print(f"  -> {out}  {a.width}x{H}  slices={len(made)}")
        return 0

    if a.cmd == "batch":
        os.makedirs(a.out_dir, exist_ok=True)
        files = C.images_at(a.in_dir)[: a.max_images]
        ok = 0
        for src in files:
            name = os.path.splitext(os.path.basename(src))[0]
            dst = os.path.join(a.out_dir, f"{name}-benefit.png")
            try:
                O.compose(src, dst, a.headline, a.subhead, a.anchor)
                ok += 1
            except SystemExit as e:
                print(f"  跳过 {name}: {e}")
        print(f"完成 {ok}/{len(files)}")
        return 0 if ok == len(files) else 1

    return 1


if __name__ == "__main__":
    sys.exit(main())
