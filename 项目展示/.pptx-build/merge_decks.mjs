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

// PowerPoint expands several long Chinese headings and can obscure the header
// when exporting. Preserve the meaning with compact titles that render
// consistently in both PowerPoint and artifact-tool.
const compactFeatureTitles = new Map([
  [1, "从入口到任务：科研模式统一配置"],
  [3, "文献与证据：结论来源可追溯"],
  [5, "实验闭环：从代码到结果"],
]);
for (const slideIndex of [1, 3, 5]) {
  const titleElement = appendedSlides[slideIndex].elements.find(
    (element) => element.name === "academic-9-title",
  );
  if (titleElement?.textStyle?.autoFit) {
    delete titleElement.textStyle.autoFit;
  }
}
for (const [slideIndex, title] of compactFeatureTitles) {
  const titleElement = appendedSlides[slideIndex].elements.find(
    (element) => element.name === "academic-9-title",
  );
  if (!titleElement?.paragraphs?.[0]?.runs?.[0]) {
    throw new Error(
      `Unable to locate the feature slide ${slideIndex + 1} title element`,
    );
  }
  titleElement.paragraphs[0].runs[0].text = title;
  for (const run of titleElement.paragraphs[0].runs.slice(1)) {
    run.text = "";
  }
}

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
