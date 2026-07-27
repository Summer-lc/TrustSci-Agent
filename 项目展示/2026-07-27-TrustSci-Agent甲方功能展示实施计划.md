# TrustSci-Agent 甲方功能展示 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将原 9 页项目展示模板与现有 7 页 TrustSci-Agent 功能展示草稿合并为一份可直接面向甲方演示的 16 页 PowerPoint。

**Architecture:** 使用 `@oai/artifact-tool` 分别导入两份 PPTX，保留原模板的母版、版式和第 1–9 页，并将功能草稿的第 1–7 页作为最终第 10–16 页追加。合并时重命名功能草稿的页面 ID 和媒体 ID，避免两个独立 PPTX 的内部编号冲突；随后逐页渲染、检查并输出安全副本，避免覆盖当前可能正在 PowerPoint 中打开的 7 页草稿。

**Tech Stack:** Node.js ES modules、`@oai/artifact-tool`、PowerPoint Open XML、PowerShell 只读校验

---

## 文件边界

- 只读：`项目展示/项目展示.pptx`，9 页原模板。
- 只读：`项目展示/项目展示_TrustSci-Agent甲方功能展示.pptx`，7 页功能草稿。
- 创建：`项目展示/.pptx-build/merge_decks.mjs`，负责安全合并和导出。
- 创建：`项目展示/.pptx-build/verify_deck.mjs`，负责页数、顺序、文字、渲染和占位内容校验。
- 创建：`项目展示/.pptx-build/template-frame-map.json`，记录最终 16 页与两份来源文件的映射。
- 创建：`项目展示/.pptx-build/template-audit.txt`、`deviation-log.txt`、`source-notes.txt`，记录模板约束、偏差和素材来源。
- 创建：`项目展示/.pptx-build/final-render/`，保存最终逐页 PNG 和布局 JSON。
- 输出：优先写入 `项目展示/项目展示_TrustSci-Agent甲方功能展示.pptx`；若该文件被占用，写入 `项目展示/项目展示_TrustSci-Agent甲方功能展示_完整16页版.pptx`。

### Task 1: 建立模板与页面映射

**Files:**
- Read: `项目展示/项目展示.pptx`
- Read: `项目展示/项目展示_TrustSci-Agent甲方功能展示.pptx`
- Create: `项目展示/.pptx-build/template-frame-map.json`
- Create: `项目展示/.pptx-build/template-audit.txt`
- Create: `项目展示/.pptx-build/deviation-log.txt`
- Create: `项目展示/.pptx-build/source-notes.txt`

- [ ] **Step 1: 使用模板检查器渲染并检查原 9 页**

Run:

```powershell
& $node "$skill\template_following_scripts\inspect_template_deck.mjs" `
  --workspace "$build\base-inspect" `
  --pptx "$showcase\项目展示.pptx"
```

Expected: 输出 9 张源页面 PNG、9 份布局 JSON 和一份模板清单。

- [ ] **Step 2: 使用模板检查器渲染并检查 7 页功能草稿**

Run:

```powershell
& $node "$skill\template_following_scripts\inspect_template_deck.mjs" `
  --workspace "$build\feature-inspect" `
  --pptx "$showcase\项目展示_TrustSci-Agent甲方功能展示.pptx"
```

Expected: 输出 7 张功能页面 PNG、7 份布局 JSON 和一份模板清单。

- [ ] **Step 3: 写入完整页面映射**

`template-frame-map.json` 写入：

