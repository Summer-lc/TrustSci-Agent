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
  "从入口到任务：科研模式统一配置",
  "三栏协同：过程、结果与论文同屏联动",
  "文献与证据：结论来源可追溯",
  "假设与基线：多视角评审，明确可信边界",
  "实验闭环：从代码到结果",
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
  if (index >= 9 && !slideSnapshot.ndjson.includes("[Sources]")) {
    throw new Error(`Slide ${index + 1} is missing source notes`);
  }
  if (
    index >= 9 &&
    !slideSnapshot.ndjson.includes(`"text":"${index + 1}"`)
  ) {
    throw new Error(`Slide ${index + 1} is missing its visible page number`);
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

await fs.writeFile(
  path.join(renderDir, "render-manifest.json"),
  JSON.stringify(
    {
      slideCount: 16,
      slides: expectedTitles.map((title, index) => ({
        slide: index + 1,
        title,
        preview: `slide-${String(index + 1).padStart(2, "0")}.png`,
      })),
    },
    null,
    2,
  ),
  "utf8",
);

console.log(JSON.stringify({ slideCount: 16, renderDir }, null, 2));
