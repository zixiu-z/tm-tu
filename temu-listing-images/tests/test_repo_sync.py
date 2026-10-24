#!/usr/bin/env python3
"""仓库同步守卫：检测是否存在未提交或未推送的改动。

用途：改完 Skill 后跑一次，确认没有“只改本地、忘了推”的遗漏。

    python tests/test_repo_sync.py            # 人类可读
    python tests/test_repo_sync.py --json     # 机读

退出码：
    0  工作区干净且与远端同步
    1  有未提交或未推送的改动
    3  不是 git 仓库、无远端或无法访问远端（无法判断）
"""
import json
import os
import subprocess
import sys


def _utf8_stdout():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def git(*args, cwd=None):
    r = subprocess.run(["git", *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", cwd=cwd)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def repo_root(start=None):
    code, out, _ = git("rev-parse", "--show-toplevel", cwd=start)
    return out if code == 0 else None


def status(root):
    code, out, err = git("status", "--porcelain", cwd=root)
    if code != 0:
        return None, err
    files = [l for l in out.splitlines() if l.strip()]
    return files, ""


def upstream(root):
    code, out, _ = git("rev-parse", "--abbrev-ref", "--symbolic-full-name",
                       "@{u}", cwd=root)
    return out if code == 0 else None


def ahead_behind(root):
    code, out, _ = git("rev-list", "--left-right", "--count",
                       "HEAD...@{u}", cwd=root)
    if code != 0:
        return None
    parts = out.split()
    if len(parts) != 2:
        return None
    return int(parts[0]), int(parts[1])  # ahead, behind


def check(start=None):
    root = repo_root(start)
    if not root:
        return {"ok": False, "code": 3, "reason": "不在 git 仓库内"}

    files, err = status(root)
    if files is None:
        return {"ok": False, "code": 3, "reason": f"git status 失败: {err}"}

    up = upstream(root)
    if not up:
        return {"ok": False, "code": 3, "reason": "当前分支未设置上游远端"}

    counts = ahead_behind(root)
    if counts is None:
        return {"ok": False, "code": 3,
                "reason": "无法比较远端（可能网络不通，或需要先 fetch）"}
    ahead, behind = counts

    problems = []
    if files:
        problems.append(f"未提交改动 {len(files)} 个文件")
    if ahead:
        problems.append(f"未推送提交 {ahead} 个")

    return {
        "ok": not problems,
        "code": 0 if not problems else 1,
        "root": root,
        "upstream": up,
        "uncommitted": files,
        "ahead": ahead,
        "behind": behind,
        "problems": problems,
    }


def main():
    _utf8_stdout()
    as_json = "--json" in sys.argv
    res = check()

    if as_json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return res["code"]

    if res["code"] == 3:
        print(f"[SKIP] 无法判断：{res['reason']}")
        return 3

    if res["ok"]:
        print(f"[PASS] 工作区干净，与 {res['upstream']} 同步")
        if res["behind"]:
            print(f"       提示：落后远端 {res['behind']} 个提交，建议 git pull")
        return 0

    print("[FAIL] 存在未同步的改动：")
    for p in res["problems"]:
        print(f"  - {p}")
    for f in res["uncommitted"][:20]:
        print(f"      {f}")
    if len(res["uncommitted"]) > 20:
        print(f"      ... 其余 {len(res['uncommitted']) - 20} 个")
    print("\n处理：git add -A && git commit -m '...' && git push")
    return 1


if __name__ == "__main__":
    sys.exit(main())