```json
{
  "outputSlides": [
    {"outputSlide": 1, "sourceDeck": "项目展示.pptx", "sourceSlide": 1, "narrativeRole": "原模板封面", "reuseMode": "duplicate-slide", "editTargets": []},
    {"outputSlide": 2, "sourceDeck": "项目展示.pptx", "sourceSlide": 2, "narrativeRole": "原模板学生端问答", "reuseMode": "duplicate-slide", "editTargets": []},
    {"outputSlide": 3, "sourceDeck": "项目展示.pptx", "sourceSlide": 3, "narrativeRole": "原模板个性化学习", "reuseMode": "duplicate-slide", "editTargets": []},
    {"outputSlide": 4, "sourceDeck": "项目展示.pptx", "sourceSlide": 4, "narrativeRole": "原模板作业反馈", "reuseMode": "duplicate-slide", "editTargets": []},
    {"outputSlide": 5, "sourceDeck": "项目展示.pptx", "sourceSlide": 5, "narrativeRole": "原模板课程知识库", "reuseMode": "duplicate-slide", "editTargets": []},
    {"outputSlide": 6, "sourceDeck": "项目展示.pptx", "sourceSlide": 6, "narrativeRole": "原模板作业管理", "reuseMode": "duplicate-slide", "editTargets": []},
    {"outputSlide": 7, "sourceDeck": "项目展示.pptx", "sourceSlide": 7, "narrativeRole": "原模板学情监测", "reuseMode": "duplicate-slide", "editTargets": []},
    {"outputSlide": 8, "sourceDeck": "项目展示.pptx", "sourceSlide": 8, "narrativeRole": "原模板平台管理", "reuseMode": "duplicate-slide", "editTargets": []},
    {"outputSlide": 9, "sourceDeck": "项目展示.pptx", "sourceSlide": 9, "narrativeRole": "原模板成果总结", "reuseMode": "duplicate-slide", "editTargets": []},
    {"outputSlide": 10, "sourceDeck": "项目展示_TrustSci-Agent甲方功能展示.pptx", "sourceSlide": 1, "narrativeRole": "TrustSci-Agent 功能概览", "reuseMode": "duplicate-slide", "editTargets": []},
    {"outputSlide": 11, "sourceDeck": "项目展示_TrustSci-Agent甲方功能展示.pptx", "sourceSlide": 2, "narrativeRole": "任务入口与科研模式", "reuseMode": "duplicate-slide", "editTargets": []},
    {"outputSlide": 12, "sourceDeck": "项目展示_TrustSci-Agent甲方功能展示.pptx", "sourceSlide": 3, "narrativeRole": "三栏科研工作台", "reuseMode": "duplicate-slide", "editTargets": []},
    {"outputSlide": 13, "sourceDeck": "项目展示_TrustSci-Agent甲方功能展示.pptx", "sourceSlide": 4, "narrativeRole": "文献检索与证据链", "reuseMode": "duplicate-slide", "editTargets": []},
    {"outputSlide": 14, "sourceDeck": "项目展示_TrustSci-Agent甲方功能展示.pptx", "sourceSlide": 5, "narrativeRole": "假设评审与可信基线", "reuseMode": "duplicate-slide", "editTargets": []},
    {"outputSlide": 15, "sourceDeck": "项目展示_TrustSci-Agent甲方功能展示.pptx", "sourceSlide": 6, "narrativeRole": "代码实验与反馈闭环", "reuseMode": "duplicate-slide", "editTargets": []},
    {"outputSlide": 16, "sourceDeck": "项目展示_TrustSci-Agent甲方功能展示.pptx", "sourceSlide": 7, "narrativeRole": "报告审计与成果交付", "reuseMode": "duplicate-slide", "editTargets": []}
  ],
  "omittedSourceSlides": []
}
```

- [ ] **Step 4: 写入模板审计、偏差和来源说明**

`template-audit.txt` 写入：

```text
页面尺寸：960 × 540 pt，16:9。
原模板页数：9；功能草稿页数：7；最终页数：16。
母版：/ppt/slideMasters/slideMaster1.xml。
版式：/ppt/slideLayouts/slideLayout1.xml 至 slideLayout12.xml，两份来源一致。
继承规则：第 1–9 页保持原模板；第 10–16 页保持功能草稿。
视觉规则：白底、深蓝标题、亮蓝强调、左上蓝色方块、顶部细线、右上校徽、右下连续页码。
文字规则：不改写可见文案，不缩小字体，不覆盖模板元素。
```

`deviation-log.txt` 写入：

```text
唯一偏差：最终文件由两份同源 PPTX 合并。
技术处理：重命名功能草稿的页面 ID 和非重复媒体 ID，避免 Open XML 内部冲突。
可见影响：无。页面内容、位置、字体、颜色、母版和版式保持不变。
```

`source-notes.txt` 写入：

```text
第 1–9 页来源：项目展示/项目展示.pptx。
第 10–16 页来源：项目展示/项目展示_TrustSci-Agent甲方功能展示.pptx。
功能页截图来源：项目展示/界面截图/ 下的本地 TrustSci-Agent 真实系统界面。
功能说明依据：项目 README.md、当前本地实现和演示数据。
未使用网络素材、外部图片或模板旧业务内容生成新增页面。
```

- [ ] **Step 5: 自检映射**

Run:

```powershell
Get-Content -LiteralPath "$build\template-frame-map.json" -Encoding utf8 |
  ConvertFrom-Json |
  Select-Object -ExpandProperty outputSlides |
  Measure-Object
```

Expected: `Count : 16`。

### Task 2: 先写合并结果校验

**Files:**
- Create: `项目展示/.pptx-build/verify_deck.mjs`

- [ ] **Step 1: 创建失败优先的校验脚本**

