User:
我想报名参加这个比赛，请你从核心任务的选择，如基于OpenClaw、Hermes、OpenHuman等超级智能体还是自己编程设计多智能体系统Multi-Agent Systems架构，能力项参考中的核心能力的实现思路，高科学价值的科研问题集参考，基座模型的选择（Qwen-3.7-max），是否微调，如何搭建前端、制作演示视频等角度去帮我调研一下整个比赛的完成思路，是否需要调用深度研究功能等，市面上是否已经有类似的开源项目可供参考使用或二次开发，请给我一份完整的参赛指南

GPT:
([Past chat][1])([Past chat][2])([Past chat][3])([Past chat][4])([Past chat][5])([Past chat][6])([Past chat][7])([Past chat][8])([Past chat][9])([Past chat][10])([Past chat][11])([Past chat][12])([Past chat][13])([Past chat][14])

下面这份参赛指南我按“**能拿分、能落地、能复现、能和你已有 SeisLLM/EHS 背景绑定**”来设计。我的结论先放前面：

**最推荐路线：不要直接把 OpenClaw / Hermes / OpenHuman 当成最终作品主体，而是自己编程实现一个面向地震/地球物理科研问题的 Multi-Agent AI Scientist 系统；OpenClaw/Hermes 只作为参考架构、开发辅助或演示自动化工具。**

理由很简单：这个比赛评分里，**科学价值 40 分、技术深度 30 分、应用潜力 30 分**，其中技术深度明确看“超级智能体或多智能体协作设计”和“基于多模态大模型对科学模态数据的处理成效”，作品还要求提交 PDF≤20 页、架构讲解、真实案例、源代码、上下文工程设计、可选前端和 10 分钟演示视频。直接套一个超级智能体很容易显得“工具拼装”，而自己实现科研流水线式 Multi-Agent 更容易讲清楚创新点、可复现性和领域深度。

---

## 1. 参赛项目建议定位

建议你把项目命名为类似：

**GeoSeis-Scientist：面向低信噪比地震监测的多智能体科学假设生成系统**

或者更正式一点：

**SeisHypothesis Agent：融合地震波形、地震目录与文献知识的可验证科学假设生成系统**

这个方向最适合你，因为你已经有 SeisLLM 的研究积累，懂 seismic encoder、MAP、phase picking、低 SNR、DiTing、SeisT 等内容。比赛本身鼓励结合具体自然科学领域，链接观测数据、实验数据、文献知识和历史数据库，针对异常现象识别、极端事件预测、机制挖掘、路径优化等问题生成科学假设或工程优化策略。

你的作品不要泛泛做“AI Scientist 平台”，而要做一个**垂直地球物理 AI Scientist 原型**。评委会更容易看到专业深度，而不是只看到一个聊天机器人。

---

## 2. 核心科研问题怎么选

我建议优先选下面这个主问题：

**在低信噪比地震波形场景下，能否通过文献证据、波形统计特征、台站/事件元数据联合分析，自动生成可验证的 phase picking / magnitude estimation / weak event detection 改进假设？**

这个问题好处是：

一是和你的 SeisLLM 强相关，可以自然引入“连续三分量波形与文本 token 之间存在模态鸿沟”“低 SNR 导致传统模型召回下降”“局部相位细节与全局上下文建模需要协同”等你已经熟悉的论述。

二是可以接入真实科学数据。DiTing 是面向中国区域的大规模地震基准数据集，可用于地震检测、震相拾取、震级预测、早期预警等任务；SeisBench 提供机器学习地震学工具箱和统一数据/模型接口；SeisT 是一个面向多种地震监测任务的基础深度学习模型，GitHub 仓库也提供 PhaseNet、EQTransformer 等 baseline。([EquScience][15])

三是“可验证性”比较强。你的系统可以不是只生成文字假设，而是生成一个小规模实验计划：数据集、Source/Target、baseline、metrics、实验脚本、预期结果、风险点。这正好对应比赛要求的《科学假设与研究计划》字段，包括 Problem Statement、Rationale、Technical Details、Datasets、Methods、Experiments、Results、References 等。

不建议把主问题选成“地震预测”。地震预测科学争议太大，容易被专家追问“你凭什么说可预测”。更稳妥的是选：**低信噪比弱事件检测、震相拾取泛化、事件级数据划分、台站域迁移、模型轻量化与可解释性**。这些更可落地，也更容易做实验验证。

---

## 3. 技术路线选择：超级智能体 vs 自研 Multi-Agent

### 我的推荐排序

| 方案                           | 推荐程度 | 原因                             |
| ---------------------------- | ---: | ------------------------------ |
| 自研 Multi-Agent + 百炼 Qwen API |   最高 | 最容易展示架构、源码、可复现、领域工具链、上下文工程     |
| 百炼 Agent / Workflow + 自研后端   |    高 | 符合阿里云生态，方便截图和平台合规，但复杂科研逻辑最好自己写 |
| Hermes / OpenClaw 二次开发       |    中 | 可作为灵感和辅助，但直接改它们容易偏离科研主线        |
| OpenHuman 二次开发               |   较低 | 更偏个人助理/记忆/桌面智能体，不适合科研假设生成主赛题   |

OpenClaw 是开源个人 AI 助手项目；Hermes Agent 强调自我学习、技能沉淀、长期记忆和可在云端运行；OpenHuman 则更偏向桌面个人智能体和用户上下文记忆。它们都可以参考，但它们的核心定位不是“科学假设生成”。([GitHub][16])

Hermes 的浏览器自动化、技能循环和多工具调用能力可以参考，尤其是文献网页检索、表单操作、资料采集这类任务；但比赛要求必须通过阿里云百炼调用 Qwen 并提供凭证/截图，所以最终作品最好让核心模型调用链清晰落在百炼 Qwen 上。([Hermes Agent][17])

百炼本身支持 Agent、Workflow、高代码应用三种核心应用模式，也支持知识库检索、外部工具调用和记忆等能力；智能体应用适合让模型自主决策调用工具，工作流适合固定流程任务。你的项目可以采用“**自研高代码多智能体后端 + 百炼 Qwen API + 可选百炼工作流截图**”的组合。([阿里云帮助中心][18])

---

## 4. 推荐系统架构

建议做成下面这条科研流水线：

**输入：研究方向 / 论文 PDF / 关键词 / 小规模波形数据 / 地震目录**

**输出：符合比赛规范的《科学假设与研究计划》**

核心 Agent 设计如下：

