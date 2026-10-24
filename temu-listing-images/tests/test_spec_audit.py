#!/usr/bin/env python3
"""spec_audit.py 的回归测试。

三道防线，任一失败即说明校验器出了问题：

  1. 基线      —— 真实 platform-specs.md 必须零失败
  2. 变异检测  —— 故意改坏文档，校验器必须报错，且报对地方
  3. 误报防护  —— 曾经误判过的 4 种合理写法，不得再被判为失败

跑法：
    python tests/test_spec_audit.py
    python -m unittest discover -s tests -v
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
AUDIT = os.path.join(SKILL, "scripts", "spec_audit.py")
SPEC = os.path.join(SKILL, "references", "platform-specs.md")

REQUIRED_PLATFORMS = [
    "Temu", "Amazon", "淘宝/天猫", "拼多多", "京东", "抖店",
    "Shopee", "Lazada", "TikTok Shop", "小红书", "Shopify",
    "Walmart", "eBay",
]


def run_audit(spec_text, as_json=False):
    """把规格文本写入临时文件，跑一次校验，返回 (exit_code, stdout)。"""
    fd, path = tempfile.mkstemp(suffix=".md", text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(spec_text)
        cmd = [sys.executable, AUDIT, "--spec", path]
        if as_json:
            cmd.append("--json")
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        return r.returncode, r.stdout
    finally:
        os.unlink(path)


class SpecAuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(SPEC, encoding="utf-8") as f:
            cls.base = f.read()

    # ---------- 1. 基线 ----------

    def test_real_spec_passes(self):
        """真实规格文件必须零失败。"""
        rc, out = run_audit(self.base, as_json=True)
        data = json.loads(out)
        failed = [f for f in data["findings"] if not f["pass"]]
        self.assertEqual(rc, 0, f"真实规格不应失败：{failed}")
        self.assertEqual(data["failed"], 0)

    def test_all_platforms_detected(self):
        """13 个平台都必须被识别为已覆盖。"""
        rc, out = run_audit(self.base, as_json=True)
        data = json.loads(out)
        found = {f["target"] for f in data["findings"]
                 if f["check"] == "platform_present" and f["pass"]}
        missing = [p for p in REQUIRED_PLATFORMS if p not in found]
        self.assertEqual(missing, [], f"未识别到平台：{missing}")

    def test_core_checks_present(self):
        """关键检查项必须都在，防止有人删检查逻辑。"""
        rc, out = run_audit(self.base, as_json=True)
        names = {f["check"] for f in json.loads(out)["findings"]}
        expected = {
            "platform_present", "has_dimension", "ratio_consistency",
            "constraint_present", "coverage_rule", "temu_square_mandate",
            "aplus_size", "size_limit_per_platform",
        }
        self.assertEqual(expected - names, set(), f"缺少检查项：{expected - names}")

    # ---------- 2. 变异检测 ----------

    def assert_fails_with(self, mutated, keyword):
        """断言校验失败，且失败项里出现指定关键词。"""
        rc, out = run_audit(mutated)
        self.assertEqual(rc, 1, f"应当报错但通过了。输出：{out}")
        failures = [l for l in out.splitlines() if l.strip().startswith("- ")]
        self.assertTrue(
            any(keyword in l for l in failures),
            f"失败项里没有「{keyword}」，实际失败：{failures}")

    def test_detects_missing_platform(self):
        """删掉小红书整节 → 必须发现平台缺失。"""
        mutated = re.sub(r"## 六、小红书.*?(?=## 七、)", "", self.base, flags=re.S)
        self.assertNotEqual(mutated, self.base, "变异未生效")
        self.assert_fails_with(mutated, "小红书")

    def test_detects_temu_ratio_broken(self):
        """Temu 的强制 1:1 被改成 2:3 → 必须报错。"""
        mutated = self.base.replace(
            "**1:1 正方形（强制，无一例外）**", "**2:3**")
        self.assertNotEqual(mutated, self.base, "变异未生效")
        self.assert_fails_with(mutated, "Temu 1:1")

    def test_detects_wrong_aplus_size(self):
        """A+ 页眉 970×600 被改成 970×300 → 必须报错。"""
        mutated = self.base.replace(
            "| 标准图文页眉 | 970 × 600 |", "| 标准图文页眉 | 970 × 300 |")
        self.assertNotEqual(mutated, self.base, "变异未生效")
        self.assert_fails_with(mutated, "标准图文页眉")

    def test_detects_temu_constraints_gone(self):
        """同时删掉 Temu 的体积与张数行 → 必须报错。"""
        i = self.base.index("## 二、Amazon")
        seg, rest = self.base[:i], self.base[i:]
        seg = re.sub(r"\| 体积 \|[^\n]*\n", "", seg)
        seg = re.sub(r"\| 张数 \|[^\n]*\n", "", seg)
        seg = seg.replace("（以后台为准，部分类目 ≤3MB）", "")
        mutated = seg + rest
        self.assertNotEqual(mutated, self.base, "变异未生效")
        self.assert_fails_with(mutated, "区块内缺体积与张数")

    def test_detects_dimension_removal(self):
        """把某平台的尺寸与比例全部抹掉 → 必须报错。"""
        i = self.base.index("## 七、Shopify")
        j = self.base.index("## 八、")
        seg = self.base[i:j]
        stripped = re.sub(r"\d+\s*[×x]\s*\d+", "", seg)
        stripped = re.sub(r"\d+\s*:\s*\d+", "", stripped)
        mutated = self.base[:i] + stripped + self.base[j:]
        self.assertNotEqual(mutated, self.base, "变异未生效")
        self.assert_fails_with(mutated, "Shopify")

    # ---------- 3. 误报防护（历史上真正踩过的 4 个坑） ----------

    def test_no_false_positive_multi_asset_row(self):
        """一行列多个资产（Banner + 1:1 轮播）不得被判为比例矛盾。"""
        rc, out = run_audit(self.base)
        self.assertNotIn("2000x600", out)

    def test_no_false_positive_crop_source_size(self):
        """「出 1024×1536 再裁」是源尺寸，不得要求它符合最终比例。"""
        rc, out = run_audit(self.base)
        self.assertNotIn("1024x1536", out)

    def test_no_false_positive_aplus_neighbour_ratio(self):
        """A+ 的 970×600 不得因邻近表格的 1:1 而被误判。"""
        rc, out = run_audit(self.base)
        self.assertNotIn("970x600", out)

    def test_no_false_positive_width_only_platform(self):
        """拼多多/京东/抖店只约定宽度，不得报缺尺寸。"""
        rc, out = run_audit(self.base)
        for p in ("拼多多", "京东", "抖店"):
            self.assertNotIn(f"- {p}:", out)

    # ---------- 4. 设计取舍：有意保留的宽松点 ----------

    def test_volume_only_removal_still_passes(self):
        """只删体积行时仍通过——因为张数约束等价兜底，这是有意为之。"""
        i = self.base.index("## 二、Amazon")
        seg, rest = self.base[:i], self.base[i:]
        mutated = re.sub(r"\| 体积 \|[^\n]*\n", "", seg) + rest
        self.assertNotEqual(mutated, self.base, "变异未生效")
        rc, out = run_audit(mutated)
        self.assertEqual(rc, 0, f"只删体积行应仍通过（张数兜底），实际：{out}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
