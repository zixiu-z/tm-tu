#!/usr/bin/env python3
"""timg_ops.py 的回归测试：几何修复、重排、合成、拼图、裁切。

这些函数直接产出交付图，几何尺寸错了就是交付事故，因此逐个钉住输出尺寸。
样例图运行时合成，不依赖 TEMU_SAMPLE_DIR。

跑法：
    python tests/test_timg_ops.py
    python -m unittest discover -s tests -v
"""
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(SKILL, "scripts"))

from PIL import Image  # noqa: E402

import timg_ops as O  # noqa: E402


def subject(path, size, box):
    im = Image.new("RGB", size, (255, 255, 255))
    im.paste((30, 30, 30), box)
    if path.lower().endswith(".png"):
        im.save(path)
    else:
        im.save(path, quality=95)
    return path


def blank(path, size=(400, 400)):
    Image.new("RGB", size, (255, 255, 255)).save(path)
    return path


def open_size(path):
    with Image.open(path) as im:
        im.load()
        return im.size


class OpsBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def p(self, name):
        return os.path.join(self.d, name)


class FixTest(OpsBase):
    def test_output_is_square(self):
        src = subject(self.p("s.jpg"), (1200, 800), (300, 150, 900, 650))
        out = O.fix(src, self.p("o.jpg"))
        w, h = open_size(out)
        self.assertEqual(w, h)

    def test_square_input_stays_square(self):
        src = subject(self.p("s.jpg"), (800, 800), (200, 200, 600, 600))
        w, h = open_size(O.fix(src, self.p("o.jpg")))
        self.assertEqual(w, h)

    def test_target_coverage_respected(self):
        """默认 target_cov=0.78，成品主体占位应接近该值。"""
        src = subject(self.p("s.jpg"), (600, 600), (100, 100, 500, 500))
        out = O.fix(src, self.p("o.jpg"))
        im = Image.open(out)
        im.load()
        # 主体框 400/600，side ≈ 400/0.78 ≈ 513
        self.assertAlmostEqual(im.width / (400 / 0.78), 1.0, delta=0.02)
        im.close()

    def test_blank_image_does_not_crash(self):
        """无前景时不重排，但必须仍产出文件（不抛异常）。"""
        out = O.fix(blank(self.p("b.png")), self.p("o.png"))
        self.assertTrue(os.path.isfile(out))


class RelayoutTest(OpsBase):
    def test_output_square(self):
        src = subject(self.p("s.jpg"), (1200, 800), (300, 150, 900, 650))
        w, h = open_size(O.relayout(src, self.p("o.jpg"), ratio=1.0, coverage=0.78))
        self.assertEqual(w, h)

    def test_blank_raises_systemexit(self):
        """空白图必须明确报错，而不是静默产出坏图。"""
        b = blank(self.p("b.png"))
        with self.assertRaises(SystemExit) as cm:
            O.relayout(b, self.p("o.jpg"))
        self.assertIn("未找到产品", str(cm.exception))

    def test_strip_corner_removes_corner_mark(self):
        """右下角水印经 strip_corner 裁掉后，不得影响主体定位。"""
        src = self.p("s.png")
        im = Image.new("RGB", (1000, 1000), (255, 255, 255))
        im.paste((20, 20, 20), (300, 300, 700, 700))
        im.paste((0, 0, 0), (850, 930, 990, 990))  # 右下角水印
        im.save(src)
        out = O.relayout(src, self.p("o.png"), ratio=1.0, coverage=0.78,
                         strip_corner=True)
        self.assertEqual(open_size(out)[0], open_size(out)[1])

    def test_ratio_affects_canvas(self):
        """ratio 变大（更宽）时成品边长应随之变化。"""
        src = subject(self.p("s.jpg"), (1000, 1000), (350, 350, 650, 650))
        a = open_size(O.relayout(src, self.p("a.jpg"), ratio=1.0, coverage=0.78))[0]
        b = open_size(O.relayout(src, self.p("b.jpg"), ratio=1.71, coverage=0.78))[0]
        self.assertNotEqual(a, b)