| Agent                   | 作用                              | 可展示能力     |
| ----------------------- | ------------------------------- | --------- |
| Research Planner        | 将用户输入拆成科研问题、数据需求、检索任务           | 问题理解      |
| Literature Miner        | 检索论文，抽取事实、方法、数据集、结论             | 文献挖掘与事实提取 |
| Citation Verifier       | 校验引用真实性、DOI、原文证据，防止虚构参考文献       | 可靠性       |
| Data Analyst            | 读取波形/目录数据，计算 SNR、震相标注分布、震级/距离统计 | 科学模态数据处理  |
| Hypothesis Generator    | 基于事实矩阵生成多个候选假设                  | 归纳/演绎推理   |
| Debate / Critic Agent   | 从新颖性、自洽性、可验证性、风险点角度辩论           | 智能体思辨     |
| Experiment Designer     | 生成 baseline、metrics、数据划分、实验流程   | 可落地验证     |
| Human-in-the-loop Agent | 让用户选择、否决、补充领域知识                 | 人在回路      |
| Report Writer           | 输出比赛要求的标准字段                     | 结构化交付     |

这个架构刚好覆盖比赛能力项：文献挖掘、逻辑驱动假设生成、论证可行与多轮迭代、智能体思辨与人在回路。

系统内部建议用一个“证据矩阵”贯穿全流程：

| Claim | Evidence | Source Paper | Dataset | Confidence | Contradiction | Used by Hypothesis |
| ----- | -------- | ------------ | ------- | ---------- | ------------- | ------------------ |

这样你在答辩时可以强调：**我们不是让大模型凭空想科研点，而是让它在“文献证据—数据特征—方法缺口—实验可验证性”的闭环中生成假设。**

---

## 5. 基座模型选择

主模型建议：

**Qwen3.7-Max 作为主推理模型。**

阿里云百炼页面显示 Qwen3.7-Max 面向智能体时代，支持编程智能体、MCP 集成和长周期自主执行；百炼模型文档中也已经列出 qwen3.7-max、qwen3.6-plus、qwen3.6-flash 等模型选项。([AlibabaCloud][19])

具体模型分工建议：

| 模型                        | 用途                                                |
| ------------------------- | ------------------------------------------------- |
| qwen3.7-max               | Planner、Hypothesis Generator、Debate、Report Writer |
| qwen3.6-plus              | 文献摘要、事实抽取、引用解释、批量中间任务                             |
| qwen3.6-flash             | 低成本批处理，如段落分类、关键词抽取、格式转换                           |
| qwen3.5-plus / Qwen 多模态模型 | 如果前端展示图表/波形图，让模型解释图像或表格时使用                        |

百炼支持 OpenAI 兼容接口、Responses、Anthropic 兼容 Messages 和 DashScope 原生接口；为了开发快，建议你后端优先用 OpenAI-compatible Chat Completions，后面如果需要更完整参数再切 DashScope。([阿里云帮助中心][20])

---

## 6. 是否需要微调

**第一版不建议微调。**

原因是比赛核心不是训练一个新模型，而是构建一个能生成可验证科研假设的系统。你如果现在投入 SFT，风险是：时间成本高、数据构造麻烦、效果难证明、答辩时容易被问训练数据、泛化、评测、泄漏、复现性。

更建议采用：

**RAG + 工具调用 + 多智能体编排 + 结构化输出约束 + 引用校验 + 小规模实验执行。**

比赛方案中写的是“允许微调，允许基于下游任务、领域数据的 SFT”，不是强制微调。

可选加分版可以做一个很小的“后处理微调”或“偏好样例库”，比如收集 100–300 条高质量科研假设样例，用来做 few-shot / prompt library，而不是一开始就真训模型。你可以在文档中写：当前版本优先保障引用真实性与实验可复现，后续计划基于领域专家反馈进行 SFT 或 DPO，用于提升假设排序与报告表达质量。

---

## 7. 开源项目参考与二次开发价值

### 7.1 AI Scientist / AI Scientist v2

Sakana AI 的 AI Scientist 项目主打从 idea generation、literature search、experiment planning、experiment iteration、figure generation、paper writing 到 reviewing 的自动科研流程；AI Scientist v2 进一步强调更通用的端到端 agentic scientific research。这个项目非常适合作为你技术方案中的“国际参考架构”，但不建议直接照搬，因为它主要面向机器学习研究自动化，而你的比赛需要 Qwen + 百炼 + 具体自然科学领域。([GitHub][21])

### 7.2 Google AI Co-Scientist

Google 的 AI co-scientist 是一个多智能体科研协作系统，用于生成和改进科学假设；官方介绍中强调 generate、debate、evolve 的多阶段结构，Nature 论文也将其描述为面向结构化科学思维和假设生成的 multi-agent 系统。这个非常适合借鉴你的“候选假设生成—辩论—排序—迭代”机制。([Google Research][22])

### 7.3 SciAgents / SciAgentsDiscovery

SciAgentsDiscovery 是一个用于生成创新科学假设的协作框架；SciAgents 论文强调知识图谱、多智能体推理和科学发现之间的结合。这个对你很有价值，因为你可以把“地震概念—数据集—模型—任务—评价指标—问题缺口”做成一个小型知识图谱。([GitHub][23])

### 7.4 GeoGPT / GeoGPT-RAG

GeoGPT 是面向地球科学研究的大语言模型系统，GeoGPT-RAG 通过领域语料检索增强地学问答的可靠性。你可以参考它的地学 RAG 思路，但最终基座模型仍建议用 Qwen3.7-Max，GeoGPT/GeoGPT-RAG 更适合作为“地学语料和检索增强参考”。([GitHub][24])

### 7.5 SeisT / SeisBench / DiTing

SeisT、SeisBench、DiTing 是你做地震方向最该用的开源/公开参考。SeisT 提供地震检测、phase picking、震级估计、震中距估计等任务的深度模型基础；SeisBench 提供统一 API 和地震机器学习数据/模型工具链；DiTing 是可以支撑机器学习地震监测研究的大规模中文地震基准数据集。([GitHub][25])

---

## 8. 前端与后端怎么搭

推荐技术栈：

**前端：Next.js + React + TailwindCSS + shadcn/ui**

页面不需要复杂，但要像一个科研工作台：

1. 项目输入页：输入研究方向、上传论文、上传数据或选择示例数据。
2. 文献证据页：展示文献列表、事实卡片、引用证据。
3. 数据分析页：展示波形统计、SNR 分布、震相标注分布、样例波形图。
4. 多智能体过程页：展示 Planner、Miner、Critic、Experiment Designer 的中间输出。
5. 假设辩论页：展示多个候选假设、评分、反驳、修改记录。
6. 最终报告页：一键导出《科学假设与研究计划》。

**后端：FastAPI + Python**

核心模块：

