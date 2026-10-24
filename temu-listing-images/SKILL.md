---
name: temu-listing-images
description: "电商商品套图一站式 SOP，以 Temu 全托管为主、兼容 Amazon/淘宝天猫/Shopee/Lazada/TikTok Shop/小红书/拼多多/京东/抖店：锁定产品身份，按各平台规则出套图（白底主图、卖点图、场景图、细节图、尺寸图、多角度图、模特图、A+ 模块、Banner、详情长图、SKU 变体图），并用内置 CLI 校验修复比例、尺寸、白底、主体占比、文件体积与残留文字水印。当用户提到 Temu、全托管、核价、备货、商品套图、上架图、白底图、SKU 图、主图、A+、详情页、小红书封面时使用。"
---

# 电商商品套图 · Listing Images

一张实拍图进，一套可直接上架的图出。**Temu 全托管为主**，其余平台共用同一套流程与工具链。

## 铁律 · 比例

| 场景 | 比例 |
|---|---|
| **Temu 全部图**（主图/卖点/场景/细节/尺寸/多角度/SKU） | **强制 1:1 正方形**，无一例外 |
| Amazon 主图与副图 | 1:1 |
| 淘宝天猫主图 | 1:1，详情长图 750 宽 |
| Shopee / Lazada / TikTok Shop | 1:1 或 3:4 |
| 小红书封面 | 3:4 |
| Banner / A+ 模块 | 各自固定尺寸，见参考文件 |

**Temu 的 1:1 是硬要求**：出图参数固定 1:1，生成后必须跑 `timg check`，不过就 `timg fix`。原图非 1:1 的先 fix 再进流程。其他平台按上表各自比例，不要一律套 1:1。

## 参考文件

按需读取，不要一次全加载：

| 文件 | 内容 |
|---|---|
| `references/platform-specs.md` | **全部平台**的尺寸、比例、占比、体积、张数、禁用项 |
| `references/prompt-templates.md` | **全部资产类型**的提示词模板与变体 |

## Step 0 · 收料

缺任何一项先问，不要自己编：

| 项目 | 说明 |
|---|---|
| 产品实拍图 | 正面必备；建议加侧面、背面、顶部、Logo 特写 |
| 商品名 | 中/英，用于文件名与文案 |
| 类目 | 决定是否要尺码表、模特图 |
| 已核实事实 | 尺寸、材质、容量、颜色、配件、认证——**只用手上的** |
| 变体清单 | 颜色/尺码，用于 SKU 图 |
| 目标平台与站点 | 决定比例、尺寸、文案语种 |

## Step 1 · 产品身份锁

任何 prompt 之前先写锁，并**逐字**贴进每一条 prompt：

```text
PRODUCT IDENTITY LOCK (do not change):
- Shape & proportions: <形状、比例，如 矮胖圆柱，高约 1.6 倍直径>
- Colour & finish: <颜色与质感，带色值>
- Logo & printed text: <原文拼写、字体、位置、颜色>
- Parts & details: <盖子、接缝、接口、标签、随箱配件>
- Must NOT appear: <多余配件、额外 Logo、未经确认的卖点>
```

规则：只写看得见或用户确认过的事实。不知道的宁可不写，绝不编参数、编认证。

**关键**：用参考图裁切时先确认轮廓是否完整。**参考图缺了顶部或底部，AI 会自由补全，形状必然跑偏**——必须先向用户索取完整视角的照片。

## Step 2 · 活动风格锁

```text
CAMPAIGN STYLE LOCK:
- Palette: <主色 + 单一强调色>
- Light: <光线方向与质感>
- Background family: <纯白 / 浅灰 / 场景基调>
- Type: <字体气质>
- Mood: <调性>
```

同一套图里每条 prompt 都附同一段风格锁，这是全店视觉统一的前提。

## Step 3 · 套图结构

### Temu（默认 8 张，全 1:1）

| # | 用途 | 做法 |
|---|---|---|
| 1 | 白底主图 | 文生图 → `relayout` 校正 |
| 2 | 卖点图 A | `timg compose`（复用主图像素） |
| 3 | 场景图 | 文生图 |
| 4 | 细节图 | 文生图微距 |
| 5 | 卖点图 B | `timg compose` |
| 6 | 尺寸图 | 文生图 或 HTML 渲染（数字只来自用户） |
| 7 | 多角度图 | 真实多视角素材 |
| 8 | SKU 变体图 | `batch` 或 `compose` |

服饰类：3 换模特上身，6 换尺码表。

### Amazon（7 图 + A+）

白底主图 → 卖点图 → 场景图 → 第二卖点/对比 → 尺寸图 → 细节/多角度 → 使用场景或全家福；另出 A+ 模块组。

### 淘宝天猫

5 张主图 800×800（白底/场景首图、2–4 卖点、5 白底供搜索）+ 750 宽详情长图（8 屏）。

### Shopee / Lazada / TikTok Shop

1 张主图（白底或干净场景）+ 4–8 张卖点/场景 + 大促 Banner。

### 小红书

3 个 3:4 封面变体 + 3–6 张内页。

## Step 4 · 出图策略（重要）

**AI 生成带文字或双物体的图，会显著降低产品还原度。** 按这个顺序选：

1. **纯产品白底图** → 文生图，出完用 `relayout` 强制校正比例
2. **卖点图 / 变体图 / 尺寸标注** → **用 `compose` 复用主图产品像素，只加文字层**。产品 100% 不漂移
3. **多角度图** → 优先真实多视角实拍。让 AI 一张图画两个角度，实测会出现部件悬空、比例偏离、顶部误画成敞口
4. **Banner / 详情长图** → 先出无文字底图，文字后期合成，比让模型直接写字稳

