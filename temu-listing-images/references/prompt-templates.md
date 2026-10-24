# 提示词模板总库

> 每条模板前都先贴 `{IDENTITY_LOCK}`（产品身份锁），同套图再贴 `{CAMPAIGN STYLE LOCK}`。
> 例：主图用 Sunburst，场景/草稿用 Flare。文字密集的图一律 Sunburst，出完逐字核对。

## 一、白底主图（Amazon / Walmart / eBay / Shopee / Temu）

```text
Main product image.
{IDENTITY_LOCK}
Remove the original background and every object that is not the product.
Product alone, {orientation: upright | lying flat | 3/4 front view}, centered.
Pure white seamless background, #FFFFFF (RGB 255,255,255) everywhere outside the product.
Product fills about {87% | 78%} of the frame (longest side), with even margins.
Soft diffused studio lighting from front-left, very subtle natural contact shadow directly under the product,
razor-sharp edges, true-to-life colour and material.
No added text, no badges, no props, no reflections of a room, no watermark, no border. Square 1:1.
```

占比：Amazon 取 87%（要求 ≥85%）；Temu 取 78%（70–85% 区间，留呼吸空间）。

**变体**
- 含包装：`Product box placed slightly behind and to the right, both fully visible, combined group fills 87% of the frame.`
- 多件装：`Exactly {N} identical units arranged in a neat row, no other items.`
- 服装（隐形人台）：把 orientation 换成 `invisible-mannequin 3D shape, front view, neckline interior visible.`

## 二、卖点信息图

```text
Ecommerce selling-point infographic, {1:1 | 2:3}.
{IDENTITY_LOCK}
Layout: {layout from menu}. Background: {soft gradient in brand colours {hex1} → {hex2} | clean white | subtle texture}.
Headline (exact): "{HEADLINE}"
Feature rows (exact), each with a thin line icon: "{ROW 1}", "{ROW 2}", "{ROW 3}".
{Callout lines from labels to {parts}.}
Modern sans-serif typography, strong hierarchy, high contrast, generous whitespace, readable on mobile.
Premium minimal brand style. Spell all text exactly as given; no other text.
```

**版式菜单**
- **主体 + 三行**：产品占左 45%，标题 + 3 行图标在右
- **标注式**：产品居中，3–4 个标签用细线指向部位
- **对比式**：左"本品" 右"普通款"，✓/✗ 行（不出现竞品品牌）
- **数字主视觉**：一个大数字（"24H"、"1200 mAh"）+ 产品 + 一行解释

**文案规则**：先定稿再出图——1 条标题 + 最多 3 行卖点，只用用户能证明的宣称，逐字拼对，模型会原样渲染。某字母错了，把错词引号重写再生成；或出无字底图，后期在 Canva/Figma 加字。

## 三、场景图

**场景库**（选一条填占位符）

| 类别 | 场景种子 |
|---|---|
| 厨房 | 窗边大理石台面、晨光、新鲜食材、蒸汽 |
| 卫浴/美妆 | 石质洗手台、柔软毛巾、水珠、尤加利枝 |
| 桌面/数码 | 橡木书桌、笔电边缘、笔记本、暖灯、傍晚 |
| 户外 | 山径上的花岗岩 / 野餐垫 / 黄金时刻的海滩 |
| 健身 | 健身房长凳、毛巾、哑铃、冷调日光 |
| 卧室/家居 | 亚麻床品、边几、绿植、柔和午后光 |
| 节庆 | 礼盒包装、串灯、季节道具（圣诞/春节/斋月） |

```text
Lifestyle product photo for an ecommerce listing.
{IDENTITY_LOCK}
Scene: {scene seed}. {Optional person: a {age/region} {persona}'s hand reaching for / using the product — face out of frame}.
The product is the clear hero: sharp focus, about {35–55}% of the frame, realistic scale relative to {reference object}.
Lighting: {golden-hour backlight | soft window light | warm lamp}, shallow depth of field,
natural shadows that match the scene.
Photorealistic editorial brand photography, {brand mood: calm minimal | vibrant | premium}.
No added text, no extra logos. Aspect ratio {4:5 | 1:1 | 9:16}.
```

## 四、细节微距

```text
Close-up product detail photo, strictly square 1:1.
{IDENTITY_LOCK}
FRAMING: {the part} fills roughly {50–60}% of the frame, positioned slightly off-centre.
The surrounding body reads as a curved surface, not a flat box corner.
Shallow depth of field: {the part} needle sharp, edges softening away.
LIGHT: soft studio light from upper left, gentle specular sheen along the edge,
clean soft shadow under the part.
BACKGROUND: smooth light gradient white to very pale grey, empty, no props.
Premium commercial macro photography, texture detail visible,
no text, no watermark, no logo, no border.
```