```text
backend/
  app.py
  agents/
    planner.py
    literature_miner.py
    citation_verifier.py
    data_analyst.py
    hypothesis_generator.py
    critic.py
    experiment_designer.py
    report_writer.py
  tools/
    paper_search.py
    pdf_parser.py
    seismic_loader.py
    metrics.py
    qwen_client.py
  rag/
    chunker.py
    embeddings.py
    vector_store.py
  workflows/
    run_scientist_pipeline.py
  outputs/
    reports/
    figures/
```

**数据层：**

第一版用 SQLite + Chroma/FAISS 就够了。想显得更强，可以加 Neo4j 做“地震科研知识图谱”，但不建议一开始就把复杂度拉满。

**部署：**

用 Docker Compose，一键启动前端、后端、向量库、数据库。答辩时强调“代码可复现”，对应评分里的“代码与结果可复现性”。

---

## 9. 最小可行 Demo 怎么做

你应该准备一个固定演示案例，不要现场完全随机生成。

演示输入：

**研究目标：如何提升低信噪比地震波形中的 P/S 震相拾取召回率，同时降低误报？**

系统流程：

1. 用户输入研究问题。
2. 系统检索 SeisT、PhaseNet、EQTransformer、DiTing、SeisBench、SeisLLM 相关论文。
3. Literature Miner 生成事实卡片。
4. Data Analyst 读取 20–100 条样例波形，计算 SNR、P/S 到时分布、震级/距离分布。
5. Hypothesis Generator 生成 3 个候选假设。
6. Critic Agent 进行反驳：是否已有论文做过？数据是否够？指标是否合理？
7. Experiment Designer 生成 baseline 和实验计划。
8. Report Writer 输出完整报告。

最终候选假设示例可以是：

**假设 H1：在低 SNR 波形中，引入由波形统计特征驱动的 prompt-as-prefix 或结构化先验，可以提升 LLM-guided phase picking 的 recall，尤其是在 P/S 到时模糊、振幅弱、Z/H 比异常的样本中表现更明显。**

这个假设和你的 SeisLLM 非常贴合，而且可验证：baseline 可以是 PhaseNet、EQTransformer、SeisT、去掉 prompt 的模型、去掉 LLM 的模型；指标可以是 Precision、Recall、F1、MAE、不同 SNR 区间的分层结果。

---

## 10. 10 分钟演示视频脚本

建议视频结构如下：

**0:00–0:40 背景痛点**
传统科研假设生成依赖专家经验；地震低信噪比波形难以识别，文献、数据、模型结果分散。

**0:40–1:30 项目目标**
介绍 GeoSeis-Scientist：从文献/数据输入到可验证科学假设输出。

**1:30–3:00 架构展示**
展示多智能体架构图：Planner、Literature Miner、Data Analyst、Hypothesis Generator、Critic、Experiment Designer、Report Writer。

**3:00–5:00 真实案例演示**
输入低 SNR phase picking 问题，展示文献事实抽取、波形统计图、候选假设。

**5:00–6:30 智能体辩论与人在回路**
展示三个假设的评分、反驳、迭代，人类选择其中一个进行深化。

**6:30–8:00 实验设计输出**
展示 baselines、metrics、dataset split、预期结果和可复现实验脚本。

**8:00–9:20 最终报告导出**
展示比赛要求的标准字段完整生成，引用真实论文。

**9:20–10:00 总结价值**
强调科学价值、技术深度、应用潜力、可复现性。

比赛推荐搭建前端、制作 10 分钟内演示视频，并推荐使用秒悟、万镜一刻等工具，所以你的视频一定要做，不能只交文档。

---

## 11. 技术方案 PDF 目录建议，控制在 20 页内

建议这样排：

1. 项目背景与问题定义
2. 研究问题：低信噪比地震监测中的可验证假设生成
3. 国内外相关工作：AI Scientist、Co-Scientist、SciAgents、GeoGPT、SeisT
4. 总体架构：GeoSeis-Scientist 多智能体系统
5. 基于 Qwen3.7-Max 与百炼 API 的模型调用设计
6. 文献挖掘与事实抽取模块
7. 地震波形/目录数据分析模块
8. 假设生成、辩论、迭代机制
9. 可验证实验设计模块
10. 真实案例展示
11. 前端与交互设计
12. 代码结构与复现方式
13. 创新点与应用价值
14. 局限性与后续计划

---

## 12. 是否需要“深度研究”

需要，但不是每一步都需要。

我建议你在三个节点使用深度研究：

第一，**选题确定前**，做一次“地震 AI Scientist / geoscience hypothesis generation / weak event detection / phase picking”系统调研，用来确定最终科学问题。

第二，**技术方案写作前**，深挖 AI Scientist、Google Co-Scientist、SciAgents、GeoGPT-RAG 的架构，把它们转化成你的“参考系统—差异点—本项目创新点”。

第三，**提交前**，做一次引用核验，确保报告里的 References 没有虚构，且每个关键 claim 都能追溯到真实论文或真实数据。

但深度研究结果不能直接照搬成作品。它更适合帮你做“资料收集和差异化定位”，最终系统和代码还是要你自己实现。

---

## 13. 时间规划

当前比赛报名时间是 **2026 年 5 月 30 日—6 月 30 日**，作品提交截止是 **2026 年 9 月 5 日**，9 月 20 日前初审，11 月终审擂台赛。

建议节奏：

| 时间      | 目标                           |
| ------- | ---------------------------- |
| 第 1 周   | 确定题目、报名、拉通老师/队友、完成调研提纲       |
| 第 2–3 周 | 完成论文库、数据集、baseline 清单，搭建后端骨架 |
| 第 4–5 周 | 实现文献挖掘、事实抽取、引用校验             |
| 第 6–7 周 | 实现波形/目录数据分析工具                |
| 第 8 周   | 实现假设生成、辩论、实验设计               |
| 第 9 周   | 搭建前端和固定演示案例                  |
| 第 10 周  | 完成技术方案 PDF 初稿和代码 README      |
| 第 11 周  | 录制演示视频，补充截图、百炼 API 调用凭证      |
| 第 12 周  | 打包提交、检查复现性、压缩包命名和材料完整性       |

---

## 14. 最终交付清单

你最后至少要交这些：

1. **技术方案 PDF ≤20 页**
2. **源代码仓库**
3. **README：一键运行说明**
4. **.env.example：百炼 API Key 配置示例**
5. **sample_data：小规模地震波形/目录样例**
6. **demo_outputs：系统生成的科学假设与研究计划**
7. **百炼调用截图 / 凭证截图**
8. **可交互前端页面**
9. **10 分钟内演示视频**
10. **引用论文列表与引用校验说明**

---

## 15. 你最应该强调的创新点

你的项目可以这样总结：

