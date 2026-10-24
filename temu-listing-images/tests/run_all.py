#!/usr/bin/env python3
"""一键回归：规格文档校验 + 校验器测试 + 图片质检。

    python tests/run_all.py
    TEMU_SAMPLE_DIR=/path/to/images python tests/run_all.py

图片质检依赖 TEMU_SAMPLE_DIR。**未设置或目录不存在时默认失败**，避免 CI 里
静默跳过一道防线。本地临时调试可用 --allow-missing-sample 显式降级。

退出码：
    0  全部通过
    1  有检查不通过
    2  配置缺失（TEMU_SAMPLE_DIR 未设置或目录不存在）
"""
import argparse
import os
import subprocess
import sys

def _utf8_stdout():
    """Windows 控制台默认 cp1252，输出中文会 UnicodeEncodeError。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


_utf8_stdout()

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)


def step(name, cmd, cwd=None):
    print(f"\n{'=' * 56}\n{name}\n{'=' * 56}")
    r = subprocess.run(cmd, cwd=cwd or SKILL)
    ok = r.returncode == 0
    print(f"-> {'PASS' if ok else 'FAIL'} ({name})")
    return ok


def resolve_sample(allow_missing):
    """返回 (目录或 None, 退出码或 None)。"""
    raw = os.environ.get("TEMU_SAMPLE_DIR", "").strip()
    if not raw:
        msg = ("未设置环境变量 TEMU_SAMPLE_DIR。\n"
               "  图片质检无法进行——这是三道防线之一，不允许静默跳过。\n"
               "  Linux/macOS:  export TEMU_SAMPLE_DIR=/path/to/images\n"
               "  Windows CMD:  set TEMU_SAMPLE_DIR=D:\\path\\to\\images\n"
               "  Windows PS:   $env:TEMU_SAMPLE_DIR = 'D:\\path\\to\\images'\n"
               "  仅本地临时调试可加 --allow-missing-sample 降级。")
        if allow_missing:
            print(f"\n[WARN] {msg}")
            print("[WARN] 已按 --allow-missing-sample 降级，本次结果不覆盖图片质检。")
            return None, None
        print(f"\n[FAIL] {msg}", file=sys.stderr)
        return None, 2

    if not os.path.isdir(raw):
        msg = f"TEMU_SAMPLE_DIR 指向的目录不存在: {raw}"
        if allow_missing:
            print(f"\n[WARN] {msg}")
            print("[WARN] 已按 --allow-missing-sample 降级。")
            return None, None
        print(f"\n[FAIL] {msg}", file=sys.stderr)
        return None, 2

    images = [f for f in os.listdir(raw)
              if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))]
    if not images:
        msg = f"TEMU_SAMPLE_DIR 目录内没有图片: {raw}"
        if allow_missing:
            print(f"\n[WARN] {msg}")
            return None, None
        print(f"\n[FAIL] {msg}", file=sys.stderr)
        return None, 2

    print(f"\n[INFO] 图片样例目录: {raw}（{len(images)} 张）")
    return raw, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--allow-missing-sample", action="store_true",
                    help="TEMU_SAMPLE_DIR 缺失时降级为跳过（仅本地调试）")
    args = ap.parse_args()

    print("[INFO] 1/3 规格文档校验")
    results = [step("1/3 规格文档校验",
                    [sys.executable, "scripts/spec_audit.py"])]

    print("\n[INFO] 2/3 校验器回归测试")
    results.append(step("2/3 校验器回归测试",
                        [sys.executable, "tests/test_spec_audit.py"]))

    print("\n[INFO] 3/3 图片质检")
    sample, code = resolve_sample(args.allow_missing_sample)
    if code is not None:
        print(f"\n{'-' * 56}\n汇总：配置缺失，管线中止（退出码 {code}）")
        return code
    if sample is None:
        print("\n[跳过] 3/3 图片质检")
    else:
        results.append(step("3/3 图片质检（示例批次）",
                            [sys.executable, "scripts/timg.py", "check", sample,
                             "--min-coverage", "0", "--max-coverage", "1"]))

    total, passed = len(results), sum(results)
    print(f"\n{'-' * 56}\n汇总：{passed}/{total} 环节通过")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