## 五、尺寸 / 规格图

### 产品尺寸

```text
Clean product dimension infographic, 1:1, white background.
{IDENTITY_LOCK}
Product shown {front view} at centre, {optional: a realistic adult hand beside it for scale}.
Thin dark-grey dimension lines with arrowheads and labels (exact text):
height "{26 cm / 10.2 in}", width "{7.5 cm / 3.0 in}", {capacity "750 ml / 25 oz"}.
Labels in a clean sans-serif, small caps, perfectly legible, aligned to the lines.
Minimal technical style, no other text.
```

Amazon 需同时标 **cm 与 inch**。**数字只用用户给的**，没给的就不标。

### 服装尺码表

```text
Apparel size chart image, 3:4, light background.
Top: flat sketch of the {garment} with lettered measurement arrows A (chest), B (length), C (sleeve).
Bottom: a clean table, header row "Size | A Chest | B Length | C Sleeve" and rows exactly:
{S | 52 cm | 68 cm | 60 cm}
{M | 55 cm | 70 cm | 61 cm}
{L | 58 cm | 72 cm | 62 cm}
Note line: "Measured flat · ±2 cm". Sans-serif, high contrast. Spell numbers exactly.
```

带大量数字的表格是图像模型最难的部分。务必 Sunburst、放大逐个核对；错一个就重出，或改用 HTML/SVG 渲染表格再合成。

## 六、多角度套图

**镜头清单（默认 6 张）**
1 正面平视 · 2 前方 45° · 3 侧面 · 4 背面 · 5 俯视 · 6 细节微距（{盖/纹理/接口/Logo}）
可选：7 包装+产品 · 8 手持显尺度 · 9 拆解平铺

**套图锁**（每条都贴）

```text
SET LOCK: background {seamless light warm-grey #EDEBE8 | white #FFFFFF};
lighting {large softbox front-left 45°, white fill right, soft floor shadow};
camera {85mm, f/8, product centred, fills 80% of frame}; colour grading neutral.
```

```text
Ecommerce product photo, angle {N}/{total}: {angle description}.
{IDENTITY_LOCK}
{SET LOCK}
Show only what is physically on this side of the product;
do not move logos or text to faces where they don't exist.
Photorealistic studio photography, sharp detail, no added text. Square 1:1.
```

## 七、模特上身 / 试穿

```text
On-model ecommerce photo.
GARMENT IDENTITY LOCK: {colour, fabric texture, cut/fit, neckline, sleeve, hem,
prints, logo text and position, trims}.
Keep the garment 100% faithful; do not change colour, pattern, logo or length.
Model: {a natural-looking {region} {gender} in their {age}s, {body type}, {hair}},
wearing the garment with {styling}.
Pose: {relaxed standing, one hand in pocket | walking | seated},
{full body | three-quarter | waist-up}, {front | 3/4 | back} view.
{If pose reference: Copy pose, framing and lighting from image 2; take the garment only from image 1.}
Background: {plain light-grey studio | white | urban street | cafe}.
Soft key light, realistic fabric folds and drape.
Catalogue photography, photorealistic. No text, no watermark.
```

**伦理**：只用合成模特，不得使用真人肖像（除非用户拥有授权）；不性化；身材比例自然。卖尺码区间时至少给两种体型。

**变体**：`ghost mannequin`（隐形人体、领口内空）、`jewellery close-up`（耳/颈/手特写、微距、皮肤质感自然）、`size comparison`（同款 S 与 XL 模特并排）。

## 八、A+ 模块

**默认 5 模块故事线**：① 970×600 页眉（品牌承诺）→ ② 3×300×300 核心卖点 → ③ 970×300 场景横幅 → ④ 4×220×220 细节 → ⑤ 对比表（仅自有系列）。

```text
Amazon A+ module image, {module name}, final size {W}×{H} px
(generate at {closest supported ratio}, then crop).
{IDENTITY_LOCK}
{CAMPAIGN STYLE LOCK}
Content: {what this module must communicate}.
Composition: product {left third | centre}, {scene}, leave {right 40% | top band} clean for the headline.
{Headline (exact): "..." — or: no text, copy will be added in Seller Central.}
Photorealistic, consistent with the campaign style lock.
```

出图后按模块精确裁切：`timg crop src.png --module header`（970×600）等。

## 九、大促 Banner

**活动配色预设**

| 活动 | 配色与元素 |
|---|---|
| 双11 / 11.11 | 橙红→洋红渐变、金色箔字、彩纸屑 |
| 618 | 亮红 + 黄、粗体数字 |
| 年货节 / 春节 | 喜庆红、金、灯笼、剪纸（别堆太满） |
| 9.9 / 12.12 | 橙/青、金币、礼盒 |
| 黑五 | 黑 + 霓虹强调色、高对比 |
| Prime Day | 深蓝 + 青、干净 |
| 夏季促销 | 青→橙、冰块、水花、阳光 |