**本项目不是简单的文献问答系统，而是一个面向地震监测科研问题的多智能体 AI Scientist 原型。系统以 Qwen3.7-Max 为核心推理模型，通过文献事实抽取、地震波形/目录数据分析、候选假设生成、智能体辩论、人在回路修正和可验证实验设计，实现从“文献与数据输入”到“科学假设与研究计划输出”的闭环。相比通用 AI Scientist，本项目强化了地震科学模态数据处理、引用真实性校验和实验可复现设计。**

这个表述能同时打中三项评分：科学价值、技术深度、应用潜力。

[1]: https://chatgpt.com/c/69e4c098-bd74-83ea-8eec-b86a752127ba "OAuth凭证刷新失败"
[2]: https://chatgpt.com/c/69e9849c-81c4-83ea-b979-b7b1ed0e2dc5 "AI 音乐助手商业化"
[3]: https://chatgpt.com/c/6a10160d-e7c4-83ea-9161-b8422db54a66 "AI赛道项目推荐"
[4]: https://chatgpt.com/c/6a045d08-65fc-83ea-a851-dbeeffca4ecc "实习面试压力拷打"
[5]: https://chatgpt.com/c/69aed86f-68e0-8327-a62c-cfe6c7e973d8 "远程部署AI助手提升销量"
[6]: https://chatgpt.com/c/69b219eb-43c0-832b-8e22-6c6ced5c53a8 "npm安装失败问题"
[7]: https://chatgpt.com/c/6a028c14-7b24-83ea-bfb0-7fd45ce19f9d "面试准备与项目分析"
[8]: https://chatgpt.com/c/69b27500-8348-832f-aaab-25b3a674eb98 "命令空格问题解析"
[9]: https://chatgpt.com/c/69f0a0f0-a5f8-83ea-959b-978c58fa1ee4 "流程式后训练调参策略"
[10]: https://chatgpt.com/c/69ae3677-4ee8-832d-b441-b1811be7f0a4 "Gateway运行问题排查"
[11]: https://chatgpt.com/c/69c62436-2a68-83e8-9943-04318e53fa10 "2026年OKR建议"
[12]: https://chatgpt.com/c/6a058322-fab0-83ea-ae90-3da8434564f2 "面试题库建议"
[13]: https://chatgpt.com/c/6a0299ee-6df0-83ea-9f2c-cb086edc8764 "解决pip安装问题"
[14]: https://chatgpt.com/c/69c1072a-b9e8-8332-a49c-78ffe42d94bf "Seismic Model Enhancement"
[15]: https://www.equsci.org.cn/article/doi/10.1016/j.eqs.2022.01.022?utm_source=chatgpt.com "DiTing: A large-scale Chinese seismic benchmark dataset ..."
[16]: https://github.com/openclaw/openclaw?utm_source=chatgpt.com "OpenClaw — Personal AI Assistant"
[17]: https://hermes-agent.nousresearch.com/docs/user-guide/features/browser?utm_source=chatgpt.com "Browser Automation | Hermes Agent - nous research"
[18]: https://help.aliyun.com/zh/model-studio/application-introduction?utm_source=chatgpt.com "三种核心应用模式对比选型-大模型服务平台百炼-阿里云"
[19]: https://www.aliyun.com/product/bailian?utm_source=chatgpt.com "大模型服务平台百炼- 大模型应用构建- 阿里云"
[20]: https://help.aliyun.com/zh/model-studio/qwen-api-reference/?utm_source=chatgpt.com "文本生成模型API参考 - 阿里云文档"
[21]: https://github.com/sakanaai/ai-scientist?utm_source=chatgpt.com "The AI Scientist: Towards Fully Automated Open-Ended ..."
[22]: https://research.google/blog/accelerating-scientific-breakthroughs-with-an-ai-co-scientist/?utm_source=chatgpt.com "Accelerating scientific breakthroughs with an AI co-scientist"
[23]: https://github.com/lamm-mit/SciAgentsDiscovery?utm_source=chatgpt.com "lamm-mit/SciAgentsDiscovery"
[24]: https://github.com/GeoGPT-Research-Project/GeoGPT?utm_source=chatgpt.com "Official release of GeoGPT models."
[25]: https://github.com/senli1073/SeisT?utm_source=chatgpt.com "[TGRS] SeisT: A Foundational Deep-Learning Model for ..."


User:
我有几个问题和想法：1.不要强绑定SeisLLM/EHS背景，面向地震/地球物理科研问题在当前的科研界或者说顶会顶刊的圈子里，有一种默认的“鄙视”，大家很容易认为这个方向的论文是水论文，含金量不高，我们尽量避免这个方向的刻板印象。2.我认同你自研Multi-Agent+百炼Qwen API的思路，但是需要参考Hermes的浏览器自动化、技能循环和多工具调用等能力，尤其是文献网页检索、表单操作、资料采集这类任务，因为参赛规则明确要求不能虚构参考文献和资料等

GPT:
你这两个判断是对的，我建议把路线改成：

**不要把作品绑定成“地震/SeisLLM/EHS 项目延伸”，而是做一个通用但有垂直验证场景的“文献—数据—假设—实验计划”AI Scientist 平台。**
地震方向最多作为你个人理解能力的备选 case，不作为主赛题标签。主赛题最好换成更容易被评委认为“科学价值高、公开数据强、可验证性强”的方向，比如**材料科学 / 能源催化 / 固态电池 / 晶体性质预测**。

比赛文件里明确要求系统围绕特定学科领域，基于 OpenClaw、Hermes 或自研 Multi-Agent，利用 Qwen 构建从“数据/文献输入”到“可验证科学假设输出”的闭环；同时能力项强调文献挖掘、事实提取、引用可靠、多轮迭代、人在回路。这个要求非常适合你说的“自研 Multi-Agent + 参考 Hermes 的浏览器自动化和工具循环”。

---

## 一、项目定位建议更新

建议项目从：

> 面向地震/地球物理的 AI Scientist

改成：

> **面向高价值科学问题的可信 AI Scientist：基于文献证据链、开放科学数据库与多智能体推理的可验证假设生成系统**

再落到一个具体 demo 场景：

> **以能源材料 / 催化剂 / 固态电池材料发现为示范场景**

这样既避免“地震应用论文”的刻板印象，又不会变成空泛平台。材料科学方向有几个优势：
一是高科学价值更容易被认可，和新能源、低碳、材料发现、AI for Science 关系更近；二是公开数据库和 benchmark 比较成熟，比如 Materials Project 提供已知和预测材料的计算信息，Matbench 是材料性质预测 benchmark，Open Catalyst Project 提供催化相关数据和 baseline，便于做“可验证实验计划”。([Materials Project][1])

---

## 二、核心任务怎么重新定义