不要用镜像复制冒充多角度，那会让人误以为有左右两版产品。

## Step 5 · 工具链

CLI 在 `scripts/timg.py`，依赖 `pillow` `numpy`。

```bash
# 质检（单图或整个目录）
python scripts/timg.py check out/

# 强制修成 1:1 合规
python scripts/timg.py fix raw/*.jpg --out-dir fixed/

# 按目标比例与占比重排（保产品像素，只重排画布）
python scripts/timg.py relayout in.png out.jpg --ratio 1.71 --coverage 0.78 --strip-corner

# 卖点图：复用主图产品，只叠文字与引线
python scripts/timg.py compose main.jpg out.jpg \
  --headline "See Through. Never Guess." \
  --subhead "Frosted body shows the water level" --anchor body

# 整目录批量出卖点图
python scripts/timg.py batch in/ out/ --headline "H" --subhead "S"

# 拼网格 / 裁平台固定尺寸 / 拼详情长图并切片
python scripts/timg.py grid a.jpg b.jpg c.jpg --cols 3 --out g.jpg
python scripts/timg.py crop src.png --module premium
python scripts/timg.py stitch s1.png s2.png --width 750
```

`--anchor body` 引线指向壶身弧面，`--anchor spigot` 指向底部旋盖。坐标按产品实际边界定位，不靠目测。

### 规格校验与回归测试

改过 `references/platform-specs.md` 或 `spec_audit.py` 之后，跑一次确认没改坏：

```bash
python scripts/spec_audit.py            # 只列问题，退出码 0=通过
python tests/run_all.py                 # 一键回归：规格校验 + 测试 + 图片质检
```

`tests/test_spec_audit.py` 共 13 个用例，分四组：基线（真实文档必须零失败）、变异检测（故意改坏必须报错）、误报防护（4 种历史误判不得复现）、设计取舍（只删体积行仍通过，因张数兜底）。

图片质检依赖 `TEMU_SAMPLE_DIR`。**未设置或目录不存在时以退出码 2 失败**，不会静默跳过：

```bash
# Linux / macOS
TEMU_SAMPLE_DIR=/path/to/deliver python tests/run_all.py

# Windows CMD
set TEMU_SAMPLE_DIR=D:\path	o\deliver && python testsun_all.py

# Windows PowerShell
$env:TEMU_SAMPLE_DIR = 'D:\path	o\deliver'; python testsun_all.py
```

本地临时调试可显式降级（CI 中禁止使用）：

```bash
python tests/run_all.py --allow-missing-sample
```

退出码：`0` 全通过 / `1` 有检查不通过 / `2` 配置缺失。

**CI**：`.github/workflows/skill-regression.yml`。Ubuntu 与 Windows、Python 3.10/3.12 矩阵跑完整回归；
`config-guard` 作业专门断言「未设变量→2」「目录不存在→2」「显式降级→0」，
防止有人把默认值改回静默跳过。仓库内无真实样例时，CI 会生成确定性合成图供质检链路自测。

`crop --module` 支持 A+ 全部模块：header / overlay / logo / tile300 / tile220 / sidebar-main / sidebar / comparison / brand-story / premium / premium-mobile。

## Step 6 · 质检

```bash
python scripts/timg.py check out/ --min-coverage 0.70 --max-coverage 0.85
```

| 检查 | 通过标准 |
|---|---|
| aspect_ratio | 宽高差 ≤2% |
| size | 长边 ≥800 |
| format | JPG/PNG |
| file_size | ≤2MB |
| coverage | 0.70–0.85（白底主图类） |
| risk | 主体框外无游离非白像素（文字/水印残留） |

脚本只量几何，画面还要人眼过三遍：

1. **形态**：有无变形、比例失调、结构被改
2. **细节**：100% 放大看纹理、边缘、反光；金属别变塑料
3. **合规**：无乱码文字、无错误标识、颜色与实物一致、变体对应正确

**图文不符是硬伤**：画面里是塑料就别写 Metal，没实测就别标容量，不能证明就别写"最/第一/国家级"。

## Step 7 · 交付

```
<platform>-<slug>/
  01-main.jpg
  02-benefit-a.jpg
  03-scene.jpg
  04-detail.jpg
  05-benefit-b.jpg
  06-size.jpg
  07-angles.jpg
  08-sku-<color>.jpg
  prompts.md      # 每条最终 prompt + 身份锁 + 风格锁
  qa-report.md    # 质检表 + 迭代记录 + 未完成项
```

交付前把 `qa-report.md` 给用户看，**未完成项要明说原因**，不要含糊带过。

## 常见返工原因

| 现象 | 原因 | 处理 |
|---|---|---|
| 比例总画不准 | 参考图轮廓不完整，AI 自由补全 | 索取完整视角照片；用 `relayout` 强制校正 |
| 图被裁成非 1:1 | 出图传了别的比例 | Temu 固定 1:1，出完必跑 check |
| 产品越画越不像 | 重复 re-render 漂移 | 改用 `compose` 复用主图像素 |
| 顶部被画成敞口 | prompt 未强制闭合 | 明确写 closed / rounded shoulder |
| 背景像贴纸 | 缺光影描述 | 补光源方向、接触阴影 |
| 主图被驳回 | 有中文、水印、边框 | 看 check 的 risk 项 |
| 两张图风格不一 | 没带风格锁 | 每条 prompt 都附完整风格锁 |
| 文件超限 | 直接输出未压缩 | `fix` 或降质量到 90 |
| 多角度图像同一张 | 用了镜像复制 | 改用真实多视角素材 |