```javascript
import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const [candidatePath, renderDir] = process.argv.slice(2);
if (!candidatePath || !renderDir) {
  throw new Error("Usage: node verify_deck.mjs <candidate.pptx> <render-dir>");
}

const expectedTitles = [
  "校级项目成果汇报",
  "多源知识问答",
  "个性化学习",
  "作业与反馈",
  "课程知识库",
  "作业管理闭环",
  "学情监测与知识图谱",
  "平台运行管理",
  "项目已形成覆盖",
  "TrustSci-Agent：可验证 AI Scientist 科研工作台",
  "从入口到任务：三类科研模式统一配置",
  "三栏协同：过程、结果与论文同屏联动",
  "文献与证据：每项结论都能追溯到来源",
  "假设与基线：多视角评审，明确可信边界",
  "实验闭环：从代码生成到结果判断与重设计",
  "报告与交付：审计、导出、工作区一并留档",
];

const candidate = await PresentationFile.importPptx(
  await FileBlob.load(candidatePath),
);
if (candidate.slides.items.length !== 16) {
  throw new Error(`Expected 16 slides, got ${candidate.slides.items.length}`);
}

const snapshot = await candidate.inspect({
  kind: "slide,textbox,shape,image,notes,layout",
  maxChars: 100000,
});
await fs.mkdir(renderDir, { recursive: true });
await fs.writeFile(
  path.join(renderDir, "final-inspect.ndjson"),
  `${snapshot.ndjson}\n`,
  "utf8",
);

for (const [index, title] of expectedTitles.entries()) {
  const slide = candidate.slides.items[index];
  const slideSnapshot = await candidate.inspect({
    kind: "slide,textbox,shape,image,notes",
    target: { id: `sl/${slide.id}`, beforeLines: 0, afterLines: 200 },
    maxChars: 20000,
  });
  if (!slideSnapshot.ndjson.includes(title)) {
    throw new Error(`Slide ${index + 1} is missing expected text: ${title}`);
  }
  if (/lorem|ipsum|TODO|TBD|Click to add|单击此处添加/i.test(slideSnapshot.ndjson)) {
    throw new Error(`Slide ${index + 1} contains unresolved placeholder text`);
  }

  const stem = `slide-${String(index + 1).padStart(2, "0")}`;
  const png = await candidate.export({ slide, format: "png", scale: 2 });
  await fs.writeFile(
    path.join(renderDir, `${stem}.png`),
    new Uint8Array(await png.arrayBuffer()),
  );
  const layout = await slide.export({ format: "layout" });
  await fs.writeFile(
    path.join(renderDir, `${stem}.layout.json`),
    await layout.text(),
    "utf8",
  );
}

const montage = await candidate.export({
  format: "webp",
  montage: true,
  scale: 1,
});
await fs.writeFile(
  path.join(renderDir, "final-montage.webp"),
  new Uint8Array(await montage.arrayBuffer()),
);

console.log(JSON.stringify({ slideCount: 16, renderDir }, null, 2));
```

- [ ] **Step 2: 在成品尚未生成时运行校验**

Run:

```powershell
& $node "$build\verify_deck.mjs" "$build\candidate-16.pptx" "$build\final-render"
```

Expected: FAIL，提示候选文件不存在。

### Task 3: 实现无损合并

**Files:**
- Create: `项目展示/.pptx-build/merge_decks.mjs`
- Create: `项目展示/.pptx-build/candidate-16.pptx`

- [ ] **Step 1: 创建合并脚本**