你的核心任务不要叫“自动生成论文”，也不要叫“科研聊天机器人”，而应该叫：

**可信科研假设生成与验证计划自动化系统。**

输入可以是：

“我想研究固态电解质材料的离子电导率提升机制，请基于近五年文献和开放数据库，生成一个可验证的研究假设与实验计划。”

系统输出必须严格符合比赛要求的《科学假设与研究计划》，包括 Problem Statement、Rationale、Technical Details、Datasets、Source、Target、Methods、Experiments、Results、References 等字段。比赛文件还明确要求参考论文必须是真实文献，严禁虚构。

所以项目的真正卖点不是“大模型会写”，而是：

**它能自动查文献、核验来源、抽取事实、发现知识缺口、提出假设、设计验证实验，并保留可追溯证据链。**

---

## 三、Hermes 的能力怎么吸收进自研系统

你不需要直接二开 Hermes，但要吸收它的三类思想：

第一是**浏览器自动化**。
系统不能只靠 API 搜索摘要，而要能打开论文网页、arXiv 页面、期刊页面、数据库页面，自动下载 PDF、读取表格、保存截图、记录访问路径。技术上可以用 Playwright 做 browser worker，用 Qwen 做网页理解和下一步动作决策。

第二是**技能循环**。
每次完成一个稳定任务，比如“检索 DOI”“下载 PDF”“解析 Methods”“核对参考文献”“查询 Materials Project 数据”，都保存成一个 Skill。下一次遇到类似任务时，不重新让大模型瞎试，而是调用已有 Skill。

第三是**多工具调用**。
文献检索不能只用一个搜索入口。建议同时接入 arXiv、OpenAlex、Crossref、Semantic Scholar。OpenAlex 提供学术 works、authors、institutions 等数据接口；Crossref REST API 可以查 DOI 和文献元数据；Semantic Scholar Graph API 可以查论文、作者、引用关系；arXiv API 可以程序化访问 arXiv 预印本。([OpenAlex开发者][2])

---

## 四、推荐总体架构

我建议你设计成三层：

### 1. Agent 层

核心 Agent 可以这样拆：

| Agent                      | 作用                                                    |
| -------------------------- | ----------------------------------------------------- |
| Task Planner Agent         | 把用户科研问题拆成文献检索、数据查询、事实抽取、假设生成、验证设计                     |
| Browser Research Agent     | 像 Hermes 一样控制浏览器，检索网页、打开论文、下载 PDF、保存证据                |
| Literature Miner Agent     | 从论文中抽取研究问题、方法、数据集、结论、局限性                              |
| Citation Verifier Agent    | 核验 DOI、标题、作者、年份、期刊、引用内容是否匹配                           |
| Scientific Data Agent      | 查询 Materials Project / Matbench / Open Catalyst 等开放数据 |
| Gap Finder Agent           | 汇总已有事实，识别“尚未解决的问题”                                    |
| Hypothesis Generator Agent | 生成多个候选假设                                              |
| Critic / Debate Agent      | 反驳假设，检查是否新颖、自洽、可验证                                    |
| Experiment Designer Agent  | 设计 baseline、metric、数据集、实验流程                           |
| Report Writer Agent        | 输出比赛要求的结构化《科学假设与研究计划》                                 |

### 2. Tool 层

工具建议包括：

```text
search_paper()
open_webpage()
download_pdf()
parse_pdf()
extract_tables()
verify_doi()
query_openalex()
query_crossref()
query_semantic_scholar()
query_arxiv()
query_materials_project()
run_small_experiment()
export_report()
```

### 3. Evidence Layer 证据层

这是你作品最应该重点展示的部分。每一个最终结论都必须对应证据：

```json
{
  "claim": "某类材料的结构特征与离子电导率存在相关性",
  "evidence_type": "paper / dataset / table / experiment",
  "source_title": "...",
  "doi": "...",
  "url": "...",
  "page": 5,
  "quote_or_summary": "...",
  "confidence": 0.82,
  "verified": true
}
```

答辩时你可以强调：
**我们的系统不是让大模型自由生成 References，而是先锁定真实来源，再基于证据池写报告。**

---

## 五、反幻觉机制要作为核心创新点

因为比赛明确要求 References 不能虚构，所以你可以把“可信引用与证据链”包装成技术创新点之一。

建议设置 7 道关：

1. **引用白名单**：最终 References 只能来自 OpenAlex / Crossref / Semantic Scholar / arXiv / 用户上传 PDF 中已验证的论文。
2. **DOI 校验**：有 DOI 的论文必须通过 Crossref 校验标题、作者、年份。
3. **标题相似度校验**：模型生成的标题与数据库标题相似度低于阈值，直接剔除。
4. **证据片段绑定**：每个关键 claim 必须绑定 PDF 页码、段落或数据库字段。
5. **引用冻结**：Report Writer 阶段不能新增 References，只能使用 Citation Verifier 已确认的引用。
6. **不确定性标记**：找不到证据的内容必须标记为“待验证”，不能写成确定结论。
7. **最终审计报告**：输出一份 citation audit log，展示哪些引用通过了 DOI、网页、PDF 三重核验。

这个机制比“我用了大模型 RAG”更有比赛说服力。

---

## 六、主赛题方向推荐：材料科学 / 能源材料

我现在更推荐你做这个方向：

**MatSci-Scientist：面向能源材料发现的可信多智能体科学假设生成系统**

示范问题可以选：

> 如何基于文献和开放材料数据库，自动生成关于高稳定性、低成本、可合成能源材料的可验证研究假设？

或者更具体：

> 面向固态电解质 / 催化剂 / 钙钛矿稳定性，自动生成“结构特征—性能指标—验证实验”闭环假设。

理由是材料科学方向有公开数据库、公开 benchmark、明确评价指标，容易把“科学价值”和“技术可验证”结合起来。Matbench 提供材料性质预测任务；Open Catalyst Project 公开了 OC20、OC22 等催化相关数据和 baseline；Materials Project 提供材料计算信息与分析工具。([材料项目][3])

---

## 七、你可以生成什么样的假设

系统最终生成的假设不要过度夸大成“发现了新材料”，而应更稳妥：

### 候选假设示例 1

**Problem Statement**
现有固态电解质候选材料筛选中，单纯依赖组成特征或晶体结构特征可能无法充分捕捉离子迁移通道与稳定性之间的耦合关系。

**Hypothesis**
如果将文献中提取的结构机制描述、开放数据库中的晶体结构特征、以及基于图神经网络的局部配位环境表征联合建模，可能提升对离子电导率或稳定性的预测能力。

**Verification Plan**
使用 Matbench 或 Materials Project 相关数据构建 baseline，对比 composition-only、structure-only、literature-augmented 三类模型。

