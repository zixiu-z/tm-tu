#!/usr/bin/env python3
"""spec_audit — 校验 platform-specs.md 的平台覆盖与尺寸/比例自洽性。

不是检查图片，而是检查规格文档本身：
  1. 必需平台是否齐全
  2. 每个平台是否给出比例或尺寸
  3. 数值是否自洽（宽高比是否等于声明比例、阈值是否在合理区间）
  4. 体积/张数等硬性约束是否存在

  python spec_audit.py [--json] [--strict]

退出码 0 全部通过；1 有缺失或矛盾。
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SPEC = os.path.join(HERE, "..", "references", "platform-specs.md")

# 平台 -> 必须出现的关键词（任一命中即视为覆盖）
REQUIRED = {
    "Temu": ["Temu"],
    "Amazon": ["Amazon"],
    "淘宝/天猫": ["淘宝", "天猫"],
    "拼多多": ["拼多多"],
    "京东": ["京东"],
    "抖店": ["抖店", "抖音"],
    "Shopee": ["Shopee"],
    "Lazada": ["Lazada"],
    "TikTok Shop": ["TikTok"],
    "小红书": ["小红书"],
    "Shopify": ["Shopify"],
    "Walmart": ["Walmart"],
    "eBay": ["eBay"],
}

# 每个平台必须能读出「比例」或「尺寸」之一，否则判定为规格不完整
NEEDS_DIMENSION = [
    "Temu", "Amazon", "淘宝", "Shopee", "Lazada", "TikTok",
    "小红书", "拼多多", "京东", "抖店", "Shopify",
]

SIZE_RE = re.compile(r"(\d{2,5})\s*[×x]\s*(\d{2,5})")
RATIO_RE = re.compile(r"(?<!\d)(1\s*:\s*1|3\s*:\s*4|4\s*:\s*5|9\s*:\s*16|16\s*:\s*9|3\s*:\s*1|4\s*:\s*3|5\s*:\s*6|2\s*:\s*3)")
WIDTH_RE = re.compile(r"(\d{2,5})\s*px", re.I)
MB_RE = re.compile(r"(\d+(?:\.\d+)?)\s*MB", re.I)
COUNT_RE = re.compile(r"(\d+)\s*张")


def parse_ratio(r):
    a, b = [float(x) for x in r.replace(" ", "").split(":")]
    return a / b


def sections(text):
    """按 '## ' 切分，返回 {标题: 正文}。"""
    out, cur, buf = {}, None, []
    for line in text.splitlines():
        if line.startswith("## "):
            if cur is not None:
                out[cur] = "\n".join(buf)
            cur, buf = line[3:].strip(), []
        elif cur is not None:
            buf.append(line)
    if cur is not None:
        out[cur] = "\n".join(buf)
    return out


def find_section(secs, keyword):
    for title, body in secs.items():
        if keyword.lower() in title.lower():
            return title, body
    # 关键词可能只出现在正文里
    for title, body in secs.items():
        if keyword.lower() in body.lower():
            return title, body
    return None, ""


def audit(path, strict=False):
    text = open(path, encoding="utf-8").read()
    secs = sections(text)
    findings = []

    # 1) 平台覆盖
    for platform, keys in REQUIRED.items():
        hit = any(k in text for k in keys)
        findings.append({
            "check": "platform_present", "target": platform,
            "pass": hit, "detail": "命中" if hit else "文档中未提及",
        })

    # 2) 每个平台是否有比例或尺寸
    for p in NEEDS_DIMENSION:
        title, body = find_section(secs, p)
        has_size = bool(SIZE_RE.search(body))
        has_ratio = bool(RATIO_RE.search(body))
        has_width = bool(WIDTH_RE.search(body))
        ok = has_size or has_ratio or has_width
        parts = []
        if has_size:
            parts.append(f"宽高{len(SIZE_RE.findall(body))}处")
        if has_ratio:
            parts.append(f"比例{len(RATIO_RE.findall(body))}处")
        if has_width:
            parts.append(f"宽度{len(WIDTH_RE.findall(body))}处")
        findings.append({
            "check": "has_dimension", "target": p, "pass": ok,
            "detail": "、".join(parts) if ok else "既无尺寸也无比例",
        })

    # 3) 尺寸与声明比例是否自洽
    for line in text.splitlines():
        # 一行里列了多个尺寸（不同资产），比例无法一一对应，跳过
        if len(SIZE_RE.findall(line)) > 1:
            continue
        # 「生成后裁切」的源尺寸不要求符合最终比例
        if "裁" in line or "crop" in line.lower():
            continue
        for m in SIZE_RE.finditer(line):
            w, h = int(m.group(1)), int(m.group(2))
            if w < 100 or h < 100:
                continue
            ratios = RATIO_RE.findall(line)
            if not ratios:
                continue
            actual = w / h
            ok = any(abs(actual - parse_ratio(r)) / parse_ratio(r) <= 0.06
                     for r in ratios)
            findings.append({
                "check": "ratio_consistency", "target": f"{w}x{h}",
                "pass": ok,
                "detail": (f"宽高比 {actual:.3f} 与同表声明的 {ratios[0]} 一致"
                           if ok else
                           f"宽高比 {actual:.3f} 与同行声明的 {ratios} 不符"),
            })

    # 4) 硬性约束存在性
    for label, rx in (("体积上限", MB_RE), ("张数要求", COUNT_RE)):
        hit = bool(rx.search(text))
        findings.append({
            "check": "constraint_present", "target": label,
            "pass": hit, "detail": "已声明" if hit else "未声明",
        })

    # 5) 结构性检查
    for p in ("Temu", "Amazon"):
        title, body = find_section(secs, p)
        has_cov = "%" in body or "占比" in body
        findings.append({
            "check": "coverage_rule", "target": p,
            "pass": has_cov, "detail": "有主体占比规则" if has_cov else "缺主体占比规则",
        })

    # 6) Temu 必须强制 1:1（本 Skill 的核心约束，不能被改掉）
    _, temu = find_section(secs, "Temu")
    square = ("1:1" in temu.replace(" ", "")) and ("强制" in temu or "无一例外" in temu)
    findings.append({
        "check": "temu_square_mandate", "target": "Temu 1:1",
        "pass": square,
        "detail": "强制 1:1 已声明" if square else "未声明强制 1:1",
    })

    # 7) A+ 关键模块尺寸必须准确
    A_PLUS = {"标准图文页眉": (970, 600), "标准公司 Logo": (600, 180),
              "品牌故事背景": (1464, 625), "Premium A+ 全幅": (1464, 600)}
    _, aplus = find_section(secs, "A+")
    for label, (ew, eh) in A_PLUS.items():
        line = next((l for l in aplus.splitlines() if label in l), "")
        m = SIZE_RE.search(line)
        got = (int(m.group(1)), int(m.group(2))) if m else None
        findings.append({
            "check": "aplus_size", "target": label,
            "pass": got == (ew, eh),
            "detail": (f"{got[0]}x{got[1]} 正确" if got == (ew, eh)
                       else f"期望 {ew}x{eh}，实际 {got}"),
        })

    # 8) 有独立规格表的平台，各自区块内都应有体积或张数约束
    for p in ("Temu", "Amazon"):
        _, body = find_section(secs, p)
        has = bool(MB_RE.search(body) or COUNT_RE.search(body))
        findings.append({
            "check": "size_limit_per_platform", "target": p,
            "pass": has,
            "detail": "区块内有体积/张数约束" if has else "区块内缺体积与张数约束",
        })

    failed = [f for f in findings if not f["pass"]]
    return findings, failed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", default=DEFAULT_SPEC)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args()

    if not os.path.isfile(a.spec):
        print(f"找不到规格文件: {a.spec}")
        return 2

    findings, failed = audit(a.spec, a.strict)
    if a.json:
        print(json.dumps({"findings": findings, "failed": len(failed)},
                         ensure_ascii=False, indent=2))
        return 0 if not failed else 1

    print(f"规格文件: {os.path.basename(a.spec)}")
    print(f"检查项: {len(findings)}\n")
    for f in findings:
        mark = "PASS" if f["pass"] else "FAIL"
        if f["pass"] and not a.strict:
            continue
        print(f'  [{mark}] {f["check"]:20s} {f["target"]:14s} {f["detail"]}')

    print(f'\n通过 {len(findings) - len(failed)}/{len(findings)}')
    if failed:
        print("存在问题:")
        for f in failed:
            print(f'  - {f["target"]}: {f["detail"]}')
        return 1
    print("全部通过：平台覆盖与尺寸比例自洽")
    return 0


if __name__ == "__main__":
    sys.exit(main())
