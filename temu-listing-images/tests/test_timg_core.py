#!/usr/bin/env python3
"""timg_core.py 的回归测试：读图、白底检测、判定、保存。

此前 spec_audit 之外的脚本零测试覆盖，这里补上核心层。
所有样例图在运行时合成，不依赖 TEMU_SAMPLE_DIR，也不入库（见 .gitignore）。

跑法：
    python tests/test_timg_core.py
    python -m unittest discover -s tests -v
"""
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(SKILL, "scripts"))

from PIL import Image  # noqa: E402

import timg_core as C  # noqa: E402


def make_image(path, size, boxes, bg=(255, 255, 255), quality=95):
    """在纯色底上画若干实心矩形，返回路径。boxes 为 (x0, y0, x1, y1) 列表。"""
    im = Image.new("RGB", size, bg)
    for box in boxes:
        im.paste((0, 0, 0), box)
    if path.lower().endswith(".png"):
        im.save(path)
    else:
        im.save(path, quality=quality)
    return path


class BBoxTest(unittest.TestCase):
    def test_empty_mask_returns_none(self):
        self.assertIsNone(C.bbox(C.mask_of(_gray(100))))

    def test_single_pixel_mask(self):
        mask = C.mask_of(_gray(100))
        mask[10, 20] = True
        self.assertEqual(C.bbox(mask), (20, 10, 21, 11))

    def test_bbox_is_exclusive_on_far_edge(self):
        mask = C.mask_of(_gray(100))
        mask[10:30, 20:40] = True  # 20x20 方块
        x0, y0, x1, y1 = C.bbox(mask)
        self.assertEqual((x1 - x0, y1 - y0), (20, 20))
        self.assertEqual(C.bbox(mask), (20, 10, 40, 30))


def _gray(n):
    import numpy as np
    return np.full((n, n), 255, dtype="uint8")


class AnalyseTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def _p(self, name):
        return os.path.join(self.d, name)

    def test_square_flag_tolerance(self):
        """宽高差 2% 以内算正方形，超出则不算。"""
        near = make_image(self._p("near.png"), (1000, 1020), [(300, 300, 700, 700)])
        far = make_image(self._p("far.png"), (1000, 1060), [(300, 300, 700, 700)])
        self.assertTrue(C.analyse(near)["square"])
        self.assertFalse(C.analyse(far)["square"])

    def test_aspect_label(self):
        sq = make_image(self._p("sq.png"), (800, 800), [(200, 200, 600, 600)])
        rc = make_image(self._p("rc.png"), (1200, 800), [(300, 150, 900, 650)])
        self.assertEqual(C.analyse(sq)["aspect"], "1:1")
        self.assertEqual(C.analyse(rc)["aspect"], "1200x800")

    def test_pure_white_has_zero_coverage(self):
        p = make_image(self._p("w.png"), (1000, 1000), [])
        r = C.analyse(p)
        self.assertEqual(r["coverage"], 0.0)
        self.assertEqual(r["white_border"], 1.0)

    def test_coverage_matches_geometry(self):
        """占位 60% 边长的居中主体，coverage 应约等于 0.60。"""
        p = make_image(self._p("c.png"), (1000, 1000), [(200, 200, 800, 800)])
        self.assertAlmostEqual(C.analyse(p)["coverage"], 0.60, places=2)

    def test_colored_subject_counted_as_foreground(self):
        """彩色主体必须被算作前景——白底检测走灰度通道，不能只认黑色。"""
        p = self._p("col.jpg")
        im = Image.new("RGB", (1000, 1000), (255, 255, 255))
        im.paste((0, 180, 255), (250, 250, 750, 750))  # 亮蓝色，RGB 均值不低
        im.save(p, quality=95)
        r = C.analyse(p)
        self.assertAlmostEqual(r["coverage"], 0.50, places=2)
        self.assertEqual(r["white_border"], 1.0)

    def test_format_detected(self):
        png = make_image(self._p("f.png"), (600, 600), [(100, 100, 500, 500)])
        jpg = make_image(self._p("f.jpg"), (600, 600), [(100, 100, 500, 500)])
        self.assertEqual(C.analyse(png)["format"], "PNG")
        self.assertEqual(C.analyse(jpg)["format"], "JPEG")

    def test_mb_reported(self):
        p = make_image(self._p("m.png"), (600, 600), [(100, 100, 500, 500)])
        expect = round(os.path.getsize(p) / (1024 * 1024), 2)
        self.assertEqual(C.analyse(p)["mb"], expect)