### 候选假设示例 2

**Problem Statement**
催化剂筛选中，吸附能预测模型通常依赖大规模 DFT 数据，但对低资源材料体系的泛化能力不足。

**Hypothesis**
如果利用文献中已有的反应机理描述构建约束条件，并结合 Open Catalyst 数据中的吸附结构特征，可以生成更适合低资源催化体系的候选筛选策略。

**Verification Plan**
基于 Open Catalyst 的公开数据和 baseline 设计小规模对比实验，评估 MAE、ranking accuracy、top-k hit rate 等指标。

这种写法的优势是：既有科学问题，也有技术验证路径，不会被质疑“只是大模型编故事”。

---

## 八、是否微调

我仍然建议：**第一版不做微调。**

原因是这个比赛最看重的不是“你训了一个模型”，而是：

* 有没有科学价值；
* 有没有多智能体协作；
* 有没有处理科学模态数据；
* 有没有真实引用和可复现代码；
* 有没有能跑通的系统原型。

比赛允许 SFT，但不是强制；它要求基座模型必须基于 Qwen，并通过阿里云百炼平台调用模型 API，提供调用凭证或截图。

更稳的路线是：

**Qwen3.7-Max + RAG + Browser Automation + Tool Calling + Evidence Verification + Structured Output。**

如果你后期时间充足，可以做一个很轻的“假设质量排序器”，用人工打分样例训练一个 reranker，但不要把主线压在微调上。

---

## 九、前端应该怎么做

前端不要做成普通聊天框，而要做成“科研驾驶舱”。

建议页面包括：

1. **Research Question 输入页**
   用户输入研究方向、约束条件、目标数据源。

2. **Browser Automation 过程页**
   展示系统正在打开哪些网页、检索哪些关键词、下载哪些 PDF。这个页面非常关键，因为它能证明你不是编引用。

3. **Evidence Board 证据看板**
   每条科学事实都有来源、DOI、PDF 页码、可信度。

4. **Hypothesis Arena 假设竞技场**
   展示多个候选假设，每个假设有新颖性、自洽性、可验证性评分。

5. **Debate 页面**
   Critic Agent 对假设提出反驳，Generator Agent 修改假设。

6. **Experiment Plan 页面**
   自动生成数据集、baseline、metric、实验步骤。

7. **Final Report 页面**
   一键导出比赛要求的《科学假设与研究计划》。

前端技术栈用 Next.js + Tailwind + shadcn/ui 就够。后端 FastAPI + Python，浏览器自动化用 Playwright，向量库用 Chroma/FAISS，任务编排可以先自己写状态机，不一定一上来用 LangGraph。

---

## 十、演示视频应该突出什么

视频一定要突出“可信资料采集”和“证据链”，而不是只展示最后一篇报告。

建议 10 分钟视频结构：

1. **0:00–1:00**：介绍痛点：科研假设生成容易依赖经验，大模型容易虚构引用。
2. **1:00–2:00**：介绍系统架构：Qwen + 自研 Multi-Agent + Browser Automation + Evidence Ledger。
3. **2:00–4:00**：现场输入一个材料科学问题，展示 Browser Agent 自动检索论文和数据库。
4. **4:00–5:30**：展示 Citation Verifier 如何校验 DOI、标题、作者、PDF 内容。
5. **5:30–7:00**：展示多智能体生成、辩论、迭代假设。
6. **7:00–8:30**：展示实验计划，包括 dataset、baseline、metric。
7. **8:30–9:30**：导出最终报告。
8. **9:30–10:00**：总结科学价值、技术深度和应用潜力。

比赛文件推荐搭建前端和制作 10 分钟内演示视频，所以这个视频应该作为核心交付，而不是附属材料。

---

## 十一、更新后的最终路线

你的参赛路线可以定为：

**主线：自研 Multi-Agent AI Scientist 系统。**
**基座：百炼 Qwen3.7-Max / Qwen 系列 API。**
**能力参考：Hermes 的浏览器自动化、技能沉淀、多工具调用。**
**示范领域：材料科学 / 能源材料，而不是地震。**
**核心创新：可信证据链 + 引用核验 + 多智能体辩论 + 可验证实验设计。**
**不优先微调：先做系统闭环、前端、视频、可复现代码。**

一句话版本：

> 我们做的不是某个具体学科的“论文生成器”，而是一个面向高价值科学问题的可信 AI Scientist 原型：它通过浏览器自动化和多工具检索获取真实文献与数据，利用 Qwen 驱动多智能体完成事实抽取、知识缺口识别、假设生成、批判性辩论与实验设计，最终输出带证据链和引用核验的《科学假设与研究计划》。

这个定位比强行绑定 SeisLLM 或地震方向更稳，也更容易打中比赛的科学价值、技术深度和应用潜力三项评分。

[1]: https://next-gen.materialsproject.org/?utm_source=chatgpt.com "Materials Project"
[2]: https://developers.openalex.org/?utm_source=chatgpt.com "OpenAlex API"
[3]: https://docs.materialsproject.org/services/ml-and-ai-applications/matbench?utm_source=chatgpt.com "MatBench"


User:
我找到一个开源仓库https://github.com/handsome-rich/Awesome-Auto-Research-Tools，里面也是一些自动化研究的工具集合，请你查看这个仓库的内容，判断一下是否有参考的价值，如果有应该怎么利用这些仓库的内容，接下来我打开正式开始搭建这个Multi-Agent AI Scientist系统，我想在linux环境的远程服务器docker中搭建，我是利用vscode中的codex插件进行协助开发比较好，还是直接用hermes框架进行开发比较好

GPT:
你的判断可以进一步收敛成一句话：

**这个 Awesome-Auto-Research-Tools 仓库非常有参考价值，但它不是你要直接 fork 的主工程；它更像“自动科研系统选型地图”。你的主工程还是建议自研 Multi-Agent AI Scientist，开发过程用 VSCode + Codex 插件辅助，Hermes 作为浏览器自动化、技能循环、多工具调用的参考对象或旁路工具，而不是直接把 Hermes 当主框架。**

比赛本身要求基于 Qwen/千问系列、通过阿里云百炼平台调用模型 API，并提交架构设计、源代码、上下文工程、真实案例，且最终报告里的参考文献严禁虚构；这决定了我们需要一个**可控、可解释、可复现、能证明引用来源真实**的系统，而不是单纯套一个通用智能体框架。

---

## 1. Awesome-Auto-Research-Tools 有没有参考价值？

有，而且价值很高。