```javascript
import fs from "node:fs/promises";
import path from "node:path";
import { createHash } from "node:crypto";
import {
  FileBlob,
  Presentation,
  PresentationFile,
} from "@oai/artifact-tool";

const [basePath, featurePath, outputPath] = process.argv.slice(2);
if (!basePath || !featurePath || !outputPath) {
  throw new Error(
    "Usage: node merge_decks.mjs <base.pptx> <feature.pptx> <output.pptx>",
  );
}

function replaceStringRefs(value, replacements) {
  if (Array.isArray(value)) {
    return value.map((item) => replaceStringRefs(item, replacements));
  }
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([key, item]) => [
        key,
        replaceStringRefs(item, replacements),
      ]),
    );
  }
  if (typeof value === "string" && replacements.has(value)) {
    return replacements.get(value);
  }
  return value;
}

function hashImage(image) {
  return createHash("sha256")
    .update(Buffer.from(Object.values(image.data ?? {})))
    .digest("hex");
}

const base = await PresentationFile.importPptx(await FileBlob.load(basePath));
const feature = await PresentationFile.importPptx(
  await FileBlob.load(featurePath),
);
if (base.slides.items.length !== 9) {
  throw new Error(`Expected 9 base slides, got ${base.slides.items.length}`);
}
if (feature.slides.items.length !== 7) {
  throw new Error(
    `Expected 7 feature slides, got ${feature.slides.items.length}`,
  );
}

const baseProto = base.toProto();
const featureProto = feature.toProto();
const baseLayoutIds = baseProto.layouts.map((layout) => layout.id).sort();
const featureLayoutIds = featureProto.layouts.map((layout) => layout.id).sort();
if (JSON.stringify(baseLayoutIds) !== JSON.stringify(featureLayoutIds)) {
  throw new Error("The two decks do not share the same master/layout hierarchy");
}

const usedImageIds = new Set(baseProto.images.map((image) => image.id));
const baseHashes = new Map(
  baseProto.images.map((image) => [hashImage(image), image.id]),
);
const imageReplacements = new Map();
const appendedImages = [];

for (const [index, image] of featureProto.images.entries()) {
  const identicalBaseId = baseHashes.get(hashImage(image));
  if (identicalBaseId) {
    imageReplacements.set(image.id, identicalBaseId);
    continue;
  }
  const extension = path.extname(image.id) || ".bin";
  let nextId = `/ppt/media/trustsci-${String(index + 1).padStart(2, "0")}${extension}`;
  let suffix = 1;
  while (usedImageIds.has(nextId)) {
    nextId = `/ppt/media/trustsci-${String(index + 1).padStart(2, "0")}-${suffix}${extension}`;
    suffix += 1;
  }
  usedImageIds.add(nextId);
  imageReplacements.set(image.id, nextId);
  appendedImages.push({ ...structuredClone(image), id: nextId });
}

const appendedSlides = featureProto.slides.map((sourceSlide, index) => {
  const slide = replaceStringRefs(
    structuredClone(sourceSlide),
    imageReplacements,
  );
  slide.id = `trustsci-slide-${index + 10}`;
  slide.creationId = `trustsci-creation-${index + 10}`;
  slide.index = index + 9;
  return slide;
});

const combinedProto = structuredClone(baseProto);
combinedProto.slides = [
  ...structuredClone(baseProto.slides),
  ...appendedSlides,
];
combinedProto.images = [
  ...structuredClone(baseProto.images),
  ...appendedImages,
];

const combined = Presentation.load(combinedProto);
const sourceNotes = [
  "本地 TrustSci-Agent 科研工作台截图：界面截图/03-科研工作台.png",
  "本地系统入口与任务配置截图：界面截图/01-系统入口.png；界面截图/02-任务配置.png",
  "本地 TrustSci-Agent 科研工作台截图：界面截图/03-科研工作台.png",
  "本地文献、引用与证据截图：界面截图/04a-文献与论文.png；界面截图/04b-引用与证据.png",
  "本地假设竞技与可信基线截图：界面截图/05a-假设竞技.png；界面截图/05b-可信基线.png",
  "本地实验计划、代码、结果与反馈截图：界面截图/06a-实验计划与代码.png；界面截图/06b-实验结果与反馈.png",
  "本地报告审计与工作区截图：界面截图/07a-报告审计.png；界面截图/07b-报告与工作区.png",
];
for (const [index, source] of sourceNotes.entries()) {
  combined.slides.items[index + 9].speakerNotes.textFrame.setText(
    `[Sources]\n- ${source}\n- 项目功能依据：README.md 与本地当前实现`,
  );
}

await fs.mkdir(path.dirname(outputPath), { recursive: true });
const pptx = await PresentationFile.exportPptx(combined);
await pptx.save(outputPath);
console.log(
  JSON.stringify({
    outputPath,
    slideCount: combined.slides.items.length,
    appendedImageCount: appendedImages.length,
  }),
);
```

- [ ] **Step 2: 运行合并脚本**

Run:

```powershell
& $node "$build\merge_decks.mjs" `
  "$showcase\项目展示.pptx" `
  "$showcase\项目展示_TrustSci-Agent甲方功能展示.pptx" `
  "$build\candidate-16.pptx"