class RiskDetectionTest(unittest.TestCase):
    """水印/残留检测。

    注意：本组用例记录了 analyse() 里 risk 判定当前的实际行为。
    bbox 由全掩码投影得出，因此「主体框外」的像素其实现已落在框内，
    outside 恒为 0，risk 永远不触发。见 test_risk_* 的注释。
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def _p(self, name):
        return os.path.join(self.d, name)

    def test_risk_false_for_clean_subject(self):
        p = make_image(self._p("ok.jpg"), (1000, 1000), [(350, 350, 650, 650)])
        self.assertFalse(C.analyse(p)["risk"])

    def test_risk_false_when_stray_mark_outside_subject(self):
        """主体之外的小残留——当前实现检测不到（已知缺陷，见 KNOWN DEFECT）。"""
        p = make_image(self._p("stray.jpg"), (1000, 1000),
                       [(350, 350, 650, 650), (40, 40, 120, 120)])
        self.assertFalse(C.analyse(p)["risk"])

    def test_risk_never_set_when_no_border_white(self):
        """满幅非白图没有白边，risk 分支本就不进入。"""
        p = make_image(self._p("full.jpg"), (400, 400), [(0, 0, 400, 400)])
        r = C.analyse(p)
        self.assertEqual(r["white_border"], 0.0)
        self.assertFalse(r["risk"])


class JudgeTest(unittest.TestCase):
    BASE = {"file": "x.jpg", "format": "JPEG", "width": 1000, "height": 1000,
            "square": True, "aspect": "1:1", "longest": 1000,
            "white_border": 1.0, "coverage": 0.78, "mb": 1.0, "risk": False}

    def _res(self, **kw):
        r = dict(self.BASE)
        r.update(kw)
        return r

    def _map(self, checks):
        return {c["check"]: c["pass"] for c in checks}

    def test_all_pass_on_ideal(self):
        m = self._map(C.judge(self._res()))
        self.assertTrue(all(m.values()), m)

    def test_all_five_checks_emitted(self):
        names = [c["check"] for c in C.judge(self._res())]
        self.assertEqual(names, ["aspect_ratio", "size", "format",
                                 "file_size", "coverage"])

    def test_non_square_fails_aspect(self):
        m = self._map(C.judge(self._res(square=False, aspect="1200x800",
                                       width=1200, longest=1200)))
        self.assertFalse(m["aspect_ratio"])

    def test_small_image_fails_size(self):
        self.assertFalse(self._map(C.judge(self._res(longest=799)))["size"])
        self.assertTrue(self._map(C.judge(self._res(longest=800)))["size"])

    def test_webp_fails_format(self):
        self.assertFalse(self._map(C.judge(self._res(format="WEBP")))["format"])

    def test_png_and_jpeg_pass_format(self):
        for f in ("PNG", "JPEG", "JPG"):
            self.assertTrue(self._map(C.judge(self._res(format=f)))["format"], f)

    def test_oversize_file_fails(self):
        self.assertFalse(self._map(C.judge(self._res(mb=2.01)))["file_size"])
        self.assertTrue(self._map(C.judge(self._res(mb=2.0)))["file_size"])

    def test_coverage_bounds_inclusive(self):
        m = self._map(C.judge(self._res(coverage=0.70)))
        self.assertTrue(m["coverage"])
        m = self._map(C.judge(self._res(coverage=0.85)))
        self.assertTrue(m["coverage"])
        self.assertFalse(self._map(C.judge(self._res(coverage=0.699)))["coverage"])
        self.assertFalse(self._map(C.judge(self._res(coverage=0.851)))["coverage"])

    def test_risk_adds_extra_failing_check(self):
        checks = C.judge(self._res(risk=True))
        self.assertEqual(checks[-1]["check"], "risk")
        self.assertFalse(checks[-1]["pass"])

    def test_thresholds_overridable(self):
        m = self._map(C.judge(self._res(coverage=0.95), max_cov=0.99))
        self.assertTrue(m["coverage"])


class SaveTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def _p(self, name):
        return os.path.join(self.d, name)

    def test_png_kept_as_png(self):
        out = C.save(Image.new("RGB", (200, 200), (255, 0, 0)), self._p("a.png"))
        with Image.open(out) as im:
            self.assertEqual(im.format, "PNG")

    def test_jpeg_written(self):
        out = C.save(Image.new("RGB", (200, 200), (255, 0, 0)), self._p("a.jpg"))
        with Image.open(out) as im:
            self.assertEqual(im.format, "JPEG")
            self.assertEqual(im.size, (200, 200))

    def test_quality_floor_is_60(self):
        """体积压不下去时会停在 q=60 收手，不再无意义降质。

        用高频噪声图构造「压不下去」的场景：即使 q=60 仍超限，
        也必须正常返回文件而不是死循环。
        """
        from PIL import Image as I
        noisy = I.effect_noise((600, 600), 120).convert("RGB")
        out = self._p("noise.jpg")
        C.save(noisy, out, max_mb=0.0001)
        self.assertTrue(os.path.isfile(out))
        self.assertGreater(os.path.getsize(out), 0)


class ImagesAtTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_single_file_returned_as_is(self):
        p = os.path.join(self.d, "one.jpg")
        make_image(p, (100, 100), [(10, 10, 90, 90)])
        self.assertEqual(C.images_at(p), [p])

    def test_directory_filters_by_extension(self):
        # .gif/.txt 不属受支持格式，必须被 images_at 过滤掉
        for n in ("a.jpg", "b.JPEG", "c.png", "d.webp", "e.gif"):
            Image.new("RGB", (50, 50), (255, 255, 255)).save(os.path.join(self.d, n))
        with open(os.path.join(self.d, "f.txt"), "w", encoding="utf-8") as f:
            f.write("not an image")
        got = [os.path.basename(x) for x in C.images_at(self.d)]
        self.assertEqual(sorted(got), ["a.jpg", "b.JPEG", "c.png", "d.webp"])

    def test_directory_result_is_sorted(self):
        for n in ("c.png", "a.png", "b.png"):
            Image.new("RGB", (50, 50), (255, 255, 255)).save(os.path.join(self.d, n))
        got = [os.path.basename(x) for x in C.images_at(self.d)]
        self.assertEqual(got, ["a.png", "b.png", "c.png"])

    def test_empty_directory_returns_empty(self):
        self.assertEqual(C.images_at(self.d), [])


class CheckOneTest(unittest.TestCase):
    """check_one 的三种输出形态。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = self.tmp.name
        self.p = os.path.join(self.d, "s.png")
        make_image(self.p, (1000, 1000), [(183, 183, 817, 817)])  # 覆盖率约 0.63

    def tearDown(self):
        self.tmp.cleanup()

    def _args(self, **kw):
        import argparse
        base = dict(min_size=800, min_coverage=0.60, max_coverage=0.90,
                    max_mb=2.0, tolerance=3, json=False, quiet=False)
        base.update(kw)
        return argparse.Namespace(**base)

    def test_json_output_is_parseable(self):
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ok = C.check_one(self.p, self._args(json=True))
        data = json.loads(buf.getvalue())
        self.assertTrue(ok)
        self.assertTrue(data["pass"])
        self.assertIn("result", data)
        self.assertIn("checks", data)

    def test_quiet_suppresses_pass_output(self):
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            C.check_one(self.p, self._args(quiet=True))
        self.assertEqual(buf.getvalue(), "")

    def test_quiet_still_reports_failure(self):
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ok = C.check_one(self.p, self._args(quiet=True, max_coverage=0.10))
        self.assertFalse(ok)
        self.assertIn("FAIL", buf.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