这个仓库本质是一个自动科研工具集合，覆盖从 literature review、idea generation、experiment execution、paper writing 到 peer review 的科研生命周期；README 里把项目分成 End-to-End Autonomous Research Systems、Deep Research & Literature Synthesis、Automated Experiment & Code Agent、Research Skills & Plugin Collections 等类别。([GitHub][1])

它对你的价值主要有三层：

| 用法       | 价值                                                                             | 是否直接采用 |
| -------- | ------------------------------------------------------------------------------ | ------ |
| 看系统架构    | 参考 AI-Scientist、RD-Agent、Agent Laboratory、AI-Researcher、AutoResearchClaw 怎么拆任务 | 强烈建议   |
| 借模块思路    | 文献检索、引用核验、实验执行、报告生成、代码 agent、skills                                            | 强烈建议   |
| 直接二开整个项目 | 风险较高，容易变成别人的系统换皮                                                               | 不建议    |

这个列表中最值得你重点看的不是所有项目，而是下面几类：End-to-End 类里的 AI-Scientist、AI-Scientist-v2、RD-Agent、AutoResearchClaw、Agent Laboratory、Idea2Paper；Deep Research 类里的 STORM、GPT Researcher、PaperQA2、OpenScholar；实验与代码执行类里的 Aider、OpenHands、SWE-agent、AIDE；技能集合类里的 scientific-agent-skills 和 AI-Research-SKILLs。仓库对这些项目的功能描述已经基本覆盖了你要做的“科研假设生成—实验设计—报告输出”主链路。([GitHub][1])

---

## 2. 这个仓库应该怎么用？

不要把它当“代码仓库”，而要当“竞品调研与模块库”。

我建议你这样拆：

### 第一类：参考整体架构

重点看：

**AI-Scientist / AI-Scientist-v2 / Agent Laboratory / AI-Researcher / Idea2Paper**

你要学习的是它们如何组织：

```text
idea generation
→ novelty check
→ literature retrieval
→ experiment planning
→ code execution
→ result analysis
→ paper/report writing
→ review / critique
```

然后你自己的系统可以改成比赛更需要的版本：

```text
科研问题输入
→ 浏览器/数据库检索
→ 文献事实抽取
→ 引用真实性核验
→ 科学数据查询
→ 知识缺口识别
→ 多候选假设生成
→ Critic 辩论与人在回路
→ 实验设计
→ 标准化《科学假设与研究计划》输出
```

### 第二类：参考文献检索与引用核验

重点看：

**GPT Researcher / STORM / PaperQA2 / OpenScholar / local-deep-research**

但你不要只复制它们的 RAG。你的比赛项目最核心的是“**可信证据链**”，所以要增加一个 Citation Verifier：

```text
模型生成 claim
→ 找到对应论文
→ 校验 DOI / title / authors / year
→ 找到 PDF 原文片段或数据库字段
→ claim 绑定 source_id
→ 最终报告只能使用 verified references
```

这部分是你区别于普通 Deep Research 工具的关键。

### 第三类：参考代码执行与实验自动化

重点看：

**AIDE / Aider / OpenHands / SWE-agent / RD-Agent**

但是第一版不用做太复杂的自动实验平台。你可以先做一个轻量实验执行器：

```text
experiment_runner/
  run_baseline.py
  run_ablation.py
  evaluate_metrics.py
  save_result_card.py
```

也就是说，AI Scientist 不一定要真的跑完整大规模实验，但至少要能在小样例数据上执行一个可复现实验，生成 result card，这样就能对应比赛里的“实验结果：通过公式推导或实际执行，在一定范围内验证该实验可行性”。

### 第四类：参考技能库

重点看：

**scientific-agent-skills / AI-Research-SKILLs**

这些技能集合适合启发你设计自己的技能系统，比如：

```text
skills/
  search_openalex/
  search_crossref/
  search_semantic_scholar/
  download_pdf/
  parse_pdf/
  extract_claims/
  verify_citation/
  query_materials_project/
  generate_hypothesis/
  critique_hypothesis/
  design_experiment/
  export_report/
```

你不用一开始做通用技能市场，只要做一个本项目内可复用的 Skill Registry，就已经很像 Hermes 的技能循环了。

---

## 3. Codex 插件开发 vs 直接用 Hermes 框架

我的建议非常明确：

**主开发用 VSCode Remote SSH / Dev Container + Codex 插件；不要直接用 Hermes 作为主框架。**

Hermes 当然有参考价值。它的官方文档显示，Hermes 有浏览器自动化能力，支持 Browserbase、Browser Use、Firecrawl、Camofox、本地 Chromium CDP、本地 browser CLI 等多种模式，可以导航网页、点击元素、填写表单、提取信息，还能用 accessibility tree 给 LLM 观察页面。([GitHub][2])

Hermes 也有比较丰富的内置工具集，文档里列了浏览器工具、文件工具、终端工具、web 工具、记忆、任务委派、代码执行、技能管理等工具，并支持通过 MCP 动态加载工具。([GitHub][3])

但它不适合作为你比赛主工程的原因是：

| 维度         | Codex 辅助自研                   | 直接 Hermes 开发        |
| ---------- | ---------------------------- | ------------------- |
| 代码可控性      | 高，架构完全自己定义                   | 中，容易受框架约束           |
| 比赛叙事       | 清楚：自研 Multi-Agent + Qwen API | 容易被认为是套壳通用 Agent    |
| 百炼/Qwen 合规 | 容易保证所有核心调用走百炼                | 需要额外确认模型路由和配置       |
| 引用核验链路     | 可以按比赛要求专门设计                  | 需要改造 Hermes 工具链     |
| 前端展示       | Next.js/FastAPI 自己做，容易控制     | Hermes 自身不是科研工作台 UI |
| 开发速度       | Codex 适合帮你逐文件实现              | Hermes 学习/改造成本不低    |
| 安全隔离       | 自己定义 Docker、浏览器、API key 权限   | 需要额外处理浏览器凭证、工具权限    |

所以最优方案是：

**Codex 负责开发你的主系统；Hermes 负责启发你的 browser agent、skill loop、tool registry 设计。**

如果你非常想用 Hermes，可以把它作为“旁路验证工具”：先用 Hermes 跑几次文献检索/网页采集流程，观察它怎么操作浏览器、怎么保存技能，然后把可复用逻辑沉淀到你自己的 FastAPI + Playwright 工具层里。

---

## 4. 是否可以用 Qwen-Agent？

可以，而且它比 Hermes 更适合作为“Qwen 生态内的可选组件”。

Qwen-Agent 官方说明它是基于 Qwen 的 instruction following、tool usage、planning、memory 能力开发 LLM 应用的框架，并带有 Browser Assistant、Code Interpreter、Custom Assistant 等示例；安装时也支持 rag、code_interpreter、mcp 等可选能力。([GitHub][4])

