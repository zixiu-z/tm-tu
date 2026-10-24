# Agent Skills

个人 Agent Skill 集合，随附自动化回归测试。

## 目录

| Skill | 说明 |
|---|---|
| [`temu-listing-images`](temu-listing-images/) | 电商商品套图 SOP。以 Temu 全托管为主，兼容 Amazon / 淘宝天猫 / Shopee / Lazada / TikTok Shop / 小红书 / 拼多多 / 京东 / 抖店。含 CLI 校验与修复工具链。 |
| `temu-full-managed-images` | 已废弃，内容整合进 `temu-listing-images`，保留仅为兼容旧引用。 |

## temu-listing-images

### 能力

- 锁定产品身份（形状、颜色、Logo、配件）后按平台规则出套图
- 白底主图、卖点图、场景图、细节图、尺寸图、多角度图、模特图、A+ 模块、Banner、详情长图、SKU 变体图
- CLI 校验：比例、尺寸、格式、白底纯度、主体占比、文件体积、残留文字水印
- 自动修复：居中裁方、近白归一 `#FFFFFF`、按目标占比重排、超限重压

### 结构

```
temu-listing-images/
├── SKILL.md                      流程主入口
├── references/
│   ├── platform-specs.md         13 个平台的尺寸与比例
│   └── prompt-templates.md       16 个提示词模板
├── scripts/
│   ├── timg.py                   CLI 入口
│   ├── timg_core.py              读图、测量、判定、保存
│   ├── timg_ops.py               修复、重排、合成、拼图
│   └── spec_audit.py             规格文档校验
└── tests/
    ├── test_spec_audit.py        13 个用例
    └── run_all.py                一键回归
```

### 快速开始

```bash
pip install pillow numpy

cd temu-listing-images

# 规格文档校验
python scripts/spec_audit.py

# 图片质检
python scripts/timg.py check /path/to/images

# 修成 1:1 合规
python scripts/timg.py fix raw/*.jpg --out-dir fixed/

# 完整回归（需先指定样例目录）
TEMU_SAMPLE_DIR=/path/to/images python tests/run_all.py
```

### 退出码约定

| 码 | 含义 |
|---|---|
| 0 | 全部通过 |
| 1 | 有检查不通过 |
| 2 | 配置缺失（`TEMU_SAMPLE_DIR` 未设置或目录不存在） |

图片质检环节**不会静默跳过**。本地临时调试可加 `--allow-missing-sample` 显式降级。

## 持续集成

`.github/workflows/skill-regression.yml` 在以下情况触发：

- 改动 `temu-listing-images/` 下任何文件
- 改动 workflow 自身

包含两个作业：

1. **regression** — Ubuntu / Windows × Python 3.10 / 3.12 矩阵，跑完整回归
2. **config-guard** — 断言配置缺失时确实以退出码 2 失败，防止有人改回静默跳过

仓库内没有真实样例图时，CI 会现场生成确定性的合成图，用于验证质检链路本身可用；**真实商品图的合规性仍需在本地用 `TEMU_SAMPLE_DIR` 指向实际交付目录验证**。

## 许可

`temu-listing-images` 的提示词与规格整理改编自 [xianyu110/ecommerce-image-skills](https://github.com/xianyu110/ecommerce-image-skills)（MIT）。