```text
Ecommerce sale banner, {ratio, e.g. 3:1 wide}, for {platform/placement}.
{IDENTITY_LOCK}
Product: {1 hero unit | 3 units, middle one larger} on {a podium | floating},
{ice splash | ribbons | light rays}.
Background: {campaign palette + motifs}.
Text (exact, nothing else): headline "{11.11 MEGA SALE}", sub "{UP TO 50% OFF}",
button "{SHOP NOW}".
Text on the {left 40%}, product on the right;
keep all text inside the central 80% safe area.
Bold commercial advertising style, punchy lighting, crisp, all text spelled exactly.
```

中文文案可用（如 `"双11 狂欢价"`、`"第二件半价"`），引号内原样照抄。**不要印你无法保证的价格**，用"低至/up to"，且需用户确认。

## 十、详情长图（淘宝/天猫/拼多多/京东/抖店）

**默认 8 屏**（与用户确认后可改）
1 首屏 hero：产品 + 核心承诺
2 痛点 → 解决方案
3–5 卖点 ×3（一屏一点）
6 使用场景（2–3 个小场景）
7 细节微距 / 材质
8 参数 + 售后规格表、包装清单、保障

**风格锁**（每屏都贴）

```text
DETAIL PAGE STYLE LOCK: palette {sage #8FA58C, cream #F4EFE6, charcoal #2B2B2B};
type {思源黑体 heavy titles, regular body}; light {soft daylight};
layout {generous margins, title top-left, product right};
mood {natural, premium, calm}.
```

```text
Taobao product detail page screen {n}/8, portrait 3:4 (will be resized to 750 px wide).
{IDENTITY_LOCK}
{STYLE LOCK}
Purpose: {screen purpose}. Visual: {composition}.
Chinese text (exact, nothing else): title "{标题}", subtitle "{副标题}"{, bullets "{…}"}.
Text large enough to read on a phone; clean layout, no clutter.
```

拼接与切片：`timg stitch out/screen-*.png --width 750`，同时产出 `-slices/`（每片 ≤1546px）。

## 十一、小红书封面

**版式**

| 版式 | 适用 |
|---|---|
| 大字报：大字 + 产品 | 新品、单一核心卖点 |
| 对比：前后分屏 | 清洁、美妆、收纳 |
| 清单：4–6 格网格 | 合集、"必买清单" |
| 测评：带评分贴纸 | 测评、对比 |
| 氛围：平铺 mood | 生活方式、送礼 |
| 价格锚点 | 促销（仅限真实价格） |

```text
Xiaohongshu note cover, 3:4 portrait.
{IDENTITY_LOCK}
Layout: {layout}. Scene: {bright airy flat-lay on cream linen with {props}
| hand holding the product on a city street | desk setup}.
Large bold Chinese headline at the top in a {rounded friendly | handwritten | heavy sans} font:
"{一整天都冰的水杯}".
Smaller tag line: "{通勤 · 健身 · 露营}". Sticker in a corner: "{亲测24h}".
Fresh cozy lifestyle aesthetic, soft natural window light, natural saturation,
slight real-photo imperfection.
All Chinese text spelled exactly, clearly legible; no other text.
```

做 3 个不同版式让用户挑，封面适合 A/B 测试。

## 十二、批量换背景 / SKU 换色

```text
# 换背景
Edit this product photo. Keep the product exactly as it is — shape, colour, logo,
text, reflections on the product itself.
Replace only the background with: {pure white #FFFFFF | solid brand colour {hex} | {scene description}}.
Match lighting direction and add a soft natural contact shadow. No other changes, no added text.
```

```text
# SKU 换色
Edit this product photo. Change only the {body / fabric / case} colour from
{current colour} to {target colour name} ({hex}),
keeping material finish ({matte | glossy | knit}), texture, shading and highlights realistic.
Do NOT change: {logo colour, lid, zipper, stitching, background}.
Same framing, no other edits.
```

换色必须同时给**确切颜色名和 hex**，并列出不可变部位（Logo、拉链、鞋底）。全量跑前先用 2 张试跑。

## 十三、出图三条通道

1. **内置生图工具**：有 `generate_image` 等工具时，把最终 prompt 和产品图作为参考直接调用（本环境走这条）
2. **API Key**：设置 `GPTIMAGE_API_KEY`（可选 `GPTIMAGE_BASE_URL`），用 OpenAI 兼容接口出图
3. **无 Key**：只输出最终 prompt + 在线运行链接，让用户自己贴
