# 在其他设备上使用

仓库：https://github.com/zixiu-z/tm-tu

Skill 的发现依赖**目录位置**，不是仓库本身。所以“克隆下来”和“能被 Agent 调用”是两件事。
下面按用途分三种方式，按需选。

---

## 方式一 · 只跑 CLI（最快，任何设备）

不需要 Agent，不需要 Skill 机制，只要能跑 Python。

```bash
git clone https://github.com/zixiu-z/tm-tu.git
cd tm-tu/temu-listing-images

pip install pillow numpy
```

先自检：

```bash
python scripts/spec_audit.py          # 规格文档校验，应为 39/39
python tests/run_all.py               # 应为退出码 2（缺样例目录，这是预期）
```

正常使用：

```bash
# 质检一批图
python scripts/timg.py check /path/to/images

# 修成 1:1 合规
python scripts/timg.py fix raw/*.jpg --out-dir fixed/

# 按目标比例与占比重排
python scripts/timg.py relayout in.png out.jpg --ratio 1.71 --coverage 0.78

# 卖出点图（复用主图产品像素，只叠文字）
python scripts/timg.py compose main.jpg out.jpg \
  --headline "See Through. Never Guess." \
  --subhead "Frosted body shows the water level" --anchor body

# 完整回归（需指定样例目录）
TEMU_SAMPLE_DIR=/path/to/images python tests/run_all.py
```

Windows CMD 用 `set TEMU_SAMPLE_DIR=D:\path`，PowerShell 用
`$env:TEMU_SAMPLE_DIR = 'D:\path'`。

---

## 方式二 · 装进 Agent（让 AI 自动调用）

把 `SKILL.md` 放到对应 Agent 的 skill 目录，Agent 才会在你提到
「Temu 套图 / 白底主图 / 商品图」时自动加载。

各运行时的常见位置：

| 运行时 | 目录 |
|---|---|
| Claude Code | `~/.claude/skills/` |
| Codex | `~/.agents/skills/` 或 `~/.codex/skills/` |
| Cursor（项目内） | `.cursor/skills/` |
| GitHub Copilot | `.github/skills/` |
| 小浣熊 Desktop | `~/.office-raccoon/agent/skills/` |

**关键：拷的是 `temu-listing-images` 整个文件夹，不是仓库根。**
`references/` 和 `scripts/` 是相对路径引用的，分开放会找不到。

### macOS / Linux

```bash
git clone https://github.com/zixiu-z/tm-tu.git
cp -r tm-tu/temu-listing-images ~/.claude/skills/     # 换成你的目录
```

### Windows PowerShell

```powershell
git clone https://github.com/zixiu-z/tm-tu.git
Copy-Item -Recurse tm-tu\temu-listing-images "$env:USERPROFILE\.claude\skills\"
```

装完重启 Agent。验证：让它读一次 Skill 列表，应出现 `temu-listing-images`。

---

## 方式三 · 多设备同步（改一处，处处生效）

`cp` 的问题是**以后更新要手动重拷**。想自动跟进，用符号链接指向 clone 出来的目录：

### macOS / Linux

```bash
git clone https://github.com/zixiu-z/tm-tu.git ~/code/tm-tu
ln -s ~/code/tm-tu/temu-listing-images ~/.claude/skills/temu-listing-images
```

### Windows（管理员 PowerShell）

```powershell
git clone https://github.com/zixiu-z/tm-tu.git $env:USERPROFILE\code\tm-tu
New-Item -ItemType SymbolicLink `
  -Path "$env:USERPROFILE\.claude\skills\temu-listing-images" `
  -Target "$env:USERPROFILE\code\tm-tu\temu-listing-images"
```

之后在 `~/code/tm-tu` 里 `git pull`，所有装了软链的设备自动生效。

---

## 跨设备改完怎么同步回去

```bash
cd tm-tu
git pull                       # 先拉，避免分叉
# 改 references/ 或 scripts/
python -m unittest discover -s temu-listing-images/tests   # 本地先过一遍
git add -A && git commit -m "docs: 补充 XX 平台规格"
git push
```

推上去后 CI 会自动跑（Ubuntu/Windows × Py3.10/3.12 + config-guard）。
**CI 全绿再算完成**，红色就去 Actions 页面看是哪个作业挂的。

首次在**新设备**推送需要认证：GitHub 只能用 PAT 或 SSH，密码推送早已不支持。

```bash
# SSH 方式（推荐，一次配置长期可用）
ssh-keygen -t ed25519 -C "your@email"
# 把 ~/.ssh/id_ed25519.pub 内容贴到 GitHub → Settings → SSH and GPG keys
git remote set-url origin git@github.com:zixiu-z/tm-tu.git
```

---

## 注意事项

### 1. 仓库目前是 Public

我查过了，现在是**公开仓库**。里面有你的平台规格整理、提示词库和工具链。
若不想公开，去 Settings → General → Danger Zone → Change visibility → Private。
转私有后，别的设备克隆需要登录，CI 不受影响。

### 2. CI 的合成图不等于真实图

CI 用现场生成的合成图，只证明**质检链路可用**。
真实商品图合不合规，必须本地用 `TEMU_SAMPLE_DIR` 指向实际交付目录跑：

```bash
TEMU_SAMPLE_DIR=/path/to/deliver python tests/run_all.py
```

三道环节全过才算数。

### 3. 退出码约定

| 码 | 含义 | 常见原因 |
|---|---|---|
| 0 | 全部通过 | — |
| 1 | 检查不通过 | 图片比例/占比/体积不合规，或规格文档有缺失 |
| 2 | 配置缺失 | `TEMU_SAMPLE_DIR` 未设、目录不存在或没有图片 |

退出码 2 **不是**“通过”。脚本故意不静默跳过，本地调试要降级得显式加
`--allow-missing-sample`。

### 4. 本机代理

原设备上 `github.com:443` 直连被重置，配了 `http.proxy=127.0.0.1:7890`。
新设备如果克隆失败，先测：

```bash
curl -s -o /dev/null -w "%{http_code}\n" --max-time 8 https://github.com
```

返回 `000` 就是网络层不通，按本机代理情况配 `git config --global http.proxy`。

### 5. Python 编码

脚本已内置 UTF-8 reconfigure，Windows 控制台输出中文不会再崩。
若仍遇 `UnicodeEncodeError`，设 `PYTHONIOENCODING=utf-8`。