```

Expected: `slideCount` 为 16，输出文件非空。

- [ ] **Step 3: 运行校验并生成全部预览**

Run:

```powershell
& $node "$build\verify_deck.mjs" "$build\candidate-16.pptx" "$build\final-render"
```

Expected: PASS，生成 16 张 PNG、16 份布局 JSON、检查快照和总览图。

### Task 4: 逐页视觉校验与修复

**Files:**
- Read: `项目展示/.pptx-build/final-render/slide-01.png` 至 `slide-16.png`
- Modify: `项目展示/.pptx-build/merge_decks.mjs`，仅在发现问题时修改
- Recreate: `项目展示/.pptx-build/candidate-16.pptx`

- [ ] **Step 1: 逐页检查全部 16 张 PNG**

检查重叠、裁切、标题换行、低对比度、截图模糊、页码中断、校徽缺失、异常空白、模板占位文本和左右边距。

- [ ] **Step 2: 检查布局越界**

Run:

```powershell
& $python "$skill\container_tools\slides_test.py" "$build\candidate-16.pptx"
```

Expected: 不存在未解释的画布外元素。

- [ ] **Step 3: 检查结构化空占位符**

Run:

```powershell
Add-Type -AssemblyName System.IO.Compression.FileSystem
$archive = [System.IO.Compression.ZipFile]::OpenRead("$build\candidate-16.pptx")
$issues = [System.Collections.Generic.List[string]]::new()
try {
  foreach ($entry in $archive.Entries) {
    if ($entry.FullName -notmatch '^ppt/slides/slide\d+\.xml$') { continue }
    $reader = [System.IO.StreamReader]::new($entry.Open())
    try { $xml = $reader.ReadToEnd() } finally { $reader.Dispose() }
    foreach ($shape in [regex]::Matches($xml, '(?s)<p:sp>.*?</p:sp>')) {
      if ($shape.Value -match '<p:ph\b' -and $shape.Value -notmatch '<a:t>\s*\S') {
        $issues.Add("$($entry.FullName): empty structural placeholder")
      }
    }
    if ($xml -match 'Slide Number|Click to add|单击此处添加|>Date<|>Footer<') {
      $issues.Add("$($entry.FullName): visible placeholder prompt")
    }
  }
} finally {
  $archive.Dispose()
}
if ($issues.Count) { throw ($issues -join [Environment]::NewLine) }
```

Expected: 无错误。

- [ ] **Step 4: 至少完成一次修复—重渲染循环**

即使首次视觉效果正常，也要根据检查结果完成一轮可验证修正，例如补充来源备注、修复内部媒体冲突或调整导出文件命名；然后重新运行 Task 3 Step 2–3 并复查受影响页面。

### Task 5: 输出正式成品

**Files:**
- Create or Replace: `项目展示/项目展示_TrustSci-Agent甲方功能展示.pptx`
- Fallback Create: `项目展示/项目展示_TrustSci-Agent甲方功能展示_完整16页版.pptx`
- Create: `项目展示/成品预览_完整16页/`

- [ ] **Step 1: 判断正式文件是否被 PowerPoint 占用**

Run:

```powershell
$locked = Test-Path -LiteralPath "$showcase\~`$项目展示_TrustSci-Agent甲方功能展示.pptx"
if ($locked) {
  Copy-Item -LiteralPath "$build\candidate-16.pptx" `
    -Destination "$showcase\项目展示_TrustSci-Agent甲方功能展示_完整16页版.pptx" `
    -Force
} else {
  Copy-Item -LiteralPath "$build\candidate-16.pptx" `
    -Destination "$showcase\项目展示_TrustSci-Agent甲方功能展示.pptx" `
    -Force
}
```

- [ ] **Step 2: 复制最终预览**

Run:

```powershell
$preview = "$showcase\成品预览_完整16页"
New-Item -ItemType Directory -Path $preview -Force | Out-Null
Copy-Item -LiteralPath (Get-ChildItem -LiteralPath "$build\final-render" -Filter 'slide-*.png').FullName `
  -Destination $preview -Force
Copy-Item -LiteralPath "$build\final-render\final-montage.webp" `
  -Destination "$preview\完整16页总览.webp" -Force
```

- [ ] **Step 3: 最终验收**

重新导入交付文件并确认：

- 共有 16 页；
- 第 1–9 页与原模板顺序、文字和视觉一致；
- 第 10–16 页标题、页码和截图完整；
- 不包含占位文本、乱码、裁切或未解释的重叠；
- 文件可由 PowerPoint 正常打开；
- 所有制作相关文件均位于 `项目展示/` 下。

- [ ] **Step 4: 提交制作脚本和实施计划**

Run:

```powershell
& $git -C $repo add -- `
  "项目展示/2026-07-27-TrustSci-Agent甲方功能展示实施计划.md" `
  "项目展示/.pptx-build/merge_decks.mjs" `
  "项目展示/.pptx-build/verify_deck.mjs"
& $git -C $repo commit -m "build: assemble 16-slide client feature deck"
```

Expected: 只提交实施计划与可复现脚本，不提交日志、预览 PNG 或 PPTX 二进制文件。