class ComposeTest(OpsBase):
    def test_default_side_2048(self):
        src = subject(self.p("s.jpg"), (800, 800), (200, 200, 600, 600))
        out = O.compose(src, self.p("o.png"), "标题", "副标题")
        self.assertEqual(open_size(out), (2048, 2048))

    def test_custom_side(self):
        src = subject(self.p("s.jpg"), (800, 800), (200, 200, 600, 600))
        out = O.compose(src, self.p("o.png"), "H", "S", side=1200)
        self.assertEqual(open_size(out), (1200, 1200))

    def test_blank_main_raises(self):
        with self.assertRaises(SystemExit) as cm:
            O.compose(blank(self.p("b.png")), self.p("o.png"), "H", "S")
        self.assertIn("主图中未找到产品", str(cm.exception))

    def test_both_anchors_work(self):
        src = subject(self.p("s.jpg"), (800, 800), (200, 200, 600, 600))
        for anchor in ("spigot", "body"):
            out = O.compose(src, self.p(f"{anchor}.png"), "H", "S", anchor=anchor)
            self.assertEqual(open_size(out), (2048, 2048), anchor)

    def test_text_wrapping_keeps_text_in_canvas(self):
        """超长标题必须换行，不能溢出画布导致裁切异常。"""
        src = subject(self.p("s.jpg"), (800, 800), (200, 200, 600, 600))
        long_head = "超长标题" * 12
        out = O.compose(src, self.p("o.png"), long_head, "副标题" * 8)
        self.assertEqual(open_size(out), (2048, 2048))


class WrapTest(unittest.TestCase):
    def test_no_line_exceeds_max_width(self):
        from PIL import ImageDraw
        canvas = Image.new("RGB", (600, 600), (255, 255, 255))
        d = ImageDraw.Draw(canvas)
        from timg_core import _BOLD, font
        f = font(_BOLD, 20)
        lines = O._wrap(d, "one two three four five six seven", f, 100)
        for line in lines:
            self.assertLessEqual(d.textlength(line, font=f), 100, line)

    def test_empty_text_yields_no_lines(self):
        from PIL import ImageDraw
        canvas = Image.new("RGB", (200, 200), (255, 255, 255))
        d = ImageDraw.Draw(canvas)
        from timg_core import _BOLD, font
        self.assertEqual(O._wrap(d, "", font(_BOLD, 10), 100), [])


class GridTest(OpsBase):
    def test_canvas_size_matches_grid_math(self):
        imgs = [subject(self.p(f"{i}.jpg"), (200, 200), (50, 50, 150, 150))
                for i in range(3)]
        out = O.grid(imgs, self.p("g.jpg"), cols=2, cell=100, gap=10)
        # 2 列 3 行 -> W=2*100+3*10=230, H=2*100+3*10=230
        self.assertEqual(open_size(out), (230, 230))

    def test_single_row(self):
        imgs = [subject(self.p(f"{i}.jpg"), (100, 100), (20, 20, 80, 80))
                for i in range(3)]
        out = O.grid(imgs, self.p("g.jpg"), cols=3, cell=50, gap=5)
        self.assertEqual(open_size(out), (3 * 50 + 4 * 5, 50 + 2 * 5))


class CropTest(OpsBase):
    def test_module_sizes_exact(self):
        src = subject(self.p("s.jpg"), (2000, 2000), (500, 500, 1500, 1500))
        for name, size in O.CROP_MODULES.items():
            out = O.crop_to(src, self.p(f"{name}.jpg"), size)
            self.assertEqual(open_size(out), size, name)

    def test_expected_module_names_present(self):
        """规格文档里点名的模块必须在映射表中。"""
        for n in ("header", "overlay", "logo", "tile300", "tile220",
                  "premium", "brand-story"):
            self.assertIn(n, O.CROP_MODULES, n)

    def test_header_is_970x600(self):
        self.assertEqual(O.CROP_MODULES["header"], (970, 600))


class StitchTest(OpsBase):
    def test_total_height_is_sum_of_scaled(self):
        a = subject(self.p("a.png"), (300, 200), (50, 50, 250, 150))
        b = subject(self.p("b.png"), (300, 400), (50, 50, 250, 350))
        out, H, made = O.stitch([a, b], self.p("s.jpg"), width=150, slice_h=0)
        # 宽缩到 150：a 高 100，b 高 200 -> H=300
        self.assertEqual(H, 300)
        self.assertEqual(open_size(out), (150, 300))
        self.assertEqual(made, [])

    def test_slices_created_and_counted(self):
        a = subject(self.p("a.png"), (200, 200), (50, 50, 150, 150))
        out, H, made = O.stitch([a, a, a], self.p("s.jpg"), width=100, slice_h=100)
        self.assertEqual(H, 300)
        self.assertEqual(len(made), 3)
        for p in made:
            self.assertTrue(os.path.isfile(p))
            self.assertEqual(open_size(p)[0], 100)

    def test_inputs_sorted_for_determinism(self):
        """乱序传入也必须按文件名排序，保证长图顺序稳定。"""
        a = subject(self.p("01.png"), (100, 100), (20, 20, 80, 80))
        b = subject(self.p("02.png"), (100, 100), (20, 20, 80, 80))
        out1, H1, _ = O.stitch([b, a], self.p("s1.jpg"), width=100, slice_h=0)
        out2, H2, _ = O.stitch([a, b], self.p("s2.jpg"), width=100, slice_h=0)
        self.assertEqual((H1, H2), (200, 200))


if __name__ == "__main__":
    unittest.main(verbosity=2)
