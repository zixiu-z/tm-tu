#!/usr/bin/env python3
"""timg_core 性能基准（手动运行，不属于回归测试）。

运行：python tests/benchmark_timg.py [图片目录]
默认会合成 32 张 1200/2400px JPEG 到临时目录。
"""
import glob
import os
import statistics
import sys
import tempfile
import time

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(SKILL, "scripts"))
import timg_core as C  # noqa: E402


def make_fixtures(root):
    for i in range(32):
        side = 2400 if i < 16 else 1200
        im = Image.new("RGB", (side, side), "white")
        d = ImageDraw.Draw(im)
        margin = int(side * (0.10 + (i % 5) * 0.008))
        d.rounded_rectangle((margin, margin, side - margin, side - margin),
                            radius=side // 15, fill=(40 + i * 3, 100 + i * 2, 150))
        im.save(os.path.join(root, f"{i:02d}.jpg"), quality=92)


def run(paths, rounds=5):
    values = []
    for _ in range(rounds):
        start = time.perf_counter()
        for path in paths:
            C.analyse(path)
        values.append(time.perf_counter() - start)
    best = min(values)
    print(f"图片数: {len(paths)}")
    print(f"最好: {best:.4f}s  中位数: {statistics.median(values):.4f}s")
    print(f"吞吐: {len(paths) / best:.1f} 张/秒")


def main():
    if len(sys.argv) > 1:
        paths = glob.glob(os.path.join(sys.argv[1], "*"))
        run(paths)
        return
    with tempfile.TemporaryDirectory() as root:
        make_fixtures(root)
        run(sorted(glob.glob(os.path.join(root, "*.jpg"))))


if __name__ == "__main__":
    main()