所以你的框架选择可以是：

```text
方案 A：完全自研轻量状态机
FastAPI + Python classes + tools + evidence DB
推荐指数：★★★★★

方案 B：自研主系统 + 部分使用 Qwen-Agent
用于 tool calling / code interpreter / RAG
推荐指数：★★★★☆

方案 C：直接 Hermes 作为主框架
推荐指数：★★☆☆☆
```

我更建议先用 **方案 A**，因为你现在需要快速形成可控 Demo，不要一开始陷入大框架适配。等主流程跑通后，再评估是否把 Qwen-Agent 的工具调用或 MCP 接进来。

---

## 5. 远程 Linux Docker 环境怎么搭

推荐目录结构：

```text
ai-scientist/
  backend/
    app/
      agents/
      tools/
      services/
      evidence/
      workflows/
      schemas/
    Dockerfile
    requirements.txt
  frontend/
    app/
    components/
    Dockerfile
    package.json
  browser-worker/
    Dockerfile
    worker.py
  infra/
    docker-compose.yml
    .env.example
  data/
    papers/
    parsed/
    outputs/
  docs/
    architecture.md
    demo_script.md
```

推荐服务拆分：

```text
frontend: Next.js 科研工作台
backend: FastAPI，多智能体编排
browser-worker: Playwright 浏览器自动化
postgres: 保存任务、证据、引用、报告
qdrant/chroma: 向量检索
redis: 异步任务队列，可选
```

第一阶段不要做太复杂，甚至可以先不用 Celery，用 FastAPI BackgroundTasks 或 RQ。你真正要先跑通的是：

```text
用户输入研究问题
→ Planner 生成检索计划
→ Browser/Paper Search 获取真实论文
→ PDF Parser 抽取事实
→ Citation Verifier 校验引用
→ Hypothesis Agent 生成候选假设
→ Critic Agent 反驳与改写
→ Experiment Designer 生成实验计划
→ Report Writer 导出结构化报告
```

---

## 6. 第一版 MVP 具体做什么

不要一开始做“超级完整 AI Scientist”。第一版只做 5 个闭环能力：

### MVP-1：论文检索与引用核验

接入：

```text
OpenAlex
Crossref
Semantic Scholar
arXiv
用户上传 PDF
```

输出：

```json
{
  "title": "...",
  "authors": ["..."],
  "year": 2024,
  "doi": "...",
  "source_url": "...",
  "verified": true
}
```

### MVP-2：PDF 事实抽取

从论文里抽取：

```text
研究问题
方法
数据集
实验指标
主要结论
局限性
可迁移思路
```

### MVP-3：证据链 Evidence Ledger

所有 claim 必须绑定证据：

```json
{
  "claim": "某方法在低资源材料预测中泛化不足",
  "source_id": "paper_001",
  "evidence_text": "...",
  "page": 6,
  "confidence": 0.84,
  "verified": true
}
```

### MVP-4：多智能体假设生成

最小 Agent 组合：

```text
Planner Agent
Literature Miner Agent
Citation Verifier Agent
Hypothesis Generator Agent
Critic Agent
Experiment Designer Agent
Report Writer Agent
```

### MVP-5：前端展示

前端只要四个页面就够：

```text
1. Research Question 输入页
2. Evidence Board 证据看板
3. Hypothesis Arena 假设生成/辩论页
4. Final Report 报告导出页
```

---

## 7. 你现在应该怎么开始

建议你今天就按这个顺序做：

```bash
mkdir ai-scientist
cd ai-scientist
git init

mkdir backend frontend browser-worker infra data docs
```

然后先让 Codex 帮你完成这 4 个任务：

```text
任务 1：创建 FastAPI 后端骨架，包含 /api/runs/create、/api/runs/{id}、/api/evidence、/api/report
任务 2：实现 qwen_client.py，统一封装百炼 DashScope / OpenAI-compatible API 调用
任务 3：实现 paper_search.py，先接 OpenAlex + Crossref，返回标准 PaperSchema
任务 4：实现 citation_verifier.py，校验 DOI、标题相似度、作者年份
```

你给 Codex 的第一条 prompt 可以这样写：

```text
我正在开发一个用于挑战杯 AI Scientist 比赛的 Multi-Agent 科研假设生成系统。请先帮我搭建 backend 的 FastAPI 项目骨架。要求：
1. Python 3.11；
2. 使用 pydantic 定义 ResearchRun、Paper、Evidence、Hypothesis、ExperimentPlan、FinalReport schema；
3. 预留 Qwen 百炼 API 客户端 qwen_client.py；
4. 预留 tools/paper_search.py、tools/citation_verifier.py、tools/pdf_parser.py；
5. 提供 Dockerfile 和 requirements.txt；
6. 代码结构清晰，方便后续加入多智能体 workflow；
7. 不要一次性写太多业务逻辑，先保证能启动和接口能返回 mock 数据。
```

等 FastAPI 骨架跑起来，再让 Codex 写前端。不要前后端一起开工，否则很容易乱。

---

## 8. 最终建议

你现在的路线应该定成：

**开发方式：VSCode Remote SSH / Docker + Codex 插件辅助开发。**
**主系统：自研 Multi-Agent AI Scientist。**
**模型：百炼 Qwen3.7-Max / Qwen 系列。**
**参考：Awesome-Auto-Research-Tools 作为架构地图；Hermes 作为浏览器自动化和技能循环参考；必要时局部引入 Qwen-Agent。**
**核心卖点：可信证据链、引用核验、多智能体辩论、可验证实验计划。**

不要直接用 Hermes 做主框架。你可以学习 Hermes，但比赛作品最好让评委看到：**这是你们自己围绕 AI Scientist 赛题设计的科研智能体系统，而不是把一个通用个人助理改了个科研 prompt。**

[1]: https://github.com/handsome-rich/Awesome-Auto-Research-Tools "GitHub - handsome-rich/Awesome-Auto-Research-Tools: A curated collection of automated research tools, covering literature search, paper reading, experiment management, and code generation to help researchers accelerate their workflow. · GitHub"
[2]: https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/browser.md "hermes-agent/website/docs/user-guide/features/browser.md at main · NousResearch/hermes-agent · GitHub"
[3]: https://github.com/NousResearch/hermes-agent/blob/main/website/docs/reference/tools-reference.md "hermes-agent/website/docs/reference/tools-reference.md at main · NousResearch/hermes-agent · GitHub"
[4]: https://github.com/QwenLM/Qwen-Agent "GitHub - QwenLM/Qwen-Agent: Agent framework and applications built upon Qwen>=3.0, featuring Function Calling, MCP, Code Interpreter, RAG, Chrome extension, etc. · GitHub"

