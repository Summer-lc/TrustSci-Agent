# TrustSci-Agent PRD v3

更新时间：2026-06-26

## 1. 一句话定位

TrustSci-Agent v3 在 v1/v2 的可信科研基础流程之上，新增 **Seismic Expert / 地震科研专家** 工作流。前端通过版本切换器并存两种入口：Classic Workflow（v1/v2 线性基础版）和 Seismic Expert（v3 地震竞技版）。Seismic Expert 新增三种科研入口模式、竞技式假设筛选（Discovery 排名竞技 / Idea Refinement 消融式竞技）、微观 ReAct 代码调试循环、宏观 ReAct 实验反馈循环、假设回退机制和消融验证能力。

系统目标不是只训练一个地震分类模型，而是构建一个可以围绕地震事件分类科研问题完成以下闭环的 AI Scientist：

```text
科研方向 / 已有创意 / 已有实验
  -> 问题结构化 (Intent Router)
  -> 文献与数据采集
  -> 可信证据链
  -> 假设竞技筛选 (Discovery排名 / Idea Refinement消融式)
  -> 文献代码 baseline 发现与复现
  -> 实验代码生成 / 适配 / 执行 (微观ReAct调试循环)
  -> 结果评估与反馈 (宏观ReAct实验迭代循环)
  -> 假设回退 (实验失败时切换候选假设)
  -> 消融验证
  -> 标准化科学假设与研究计划报告
```

v3 的垂直 demo 聚焦：

> 基于真实地震波形数据、公开文献与可复现代码 baseline，辅助研究者生成并验证深度学习地震事件分类假设，例如自然地震、人工爆破、塌陷/冲击类事件与噪声等事件类型的自动识别。

## 2. v1/v2 基础流程保留

v1/v2 的核心逻辑仍然保留，不推翻：

```text
User Input
  -> Research Planner
  -> Literature & Data Acquisition
  -> Evidence Engine
  -> Hypothesis Arena
  -> Experiment Designer
  -> Report Generator
  -> Research Workspace
```

这些模块仍是 TrustSci-Agent 的底座：

- Research Planner：把科研问题转成可执行任务。
- Literature Router：检索真实文献。
- Citation Verifier：核验 DOI、arXiv ID、标题和来源。
- Evidence Ledger：绑定 claim、paper、source、page、verification state。
- Hypothesis Arena：v1/v2 是线性"生成→批判→修订"，v3 升级为竞技机制（Discovery 排名竞技 / Idea Refinement 消融式竞技）。
- Experiment Designer：生成可验证实验计划。
- Report Writer：输出符合比赛规范的《科学假设与研究计划》。
- Research Workspace：保存全过程 artifacts，支持复现和审计。

v3 的变化是：前端增加版本切换器（Classic Workflow vs Seismic Expert），两种工作流并存；Seismic Expert 在入口增加三种科研模式（分支），在假设层升级为竞技机制，在后段增加微观ReAct代码调试、宏观ReAct实验反馈循环和Hypothesis Switchback假设回退，并将主 demo 领域切换到地震事件分类（材料方向作为保留的第二domain）。Classic Workflow 保持 v1/v2 不变。

## 3. v3 新增三种入口模式

v3 不再默认所有用户都只有一个模糊方向，而是区分三种真实科研使用场景。

### 3.1 Discovery Mode：科研方向发现模式

适用于用户只有模糊方向、没有明确假设的场景。

用户示例：

> 我想研究深度学习在地震事件识别中的应用。

系统职责：

```text
模糊方向输入
  -> 多视角拆题
  -> 文献检索
  -> 数据源识别
  -> 知识缺口发现
  -> 生成多个候选假设
  -> reviewer critic / revision
  -> 用户选择假设
  -> 文献代码 baseline 发现
  -> 实验代码生成和执行
  -> baseline 对比
  -> 消融验证
  -> 结果解释与报告
```

该模式的重点是：系统从 0 到 1 帮助用户找到可验证科研假设，并进一步生成代码和实验验证路径。

### 3.2 Idea Refinement Mode：已有创意精修模式

适用于用户已有初步想法，但需要系统帮助判断创新性、可行性和实验路径的场景。

用户示例：

> 我想用多通道波形 + 时频图融合来区分自然地震和人工爆破。

系统职责：

```text
已有创意输入
  -> 创意结构化
  -> 相似工作检索
  -> novelty / overlap check
  -> 找出可优化点和风险
  -> 精修假设与贡献表述
  -> 文献代码 baseline 发现
  -> 公平对比实验设计
  -> 用户创意对应代码实现
  -> baseline 对比
  -> 消融验证
  -> 结果解释与报告
```

该模式的原则是：系统不替换用户创意，而是围绕用户创意进行有限展开、证据核验、实验设计和结果验证。

### 3.3 Experiment Assistance Mode：实验补全与论文化模式

适用于用户已有数据、代码或初步实验结果，需要系统补 baseline、补消融、补分析和生成报告的场景。

用户示例：

> 我已经有一个 CNN 地震分类模型和初步训练结果，帮我补文献 baseline、消融实验和论文式分析。

系统职责：

```text
已有数据 / 代码 / 结果输入
  -> 代码结构理解
  -> 数据和实验配置审计
  -> 检查数据泄漏、指标缺失和复现风险
  -> 检索文献代码 baseline
  -> 补充 baseline 复现
  -> 补充消融实验
  -> 生成错误分析和结果解释
  -> 生成报告和论文段落
```

该模式不是从零生成实验，而是帮助用户补全科研验证矩阵，使已有工作更可复现、更可信、更符合比赛报告规范。

## 4. v3 总体架构

v3 的架构不再是 v1/v2 的线性流水线，而是一个**有分支、循环和回退的五层嵌套图结构**。

### 4.1 五层架构图

```text
┌─────────────────────────────────────────────────────┐
│  Layer 0: Intent Router                              │
│  conditional edge → 分支到三种科研模式                │
│  Discovery / Idea Refinement / Experiment Assistance │
├─────────────────────────────────────────────────────┤
│  Layer 1: Hypothesis Arena                           │
│  竞技/辩论层 — 纯LLM推理，低成本                      │
│  Discovery: 排名竞技（N→Critic→Top2）                 │
│  Idea Refinement: 消融式竞技（用户创意 vs 挑战者）     │
│  Experiment Assistance: 不需要竞技                    │
├─────────────────────────────────────────────────────┤
│  Layer 2: Code Experiment                            │
│  双层ReAct — 代码执行层，高成本                       │
│  内层: 微观ReAct（写→跑→报错→修→重跑，max 5次）      │
│  外层: 宏观ReAct（实验→评估→诊断→修改→重跑，max 3轮） │
├─────────────────────────────────────────────────────┤
│  Layer 3: Hypothesis Switchback                      │
│  回退层 — 实验彻底失败时切换候选假设                   │
│  Top1失败 → 切换Top2 → 重新进入Layer 2               │
│  Top2也失败 → 输出 negative result                   │
├─────────────────────────────────────────────────────┤
│  Layer 4: Report                                     │
│  确定性输出 — 组装报告 + claim audit                   │
└─────────────────────────────────────────────────────┤
```

### 4.2 LangGraph 概念映射

当前 v1/v2 的编排是手写 `ScientistWorkflow` 中的 `await fn()` 链式调用。v3 引入 LangGraph StateGraph 后，每个架构层对应以下 LangGraph 概念：

| 架构概念 | LangGraph 实现 | 当前代码对应 |
|----------|---------------|-------------|
| Layer 0 分支 | `add_conditional_edges("intent_router", route_fn)` | 不存在（当前是线性） |
| Layer 1 竞技 | 多个 LLM node + 评分排序 node | `HypothesisAgent → CriticAgent → RevisionAgent`（线性链） |
| Layer 2 内层循环 | cyclic subgraph: `code_debug` → `run_code` → `evaluate_error` → `fix_code` → back | 不存在 |
| Layer 2 外层循环 | cyclic subgraph: `experiment` → `evaluate` → `diagnose` → `revise` → back | `§6.11 Feedback Loop`（只写了概念，没写循环机制） |
| Layer 3 回退 | conditional edge: `should_switchback` → "switchback" or "abort" | 不存在 |
| Layer 4 输出 | 顺序 node chain | `ReportWriterAgent` → `ClaimVerifier` |
| 人工暂停 | `interrupt()` + `Command(resume=...)` | `_pause_for_human()` |
| 状态管理 | State channel: `Annotated[ResearchRun, replace]` | `ResearchRun` 直接修改 |
| checkpoint | `MemorySaver` 或数据库 checkpointer | `run_store.save()` |

### 4.3 各模式的主流程

**Discovery Mode**：

```text
User Input (模糊方向)
  → Intent Router [conditional edge]
  → Research Planner
  → Literature & Data Acquisition
  → Citation Verification
  → Evidence Engine
  → Hypothesis Arena [排名竞技: 生成N个假设 → 多视角Critic并行评分 → 排名 → Top2进入Revision]
  → Literature-Grounded Baseline Discovery
  → Seismic Experiment Designer
  → Code Experiment Loop [微观ReAct + 宏观ReAct]
  → Result Evaluator
      → Pass: Ablation → Report
      → Fail: Diagnosis → 修改重跑 [宏观ReAct循环]
      → 假设不可修复: Hypothesis Switchback [回退到排名第2假设]
  → Report Generator
```

**Idea Refinement Mode**：

```text
User Input (已有创意)
  → Intent Router [conditional edge]
  → Idea Intake Agent [结构化用户创意]
  → Novelty / Related Work Checker
  → Hypothesis Arena [消融式竞技: H_main(用户创意) vs H_challenge1 vs H_challenge2 vs H_challenge3]
  → Literature & Data Acquisition (围绕用户创意检索)
  → Citation Verification
  → Evidence Engine
  → Literature-Grounded Baseline Discovery
  → Fair Comparison Planner
  → Code Experiment Loop [微观ReAct + 宏观ReAct]
  → Result Evaluator
      → Pass: Ablation验证H_main的创新点 → Report
      → Fail: Diagnosis → 修改重跑
      → 竞技揭示创新点冗余: 修改H_main → 重跑
  → Report Generator
```

**Experiment Assistance Mode**：

```text
User Input (已有数据/代码/结果)
  → Intent Router [conditional edge]
  → Code & Data Audit Agent
  → Literature & Data Acquisition (补baseline)
  → Citation Verification
  → Baseline Discovery & Reproduction
  → Fair Comparison Planner
  → Code Experiment Loop [微观ReAct调试用户代码 + 补跑baseline]
  → Ablation Agent
  → Result Interpreter
  → Report Generator
```

### 4.4 共用节点

三种模式共用以下节点（LangGraph node），只是进入顺序和部分输入不同：

- Research Planner
- Literature Router
- Citation Verifier
- Evidence Ledger
- Literature Miner
- Report Writer
- Claim Verifier

这些共用节点的接口设计必须保持 domain-agnostic，不绑定地震或材料方向。

## 5. 地震事件分类 demo 定义

### 5.1 主任务

v3 的主 demo 任务聚焦地震事件分类：

> 基于地震波形数据和已有文献方法，研究深度学习模型在地震事件分类中的可验证改进路径，重点区分自然地震、人工爆破/爆炸、塌陷或冲击类事件、噪声等类别。

架构设计保持 domain-agnostic：地震是 v3 的主要 demo domain，能源材料方向作为保留的第二 domain，两者在 ScientificDataAgent 下用 adapter 模式共存（见 §6.3）。

### 5.2 标签范围

MVP 推荐优先使用可获得公开数据支持的标签：

- natural earthquake。
- quarry blast / explosion。
- collapse / induced / impact-like event。
- noise / non-event。

飞机失事等极罕见冲击事件可作为扩展场景或 out-of-distribution event detection，不建议作为 MVP 主标签，除非有真实公开数据和可靠标注。

### 5.3 数据输入形态

系统需要支持或规划支持：

- 单台站或多台站波形。
- 三分量波形：Z/N/E 或 Z/1/2。
- sampling rate。
- event window。
- station metadata。
- event label。
- event time。
- spectrogram / time-frequency representation。
- train / validation / test split。

### 5.4 推荐实验问题

示例问题：

1. 多通道三分量波形是否优于单通道垂直分量？
2. 原始波形模型与时频图模型在地震/爆破分类上差异如何？
3. 波形 + 时频图双分支融合是否能提升 macro-F1？
4. 类别不平衡处理是否能改善少数类事件识别？
5. 按台站划分的测试是否暴露模型泛化风险？
6. 用户提出的创新模块是否在消融实验中带来稳定贡献？

## 6. 新增核心模块

### 6.1 Intent Router

作用：判断用户输入属于哪种科研入口。这是整个 v3 工作流的**第一个 conditional edge**，决定后续走哪个分支。

在 LangGraph 中对应 `add_conditional_edges("intent_router", route_fn)`。

输出：

```json
{
  "mode": "discovery | idea_refinement | experiment_assistance",
  "confidence": 0.87,
  "reason": "...",
  "required_inputs": ["question", "dataset", "code_path"]
}
```

判断依据：

- 用户是否只有方向。
- 用户是否已经提出明确方法或假设。
- 用户是否已有数据、代码或结果。
- 用户是否要求补 baseline、消融或报告。

### 6.2 Idea Intake Agent

作用：把用户已有创意结构化，特别服务于 Idea Refinement Mode。

输出：

```json
{
  "research_problem": "地震事件分类",
  "user_idea": "多通道波形与时频图融合",
  "target_task": "earthquake/explosion/noise classification",
  "input_data": ["three-component waveform", "spectrogram"],
  "expected_contribution": "提升爆破与自然地震的可分性",
  "unknowns": [
    "公开数据是否包含目标标签",
    "是否已有相似融合模型",
    "baseline 代码是否可复现"
  ]
}
```

### 6.3 Scientific Data Agent + Domain Adapter

架构设计保持 domain-agnostic，通过 adapter 模式支持多个领域。地震事件分类是 v3 主 domain，能源材料方向作为保留的第二 domain。

推荐结构：

```text
ScientificDataAgent (统一入口)
  -> SeismicDataAdapter (v3 主 adapter — 地震事件分类)
  -> MaterialsDataAdapter (v1/v2 保留 — 固态电解质等)
  -> LocalCsvAdapter (通用 — 用户上传CSV)
```

SeismicDataAdapter 专门处理地震数据可用性和实验数据 profile。

能力：

- 读取地震事件元数据。
- 读取或描述 waveform 数据。
- 统计事件类别分布。
- 检查采样率、窗口长度、通道完整性。
- 生成 train / validation / test split。
- 标记类别不平衡风险。
- 标记跨台站泛化风险。
- 生成 seismic dataset profile。

输出示例：

```json
{
  "dataset_name": "demo_seismic_events",
  "num_events": 1200,
  "labels": {
    "earthquake": 600,
    "explosion": 350,
    "noise": 250
  },
  "channels": ["Z", "N", "E"],
  "sampling_rate": 100,
  "window_seconds": 30,
  "split_strategy": "event_level | station_level",
  "risks": ["class imbalance", "station leakage"]
}
```

### 6.4 Novelty / Related Work Checker

作用：检索和分析与用户方向或创意最接近的已有工作。

输出：

- 相似论文列表。
- 是否有公开代码。
- 方法重合点。
- 用户创意的可保留创新点。
- 需要降低表述的 claim。
- 推荐优化方向。

### 6.5 Literature-Grounded Baseline Discovery Agent

这是 v3 的关键新增模块。baseline 不应主要由系统随便自写，而应优先来自真实文献及其公开代码。

baseline 可信度分层：

```text
Tier 1: 论文 + 官方 GitHub / 官方代码
Tier 2: 论文 + 第三方复现代码
Tier 3: 论文有完整方法细节，系统做 reimplementation
Tier 4: 通用 ML / DL baseline，仅作为 fallback
```

系统原则：

> 优先检索带公开代码的地震事件分类相关论文，将其作为可复现 baseline；只有当公开代码不可用时，才退回到论文复现或通用 baseline。

baseline 代码信息源需要明确记录 provenance，MVP 至少考虑以下来源：

1. paper metadata 中的 code link、project page 或 supplementary link。
2. arXiv 页面、论文 PDF、作者主页中的 repository 链接。
3. Papers with Code 或类似论文-代码索引。
4. GitHub search：使用论文标题、方法名、作者名、任务名进行检索。
5. README / paper title matching：判断 repo README 是否明确引用目标论文或方法。
6. 用户手动提供 repo URL：允许用户指定 baseline 仓库，并进入相同验证流程。

每个 baseline candidate 必须记录 code source，不允许只写“有 GitHub”而没有来源说明。

Baseline Candidate schema：

```json
{
  "baseline_id": "baseline_001",
  "paper_title": "...",
  "paper_doi": "...",
  "paper_url": "...",
  "code_url": "https://github.com/...",
  "code_source": "official | third_party | paperswithcode | reimplementation | fallback",
  "task_match": "seismic event classification",
  "input_type": "waveform | spectrogram | multi_channel_waveform",
  "labels_supported": ["earthquake", "explosion", "noise"],
  "dataset_used": "...",
  "metrics_reported": ["accuracy", "macro_f1"],
  "reproducibility_score": 0.82,
  "license": "...",
  "run_command": "...",
  "risks": ["dependency version unclear", "dataset unavailable"]
}
```

### 6.6 Repository Verifier

作用：验证 baseline 代码仓库是否真实、可访问、可复现。

检查项：

- repo 是否存在。
- repo 是否与论文匹配。
- README 是否包含运行说明。
- requirements / environment 是否存在。
- license 是否可用。
- 是否有 pretrained model 或 dataset script。
- 是否有 commit hash。
- 是否有明确输入输出。
- 是否可以在本地或容器中运行。

安全边界：

- 不允许直接在主项目目录中运行未经审计的外部 GitHub 代码。
- baseline repo 必须 clone / unpack 到隔离目录，例如 `data/external_baselines/{baseline_id}/` 或专用临时 workspace。
- 推荐使用容器、受限虚拟环境或专用 runner 执行 baseline。
- 默认限制外部代码的写路径，只允许写入该 baseline 的 workspace、logs 和 artifacts 目录。
- 默认禁止或严格限制外部代码运行时网络访问；如必须联网下载模型或数据，需要用户确认并记录原因。
- 只执行经过 Repository Verifier 生成和展示的明确命令，不执行 repo 中自动发现的任意脚本。
- 运行前记录 command、working directory、environment、commit hash、dependency file 和 expected outputs。
- 运行后记录 stdout/stderr、exit code、生成文件和失败原因。

这些限制是 v3 代码实验闭环的强制安全要求，避免 AI Scientist 变成不受控的外部代码执行器。

### 6.7 Baseline Reproduction Agent

作用：复现文献 baseline，或生成复现失败说明。

输出：

- baseline run status。
- command。
- dependency status。
- dataset compatibility。
- metrics。
- logs。
- failure reason。
- fallback recommendation。

### 6.8 Fair Comparison Planner

作用：保证用户方法和 baseline 的对比是公平的。

检查项：

- 是否使用同一数据集。
- 是否使用同一 train / validation / test split。
- 是否使用同一 preprocessing。
- 是否使用同一 metrics。
- 是否比较相同标签集合。
- 是否报告参数量、训练成本或推理成本。
- 是否存在数据泄漏。

### 6.9 Code Experiment Loop

作用：把假设或用户创意转成可执行代码实验。

Code Experiment Loop 不等于让 LLM 每次从零随意写代码，而是在受控实验框架内生成、修改和运行代码。

该模块包含**双层 ReAct 结构**：

#### 内层循环：微观 ReAct（代码调试）

```text
Generate / Adapt Code
  → Run Code
      → Success: collect metrics, proceed to macro evaluation
      → Error: observe error message (import? shape? config? dependency?)
          → Reason: LLM诊断错误类型和修复方案
          → Act: patch code (limited scope: 依赖/配置/小结构修改)
          → Re-run
          → Still fails after max_code_debug_attempts (5次):
              → log failure, fallback to simpler implementation or ask user
```

微观 ReAct 的约束：

- 每次只做局部修改（不允许整段重写）
- 修改范围限定为：依赖缺失、数据维度、配置参数、小范围结构修复
- 最多 5 次代码调试迭代
- 超过上限后输出 `CodeDebugFailure` 记录，进入宏观 ReAct 的诊断环节

#### 外层循环：宏观 ReAct（实验反馈）

```text
Run Experiment (代码已通过微观调试)
  → Evaluate Result (Result Evaluator Agent)
      → Pass: proceed to ablation → report
      → Fail: Diagnosis (数据/模型/假设/复现 问题)
          → 修改方案 → 修改代码/数据/超参/假设表述
          → 回到微观ReAct重新调试代码 → 重新跑实验
          → 最多 3 轮宏观迭代
      → 假设不可修复: 进入 Hypothesis Switchback (§6.X)
```

宏观 ReAct 的约束见 §6.11。

#### 推荐目录结构

```text
experiments/seismic_event_classification/
  configs/
    baseline_literature.yaml
    proposed_fusion.yaml
    ablation_waveform_only.yaml
    ablation_spectrogram_only.yaml

  data/
    prepare_dataset.py
    dataset.py
    transforms.py

  models/
    baseline_adapter.py
    cnn1d.py
    spectrogram_cnn.py
    fusion_net.py

  train.py
  evaluate.py
  run_ablation.py
  result_card.py
  README.md
```

#### 完整阶段序列

```text
Experiment Specification
  → Code Planning (LLM: 根据假设和baseline设计代码结构)
  → Baseline Code Audit / Reproduction
  → Proposed Method Implementation
  → [微观ReAct循环: 调试代码直到能跑通]
  → Training / Evaluation
  → Result Card
  → [宏观ReAct循环: 评估结果 → 诊断 → 修改 → 重跑]
  → Ablation (通过后)
  → Result Interpretation
```

### 6.10 Hypothesis Arena — 竞技与辩论

v1/v2 的 Hypothesis Arena 是"生成→批判→修订"的线性链条。v3 根据科研模式引入两种竞技机制。

#### Discovery Mode：排名竞技

适用场景：用户只有模糊方向，系统从零生成多个候选假设。

流程：

```text
Hypothesis Generation Agent 生成 N 个候选假设 (N=3~5)
  → 每个假设被 3 个不同视角的 Critic Agent 并行批判
      Domain Scientist Critic: 评估科学意义和领域贡献
      ML / Experiment Critic: 评估数据可行性和验证路径
      Skeptical Reviewer Critic: 评估风险和过度声明
  → 每个 Critic 对每个假设在 8 个维度打分 (novelty, verifiability, data_availability, feasibility, evidence_support, reproducibility, competition_fit, self_consistency)
  → 多维度加权汇总排名（权重按比赛评分维度调整）
  → 排名结果:
      H1: 综合85 → Top1
      H2: 综合62 → 排名靠后
      H3: 综合70 → Top2
  → Top 1~2 进入 Revision Agent 修订表述
  → 修订后再排名确认
  → 最终 Top1 进入 Code Experiment Loop (Layer 2)
  → Top2 作为 Hypothesis Switchback (Layer 3) 的备选
```

排名竞技只在 LLM 层面执行（纯推理，成本低），代码实验只对 Top1 执行（GPU+数据，成本高）。两者成本分离。

#### Idea Refinement Mode：消融式竞技

适用场景：用户已有创意，系统围绕创意验证每个创新点的贡献。

流程：

```text
Idea Intake Agent 把用户创意结构化为 H_main (核心假设)
  → Novelty Checker 检索相似工作
  → 系统基于 H_main 的创新点拆解生成消融挑战者:
      H_challenge1: 去掉创新点A（例如：去掉时频图分支，只用波形）
      H_challenge2: 去掉创新点B（例如：去掉融合模块，只用简单concat）
      H_challenge3: 用更简单的替代方案（例如：用PCA代替创新模块）
  → H_main vs H_challenge1 vs H_challenge2 vs H_challenge3 进入竞技
  → 竞技规则不同于 Discovery:
      H_main 有特权位 — 竞技目标不是替代用户创意
      挑战者的作用是验证 H_main 的每个创新点是否真的有贡献
      如果某挑战者与 H_main 效果接近 → 说明该创新点可能是冗余的
  → 竞技结果不选"哪个赢"，而是输出:
      "H_main 在哪些维度上确实比挑战者强"
      "哪些挑战者说明 H_main 的某些创新点是冗余的"
      "哪些创新点有真实贡献 → 应保留在实验中"
      "哪些创新点可能冗余 → 应在消融实验中验证"
  → H_main 进入 Code Experiment Loop
  → 有威胁的挑战者作为消融实验候选 (不是单独跑实验，而是在H_main实验框架内做消融)
```

消融式竞技的优势：**竞技本身就包含了消融设计**。不需要先跑完 H_main 再单独设计消融实验，竞技过程已经告诉你哪些消融实验值得做。

#### Experiment Assistance Mode：不需要竞技

用户已有假设和代码，竞技不适用。此模式直接进入代码审计和 baseline 补充。

#### 完整 Elo 竞技升级路径（MVP 后升级选项）

当前 MVP 使用简化排名（Critic 多维度加权评分→排名→Top1+Top2）和消融式竞技（H_main vs 挑战者）。以下描述完整 Elo 竞技机制，作为 MVP 确认后的升级选项。实施时可以选择逐步升级或直接升级。

##### Discovery Mode 完整 Elo 竞技

完整 Elo 竞技引入三个 MVP 中没有的环节：**Pairwise 对战、假设进化、弱者淘汰**。

```text
Round 1: 假设生成
  Generation Agent 生成 N 个候选假设 (N=3~5)

Round 2: 首轮 Critic 评分 → Elo 初始化
  3视角Critic并行评分 → 加权分数作为初始Elo值
  (MVP的简化排名就是这一步)

Round 3: Pairwise 对战 → Elo 动态更新 (MVP升级点)
  LLM Judge 对每对假设做 pairwise 比较:
    "H1 vs H2: H1的数据可行性更高, H2的单通道信息不够"
    → H1胜 → H1 Elo+20, H2 Elo-20
  N个假设 = C(N,2) 对 pairwise 对战
  优势: pairwise 能发现"A整体分数高但B在某关键维度更强"的细微差异
  这种差异在加权排名中可能被淹没

Round 4: 假设进化 (MVP升级点)
  排名最低的1~2个假设淘汰
  排名最高的2个假设由 Evolution Agent 做有针对性修改:
    "根据Critic和pairwise揭示的弱点, 强化H1的数据可行性表述"
    "根据对战揭示的H3的novelty优势, 优化H3的验证路径"
  进化后的假设重新进入 pairwise 对战 → Elo 再次更新

Round 5: 最终排名确认
  → Top1 进入 Code Experiment Loop
  → Top2 作为 Switchback 备选
  → 淘汰的假设不进入实验（不浪费GPU资源）
```

LLM 调用成本估算：

| 环节 | LLM调用次数 | 说明 |
|------|------------|------|
| Round 1 假设生成 | N×1 = 5次 | Generation Agent |
| Round 2 Critic评分 | N×3 = 15次 | 3视角Critic并行 |
| Round 3 Pairwise对战 | C(N,2)×1 = 10次 | LLM Judge每对1次 |
| Round 4 进化+对战 | 2(进化)+C(3,2)(对战) = 5次 | 淘汰2个后3个再对战 |
| **总计** | **约35次LLM调用** | vs MVP简化排名的15次 |

代码实验成本：仍然只对 Top1 执行1次实验，Switchback 最多1次额外实验。总计最多2次实验，与 MVP 相同。

##### Idea Refinement Mode 完整 Elo 竞技

用户创意有特权初始 Elo，挑战者需要通过 pairwise 对战证明自己才能提升排名。

```text
Round 1: 用户创意结构化 + 挑战者生成
  H_main 特权初始 Elo=1600（用户创意优先）
  挑战者初始 Elo=1500（需要证明自己）

Round 2: Pairwise 对战 — 验证创新点 (MVP升级点)
  H_main vs H_challenge1:
    "去掉时频图后预计macro-F1下降3-5%"
    → H_main胜(+15 Elo), H_challenge1败(-15 Elo)
    → 标记: 创新点"时频图分支" → 有真实贡献 ✅

  H_main vs H_challenge2:
    "简单concat vs 融合模块差异预计不大"
    → 差距很小 → H_main胜(+5 Elo), H_challenge2败(-5 Elo) (小分差)
    → 标记: 创新点"融合模块" → 可能冗余 ⚠️

  H_main vs H_challenge3:
    "去掉波形后预计下降明显"
    → H_main胜(+15 Elo), H_challenge3败(-15 Elo)
    → 标记: 创新点"波形通道" → 有真实贡献 ✅

  优势: pairwise 给出分差大小，不只是"谁赢谁输"
  分差大 → 创新点贡献明确
  分差小 → 创新点可能冗余 → 应做消融验证
  MVP的简化排名只给出"有贡献"或"可能冗余"二分判断

Round 3: H_main 进化 (MVP升级点)
  Pairwise揭示"融合模块可能冗余"
  → Evolution Agent修改H_main:
    "波形+时频图, 用concat而非融合模块作为消融对照"
  → H_main_evolved vs 挑战者再比较 → 确认进化后表述更精确

Round 4: 最终排名
  → H_main_evolved Elo≈1635 → 竞技赢家（用户创意强化版）
  → 竞技结论输出:
      ✅ 时频图分支: 大分差胜 → 有真实贡献 → 保留
      ⚠️ 融合模块: 小分差胜 → 可能冗余 → 作为消融验证
      ✅ 波形通道: 大分差胜 → 有真实贡献 → 保留
```

##### MVP 简化排名 vs 完整 Elo 的适用场景判断

| 场景 | 推荐竞技层级 | 理由 |
|------|------------|------|
| 假设方向差异大（不同领域/方法路线） | MVP简化排名 | 加权排名已经能准确判断，pairwise不会给出更多信息 |
| 假设方向相似但细节不同（同路线不同变体） | 完整Elo | pairwise能揭示细微差异，加权排名可能被单一维度主导 |
| Idea Refinement 验证用户创意 | MVP简化 → 需要时升级Elo | 简化排名能判断"有贡献/可能冗余"，Elo能给出贡献程度 |
| 竞赛评审看重novelty和verifiability | 完整Elo | pairwise比加权排名更贴近真实评审的"对比式评价" |

##### 升级实施方式

**逐步升级（推荐）**：MVP 先用简化排名跑通完整流程，确认 Hypothesis Arena 的输入输出接口稳定后，在 Arena 内部替换排名算法为 Elo（只改 Arena 内部逻辑，不改接口）。

**直接升级**：如果 MVP 验证时发现简化排名的判断精度不够（比如 Top1 和 Top2 分数差异很小，难以决定选哪个），直接在 Sprint V3-1 或 V3-2 引入 Pairwise对战和Evolution。

升级需要的额外 Agent：

| Agent | MVP是否需要 | 升级Elo是否需要 | 说明 |
|-------|------------|----------------|------|
| Critic Agent (多视角评分) | ✅ 需要 | ✅ 需要（不变） | Elo 用 Critic 分数初始化 |
| LLM Judge Agent (pairwise 比较) | ❌ 不需要 | ✅ 需要新增 | 对每对假设做 pairwise 判断 |
| Evolution Agent (假设进化) | ❌ 不需要 | ✅ 需要新增 | 针对性修改排名高的假设 |
| Ranking/Elo Engine | ✅ 需要(加权排名) | ✅ 需要(改为Elo计算) | 排名算法替换，接口不变 |

#### 竞技与 LangGraph 的对应

MVP 简化排名竞技在 LangGraph 中对应多个并行 LLM node + 评分排序 node：

```python
# Discovery 简化排名竞技 (MVP概念示意)
graph.add_node("generate_hypotheses", hypothesis_gen_node)  # 生成N个假设
graph.add_node("critic_parallel", critic_parallel_node)     # 3视角Critic并行批判
graph.add_node("rank_hypotheses", ranking_node)             # 加权排名
graph.add_node("revise_top_candidates", revision_node)      # Top1~2修订
graph.add_conditional_edges("rank_hypotheses", route_by_mode, {
    "discovery": "revise_top_candidates",
    "idea_refinement": "ablation_competition",
})
```

完整 Elo 竞技升级后在 LangGraph 中对应 cyclic subgraph（进化→对战→排名→再进化）：

```python
# Discovery 完整Elo竞技 (升级后概念示意)
elo_graph = StateGraph(WorkflowState)
elo_graph.add_node("generate_hypotheses", hypothesis_gen_node)
elo_graph.add_node("critic_initial", critic_parallel_node)        # Round2: Critic评分→Elo初始化
elo_graph.add_node("pairwise_judge", pairwise_judge_node)         # Round3: pairwise对战
elo_graph.add_node("elo_update", elo_update_node)                 # Elo分数更新
elo_graph.add_node("eliminate_weak", eliminate_node)              # Round4前: 淘汰弱者
elo_graph.add_node("evolve_strong", evolution_node)               # Round4: 进化强者
elo_graph.add_node("final_rank", final_ranking_node)              # Round5: 最终排名

elo_graph.add_edge("generate_hypotheses", "critic_initial")
elo_graph.add_edge("critic_initial", "pairwise_judge")
elo_graph.add_edge("pairwise_judge", "elo_update")
elo_graph.add_conditional_edges("elo_update", should_continue_elo, {
    "continue": "eliminate_weak",   # Elo未收敛 → 淘汰+进化+再对战
    "converged": "final_rank",      # Elo收敛 → 最终排名
})
elo_graph.add_edge("eliminate_weak", "evolve_strong")
elo_graph.add_edge("evolve_strong", "pairwise_judge")  # 进化后重新pairwise → 循环
```

#### 竞技输出 Schema

MVP 简化排名输出：

```json
{
  "arena_id": "arena_001",
  "mode": "discovery | idea_refinement",
  "arena_level": "simplified_ranking | elo_tournament",
  "candidates": [
    {
      "hypothesis_id": "H1",
      "statement": "...",
      "critic_scores": {
        "domain_scientist": {"novelty": 8, "verifiability": 9, ...},
        "ml_critic": {"data_availability": 8, ...},
        "skeptical_reviewer": {"risk": 6, ...}
      },
      "weighted_score": 85,
      "elo_rating": null,
      "rank": 1,
      "is_user_idea": false
    }
  ],
  "ranking": ["H1", "H3", "H2"],
  "selected_for_experiment": "H1",
  "switchback_candidate": "H3",
  "pairwise_results": null,
  "evolution_history": null,
  "ablation_design": [
    {"challenge_id": "H_challenge1", "tests_innovation_point": "时频图分支", "expected_insight": "验证波形+时频图融合是否优于纯波形"}
  ]
}
```

完整 Elo 竞技输出（升级后）：

```json
{
  "arena_id": "arena_001",
  "mode": "discovery",
  "arena_level": "elo_tournament",
  "candidates": [
    {
      "hypothesis_id": "H1",
      "statement": "...",
      "critic_scores": { ... },
      "weighted_score": 85,
      "elo_rating": 1620,
      "elo_history": [1550, 1580, 1620],
      "rank": 1,
      "is_user_idea": false
    }
  ],
  "ranking": ["H1_evolved", "H3_evolved", "H5"],
  "selected_for_experiment": "H1_evolved",
  "switchback_candidate": "H3_evolved",
  "pairwise_results": [
    {"pair": ["H1", "H2"], "winner": "H1", "reason": "H1数据可行性更高", "score_diff": 20},
    {"pair": ["H1", "H3"], "winner": "H1", "reason": "H1 novelty更高", "score_diff": 15},
    {"pair": ["H_main", "H_challenge2"], "winner": "H_main", "reason": "融合模块可能冗余", "score_diff": 5}
  ],
  "evolution_history": [
    {"from": "H1", "to": "H1_evolved", "changes": "更精确绑定数据集和指标", "rationale": "Critic揭示数据可行性表述模糊"}
  ],
  "ablation_design": [ ... ]
}
```

两个 Schema 通过 `arena_level` 字段区分，接口统一。前端可根据 `arena_level` 决定展示简化排名表格还是 Elo 对战矩阵。

### 6.11 Result Evaluator Agent

作用：评估 proposed method 是否真正优于 baseline，以及是否支持假设。

评估维度：

- proposed method 是否超过文献 baseline。
- accuracy 是否提升。
- macro-F1 是否提升。
- minority class F1 是否下降。
- confusion matrix 是否改善目标混淆。
- 训练/验证差距是否过大。
- 是否存在数据泄漏。
- 消融是否证明新增模块有贡献。
- 当前结果能否支撑报告中的 claim。

示例通过条件：

```text
- proposed macro-F1 >= best baseline macro-F1 + 1% 或 2%
- minority class F1 不下降
- 目标类别混淆减少
- 消融实验显示关键模块有正贡献
- 不存在明显数据泄漏
```

### 6.12 Hypothesis Switchback — 实验失败时的假设回退

作用：当 Code Experiment Loop 的宏观 ReAct 迭代耗尽（3轮都失败），且诊断结论指向"假设本身不被数据支持"时，系统回退到 Hypothesis Arena 的排名第2假设，重新进入实验。

这是 v3 新增的回退机制，连接 Layer 1（竞技）和 Layer 2（实验），形成外层闭环。

流程：

```text
宏观 ReAct 第3轮仍失败
  → Result Evaluator 输出判断:
      "假设不可修复" (not fixable by code/data/hyperparam changes)
  → 进入 Hypothesis Switchback
      → 如果 arena 排名中有 switchback_candidate (Top2):
          → 切换到 Top2 假设
          → 用已有 baseline 代码 + 新假设重新设计实验
          → 重新进入 Layer 2 (Code Experiment Loop)
      → 如果没有备选假设 (Discovery只生成了1个, 或 Idea Refinement只有H_main):
          → 输出 negative result / partial support
          → 不包装成成功
          → 在报告中标注 "假设未被实验结果支持"
```

约束：

- Switchback 最多执行 1 次（只回退到 Top2，不继续回退到 Top3）
- 切换假设后重新进入实验，宏观 ReAct 重置迭代计数（允许3轮新实验）
- Idea Refinement 模式的 Switchback 需要用户确认（`interrupt()`），因为用户的创意是目标，不能自动替换

与 LangGraph 的对应：

```python
# Hypothesis Switchback (概念示意)
graph.add_conditional_edges("evaluate_result", should_continue, {
    "pass": "ablation",                    # 通过 → 消融
    "fail_fixable": "diagnose_and_revise", # 可修复 → 诊断修改
    "fail_unfixable_with_backup": "switchback",  # 不可修复但有备选 → 切换假设
    "fail_unfixable_no_backup": "negative_result", # 不可修复且无备选 → 输出negative
    "max_iterations": "negative_result",   # 超过3轮 → 输出negative
})
### 6.13 Experiment Feedback Loop — 宏观 ReAct 约束

宏观 ReAct 的详细约束规则。此循环对应 §6.9 Code Experiment Loop 的外层循环。

流程：

```text
Run Experiment (代码已通过微观调试)
  → Evaluate Result (Result Evaluator §6.11)
      → Pass: Ablation + Report
      → Fail: Diagnosis → 判断失败类型
          → 数据问题: 修改数据划分/预处理/类别权重 → 回到微观ReAct修代码 → 重跑实验
          → 模型问题: 调整超参/简化结构/修改训练策略 → 回到微观ReAct修代码 → 重跑实验
          → 假设问题: 假设不被结果支持 → 进入 Hypothesis Switchback (§6.12)
          → 复现问题: baseline跑不通 → 切换fallback baseline → 回到微观ReAct修代码 → 重跑实验
          → 最多 3 轮宏观迭代
      → 3轮后仍失败且无备选假设: 输出 negative result / partial support
```

每轮必须记录：

- 修改了什么。
- 为什么修改。
- 指标如何变化。
- 是否更接近目标。
- 是否需要用户批准继续（Idea Refinement 模式通过 `interrupt()` 等待用户确认）。

如果多轮后仍失败，应输出 negative result / partial support，而不是包装成成功。

### 6.14 Result Interpreter

作用：把实验结果转成科研报告语言。

输出：

- 假设是否被支持。
- 哪些证据支持。
- 哪些指标提升。
- 哪些类别仍混淆。
- 哪些消融支持创新点。
- 哪些结论只能写成 preliminary。
- 下一步实验建议。

## 7. 三种模式与代码实验的关系

三种模式都可以进入代码实验闭环，但起点和竞技机制不同。

### Discovery Mode

```text
系统生成 N 个假设
  -> 假设竞技排名 (排名竞技)
      -> Top1 和 Top2 进入 Revision
  -> 找文献 baseline
  -> 复现 baseline
  -> 写 Top1 的 proposed method
  -> 微观ReAct调试代码 + 宏观ReAct实验迭代
  -> 评估结果
      -> Pass: 消融验证 + 报告
      -> Fail可修复: 修改重跑 (宏观ReAct最多3轮)
      -> Fail不可修复: Hypothesis Switchback回退到Top2
```

### Idea Refinement Mode

```text
用户提供创意 -> 结构化为 H_main
  -> 系统生成消融挑战者 (H_challenge1, H_challenge2, H_challenge3)
  -> 消融式竞技 (H_main vs 挑战者)
      -> 确认H_main哪些创新点有真实贡献
      -> 确认哪些创新点可能冗余 → 设计消融实验
  -> 找最接近的文献 baseline
  -> 判断用户创意比 baseline 多什么
  -> 写用户方法代码
  -> 微观ReAct调试代码 + 宏观ReAct实验迭代
  -> 公平对比
  -> 消融验证竞技揭示的创新点
  -> 评估结果
      -> Pass: 报告
      -> Fail: 诊断修改 + 宏观ReAct迭代
      -> 创新点冗余确认: 修改H_main + 用户确认 (interrupt())
```

### Experiment Assistance Mode

```text
用户已有代码 / 数据 / 结果
  -> 系统审计现有实验
  -> 找缺失文献 baseline
  -> 补跑 baseline 或消融
  -> 解释结果
  -> 生成报告
```

一句话总结：

```text
A: 系统帮用户找想法，并写代码验证。
B: 系统帮用户打磨已有想法，并写代码验证。
C: 系统帮用户补全已有实验，并写论文/报告。
```

## 8. 报告输出规范

最终报告仍需满足赛题 PDF 要求。

### 8.1 必须字段

- Problem Statement。
- Rationale。
- Technical Details。
- Datasets。
- Source。
- Target。
- Paper Title。
- Paper Abstract。
- Methods。
- Experiments。
- Results。
- References。

### 8.2 v3 新增报告字段

建议在报告中新增以下审计字段：

#### Baseline Provenance

说明 baseline 来源：

- baseline 来自哪篇论文。
- 论文是否 verified。
- repo URL。
- 是否官方代码。
- 使用的 commit hash。
- 是否修改代码。
- 是否成功运行。
- 是否使用同一数据、split、metrics。
- 复现失败原因和 fallback。

#### Experiment Iteration Log

记录多轮实验：

- 第 1 轮：原始方法结果。
- 第 2 轮：修正数据划分、类别权重或模型结构后的结果。
- 第 3 轮：进一步消融或方法修正后的结果。
- 最终判断：支持 / 部分支持 / 未支持。
- 如果发生 Hypothesis Switchback：记录切换原因、新假设表述、重新实验的结果。

#### Code Debug Log

记录微观 ReAct 代码调试：

- 每次代码调试的错误类型、诊断、修复方案。
- 代码 diff。
- 调试后运行结果（success / still_error / new_error）。
- 最多 5 次调试迭代的完整记录。

#### Hypothesis Arena Report

记录竞技过程：

- Discovery Mode：所有候选假设、每个Critic的评分、排名结果、Top1和Top2选择理由。
- Idea Refinement Mode：H_main vs 挑战者的对比、每个创新点的竞技结论、消融设计建议。

#### Ablation Report

记录关键消融：

- 单通道 vs 三通道。
- waveform vs spectrogram。
- 无融合 vs 融合。
- 无 attention vs attention。
- 无类别重采样 vs 类别重采样。
- 随机 split vs station-level split。

#### Result Support Judgment

明确报告：

- 实验结果是否支持假设。
- 支持到什么程度。
- 哪些 claim 有证据。
- 哪些 claim 仍待验证。

## 9. 前端工作台 v3

### 9.1 双版本入口设计

前端左边栏顶部增加**版本切换器**，用户可选择进入两种工作流：

```text
┌──────────────────────────────────┐
│  TrustSci Agent                  │
│                                  │
│  ┌────────────────┐ ┌──────────┐ │
│  │ Classic Workflow│ │ Seismic  │ │
│  │ 经典科研工作流   │ │ Expert   │ │
│  │ (v1/v2 基础版) │ │ 地震科研  │ │
│  │                │ │ 专家(v3) │ │
│  └────────────────┘ └──────────┐ │
│                                  │
│  [选中版本后的具体面板...]        │
└──────────────────────────────────┘
```

- **Classic Workflow / 经典科研工作流**（v1/v2）：进入当前的 Workbench 界面，保留已有的所有功能（Research Console、Citation Verifier、Evidence Board、Hypothesis Arena、Experiment Plan、Report Viewer 等）。默认 domain 为 `energy_materials`，默认 question 为固态电解质方向。此版本不改动任何现有界面逻辑。
- **Seismic Expert / 地震科研专家**（v3）：进入 v3 新界面，包含以下新功能面板。默认 domain 为 `seismic_event_classification`，默认 question 为地震事件分类方向。

两个版本共用后端服务（同一个 API Server），但 v3 的 API 路径有新增端点（arena、switchback、debug 等）。前端通过 `domain` 和 `mode` 参数区分两种工作流的行为。

切换版本时不销毁当前 run 的状态——Classic Workflow 的 run 和 Seismic Expert 的 run 都可以通过 Run History 回溯。两个版本的 run 存在同一个 run_store 中，通过 `domain` 和 `mode` 字段区分。

### 9.2 Seismic Expert (v3) 面板列表

v3 界面在经典版基础上新增和替换以下面板：

- **Mode Selector**：Discovery / Idea Refinement / Experiment Assistance（v3三种入口模式选择器）。
- Research Console：输入方向、创意、数据路径或代码路径（根据mode不同显示不同输入字段）。
- Run Timeline：展示多智能体执行状态（支持分支、循环、回退的可视化——不同于经典版的线性timeline）。
- Literature Board：论文、引用核验、代码链接（与经典版共用）。
- **Baseline Board**：baseline paper、repo、reproducibility score、run status（v3新增）。
- Evidence Board：证据链和 human gate（与经典版共用）。
- **Idea Refinement Panel**：用户创意、相似工作、创新点、风险（v3新增，Idea Refinement Mode专用）。
- **Hypothesis Arena Panel**：竞技可视化 — 排名表格/对战矩阵（Discovery）、消融对比图（Idea Refinement）、Critic评分维度雷达图（v3替换经典版的HypothesisArena）。
- Experiment Plan Panel：数据、模型、指标、split、消融矩阵（v3扩展，加入Seismic Data Profile）。
- **Code Plan Panel**：文件结构、运行命令、生成代码状态（v3新增）。
- **Code Debug Panel**：微观ReAct迭代记录 — 错误类型、修复方案、代码diff、调试轮次（v3新增）。
- Experiment Results Panel：baseline / proposed / ablation metrics（v3扩展）。
- **Feedback Loop Panel**：失败诊断、下一轮建议、用户选择、Hypothesis Switchback 状态（v3新增）。
- Report Viewer：最终报告和导出（与经典版共用，但v3报告包含新增字段）。
- Workspace Panel：artifacts、logs、result cards（与经典版共用）。

### 9.3 Classic Workflow (v1/v2) 面板列表

经典版界面保持不变，不做任何改动：

- Research Console（默认question: 固态电解质方向）
- Run History
- Run Timeline（线性）
- StatusStrip
- ReviewChecklistPanel
- CitationVerifier
- EvidenceBoard
- PerspectivePlanPanel
- KnowledgeCardsPanel
- ScientificDataPanel（MaterialsDataAdapter）
- HypothesisArena（线性 生成→批判→修订）
- ExperimentPlanPanel
- ClaimAuditPanel
- ReportViewer
- BrowserCapturePanel
- WorkspacePanel

## 10. 后端 API v3 建议

新增或扩展 API：

```text
POST /api/runs
POST /api/runs/{run_id}/start
POST /api/runs/{run_id}/mode

GET  /api/runs/{run_id}/idea
POST /api/runs/{run_id}/idea/refine

GET  /api/runs/{run_id}/arena
POST /api/runs/{run_id}/arena/run                 # 触发假设竞技
POST /api/runs/{run_id}/arena/switchback/{hypothesis_id}  # 假设回退

GET  /api/runs/{run_id}/baselines
POST /api/runs/{run_id}/baselines/discover
POST /api/runs/{run_id}/baselines/{baseline_id}/verify-repo
POST /api/runs/{run_id}/baselines/{baseline_id}/reproduce

GET  /api/runs/{run_id}/experiment-plan
POST /api/runs/{run_id}/code-plan
POST /api/runs/{run_id}/experiments/run
POST /api/runs/{run_id}/experiments/debug          # 触发微观ReAct代码调试
POST /api/runs/{run_id}/experiments/ablation

GET  /api/runs/{run_id}/results
GET  /api/runs/{run_id}/result-card
POST /api/runs/{run_id}/feedback/continue

GET  /api/runs/{run_id}/report
GET  /api/runs/{run_id}/report/export
```

## 11. 核心数据模型 v3

### 11.1 ResearchMode

```python
ResearchMode = Literal[
    "discovery",
    "idea_refinement",
    "experiment_assistance",
]
```

### 11.2 IdeaBrief

```python
class IdeaBrief(BaseModel):
    research_problem: str
    user_idea: str | None
    target_task: str
    input_data: list[str]
    proposed_method: str | None
    expected_contribution: str | None
    target_labels: list[str]
    unknowns: list[str]
    risks: list[str]
```

### 11.3 BaselineCandidate

```python
class BaselineCandidate(BaseModel):
    baseline_id: str
    paper_id: str
    paper_title: str
    paper_doi: str | None
    paper_url: str | None
    code_url: str | None
    code_source: str
    task_match: str
    input_type: str
    labels_supported: list[str]
    dataset_used: str | None
    metrics_reported: list[str]
    reproducibility_score: float
    license: str | None
    run_command: str | None
    verified_repo: bool
    reproduction_status: str
    risks: list[str]
```

### 11.4 ExperimentSpec

```python
class ExperimentSpec(BaseModel):
    task: str
    dataset: str
    labels: list[str]
    split_strategy: str
    inputs: list[str]
    baseline_ids: list[str]
    proposed_method: str
    metrics: list[str]
    ablations: list[str]
    pass_criteria: dict[str, float]
```

### 11.5 ExperimentRun

```python
class ExperimentRun(BaseModel):
    run_id: str
    experiment_id: str
    kind: Literal["baseline", "proposed", "ablation"]
    config_path: str
    command: str
    status: str
    metrics: dict[str, float]
    artifacts: dict[str, str]
    logs_path: str | None
    started_at: str
    finished_at: str | None
```

### 11.6 ResultCard

```python
class ResultCard(BaseModel):
    result_card_id: str
    dataset: str
    split_strategy: str
    best_baseline: dict
    proposed_result: dict
    ablation_results: list[dict]
    pass_status: Literal["pass", "partial", "fail"]
    support_judgment: str
    failure_diagnosis: list[str]
    next_actions: list[str]
```

### 11.7 HypothesisArenaResult

```python
class HypothesisArenaResult(BaseModel):
    arena_id: str
    mode: Literal["discovery", "idea_refinement"]
    arena_level: Literal["simplified_ranking", "elo_tournament"]   # MVP用简化排名, 升级后用Elo
    candidates: list[HypothesisArenaCandidate]
    ranking: list[str]                                  # hypothesis_id 按排名排序
    selected_for_experiment: str                         # Top1 hypothesis_id
    switchback_candidate: str | None                     # Top2 hypothesis_id (回退备选)
    ablation_design: list[AblationChallenge]             # 消融式竞技的挑战者设计
    pairwise_results: list[PairwiseResult] | None        # Elo升级: pairwise对战记录
    evolution_history: list[EvolutionRecord] | None      # Elo升级: 假设进化记录

class HypothesisArenaCandidate(BaseModel):
    hypothesis_id: str
    statement: str
    is_user_idea: bool                                   # Idea Refinement模式标记
    critic_scores: dict[str, CriticReview]               # 每个视角Critic的评分
    weighted_score: float                                # 加权综合分数
    elo_rating: float | None                             # Elo升级: 当前Elo分数
    elo_history: list[float] | None                      # Elo升级: 每轮Elo变化
    rank: int

class PairwiseResult(BaseModel):                         # Elo升级: pairwise对战记录
    pair: list[str]                                      # 对战的两个hypothesis_id
    winner: str                                          # 赢家hypothesis_id
    reason: str                                          # LLM Judge的判断理由
    score_diff: int                                      # Elo分数变化量

class EvolutionRecord(BaseModel):                        # Elo升级: 假设进化记录
    from_id: str                                         # 进化前的hypothesis_id
    to_id: str                                           # 进化后的hypothesis_id
    changes: str                                         # 进化修改了什么
    rationale: str                                       # 进化原因

class AblationChallenge(BaseModel):
    challenge_id: str                                    # e.g. "H_challenge1"
    tests_innovation_point: str                          # 测试哪个创新点
    expected_insight: str                                # 预期揭示什么
    derivation_from_main: str                            # 从H_main去掉/替换了什么
```

### 11.8 CodeDebugIteration

```python
class CodeDebugIteration(BaseModel):
    iteration_id: str
    error_type: Literal["import", "shape", "config", "dependency", "runtime", "other"]
    error_message: str
    diagnosis: str                                       # LLM推理的错误诊断
    fix_description: str                                 # 修复方案描述
    code_diff: str | None                                # 代码修改的diff
    run_after_fix: Literal["success", "still_error", "new_error"]
    iteration_number: int                                # 1~5
```

### 11.9 ExperimentIteration

```python
class ExperimentIteration(BaseModel):
    iteration_id: str
    reason: str
    changes: list[str]
    previous_metrics: dict[str, float]
    new_metrics: dict[str, float]
    decision: Literal["continue", "stop", "accept", "revise_hypothesis"]
    human_approved: bool
```

## 12. v3 MVP 验收标准

v3 MVP 至少需要满足：

1. 支持 Discovery / Idea Refinement / Experiment Assistance 三种入口模式。
2. 地震事件分类作为默认 demo domain。
3. 能将用户方向或创意结构化为 IdeaBrief。
4. 能检索真实地震分类相关论文。
5. 能核验 references，不允许虚构引用进入最终报告。
6. 能检索或记录 baseline 代码来源，优先选择论文官方 GitHub。
7. 能为 baseline 生成 Baseline Candidate 和可复现性评分。
8. 能生成公平对比实验方案。
9. 能在受控实验框架中生成或适配实验代码。
10. 能运行至少一个 baseline 和一个 proposed method 的最小 demo。
11. 能生成 metrics：accuracy、macro-F1、per-class F1，推荐 confusion matrix。
12. 能执行至少一个消融实验。
13. 能评估 proposed method 是否超过 baseline。
14. 结果不好时，能给出失败诊断和下一轮修改建议。
15. 支持最多 3 轮实验反馈循环。
16. 最终报告包含 Baseline Provenance、Experiment Iteration Log、Ablation Report 和 Result Support Judgment。
17. 前端能展示模式、文献、baseline、实验计划、结果和报告。
18. 每个 run 保存 workspace artifacts、代码计划、实验日志、result card 和报告。

## 13. 与比赛 PDF 要求的对应关系

| PDF 要求 | v3 对应设计 |
| --- | --- |
| 基于 Qwen / 百炼 | Qwen client、LLM log、调用凭证 |
| 多智能体系统 | Planner、Evidence、Arena(Critic×3)、Baseline、Experiment、Evaluator、Report agents |
| 数据/文献输入到假设输出 | Literature/Data Acquisition + Hypothesis Arena(竞技筛选) |
| 文献挖掘与事实提取 | Literature Miner + Evidence Ledger |
| 逻辑驱动假设生成 | Discovery Mode + Hypothesis Arena(排名竞技) + Idea Refinement(消融式竞技) |
| 多轮迭代 | 微观ReAct(代码调试5次) + 宏观ReAct(实验反馈3轮) + Hypothesis Switchback(假设回退) |
| 人在回路 | hypothesis selection、evidence freeze、feedback decision |
| Datasets | Seismic Data Agent |
| Methods | Code Experiment Loop |
| Experiments | baseline + proposed + ablation |
| Results | actual result card 或可解释 preliminary result |
| References 严禁虚构 | Citation Verifier + Baseline Provenance |
| 代码与结果可复现 | workspace、code plan、logs、result card |

## 14. 当前代码迁移与 LangGraph 策略

当前代码已经完成 v1/v2 的 MVP 主闭环。v3 建议分阶段迁移，同时在合适的时机引入 LangGraph。

### 14.1 LangGraph 迁移策略

#### 迁移原则

1. **先跑通 LLM，再换编排**：先把 v1/v2 的 8 个硬编码 Agent 接入 LLM（复制 PlannerAgent 模式：`self.llm` + `SYSTEM_PROMPT` + `fallback`），验证 prompt/fallback/structured output 正确后，再引入 LangGraph 替换编排层。
2. **LLM 调用逻辑与编排框架解耦**：Agent 的 `self.llm.complete(LLMRequest(...))` 是纯函数，不依赖 LangGraph。LangGraph node 内部调的仍然是同一个 LLMClient，只是编排方式变了。
3. **ResearchRun 整体作为 State channel**：不拆散 `ResearchRun` 的 20+ 字段为独立 channel，而是整体作为一个 LangGraph State channel（`Annotated[ResearchRun, replace]`）。原因：`frozen_evidence_ids ↔ evidence ↔ papers` 的交叉引用逻辑在拆散的 channels 里很难维护。
4. **逐步替换，不推翻**：保留 v1/v2 的 `ScientistWorkflow`，LangGraph 先只接管新增的非线性部分（Intent Router 分支、Hypothesis Arena 竞技、Feedback Loop 循环），线性共用部分（literature、citation、evidence、report）可以先作为 LangGraph 的顺序 node，后续逐步迁移。

#### 迁移时机判断

| Sprint | 是否需要 LangGraph | 理由 |
|--------|-------------------|------|
| V3-1 模式入口 | **需要** | Intent Router 是 conditional edge，手写分支代码比 LangGraph 更复杂 |
| V3-2 Baseline Discovery | 可以用手写 | Baseline Discovery 仍然是线性步骤，不需要循环 |
| V3-3 Code Experiment | **需要** | 微观ReAct是cyclic subgraph，手写while循环可维护性差 |
| V3-4 Feedback Loop | **需要** | 宏观ReAct + Hypothesis Switchback 是 cyclic graph + conditional edge |
| V3-5 Demo Freeze | 不需要新改动 | 只固化已有功能 |
| V3-6 Hardening | 不需要新改动 | 只增强已有功能 |

#### State 设计（路线A）

```python
# LangGraph State — ResearchRun 整体作为 channel
class WorkflowState(TypedDict):
    run: Annotated[ResearchRun, _run_replace]       # 整体状态
    mode: str                                        # 当前科研模式
    arena_result: HypothesisArenaResult | None       # 竞技排名结果
    iteration: int                                   # 当前实验迭代轮次
    debug_iteration: int                             # 当前代码调试轮次
    messages: list[BaseMessage]                      # Agent间对话记录

def _run_replace(old: ResearchRun, new: ResearchRun) -> ResearchRun:
    return new  # 整体替换，不做字段级合并
```

#### 每个Sprint与LangGraph的关系

Sprint V3-1 引入 LangGraph 骨架：
- 用 `StateGraph(WorkflowState)` 重写 `ScientistWorkflow`
- Intent Router 作为 `add_conditional_edges`
- v1/v2 的线性步骤作为顺序 node chain
- v1/v2 的 guided 模式暂停用 `interrupt()` 替代 `_pause_for_human()`
- **但此时 v1/v2 的 Agent 内部逻辑不变**（仍用 `self.llm.complete()`）

Sprint V3-2 在 LangGraph 上添加 Baseline Discovery node：
- 新增 `baseline_discovery` node 和 `repo_verifier` node
- 与 Literature Router 的衔接通过 edge 连接

Sprint V3-3 添加微观 ReAct cyclic subgraph：
- `generate_code → run_code → evaluate_error → fix_code → run_code` 循环
- `add_conditional_edges("evaluate_error", debug_route_fn)` 控制退出

Sprint V3-4 添加宏观 ReAct + Switchback：
- 外层 cyclic subgraph: `experiment → evaluate → diagnose → revise → experiment`
- Switchback conditional edge: `should_switchback` → "switchback" 或 "abort"
- Idea Refinement 的用户确认: `interrupt()` 等待用户批准

### 14.2 Sprint 规划

### Sprint V3-1：模式入口与地震 domain

目标：在不破坏 v1/v2 主流程的前提下，让系统能识别三种科研入口，并把地震事件分类作为默认 demo domain。

交付：

- 增加 `ResearchMode`。
- 增加 Intent Router。
- 增加 IdeaBrief schema。
- 前端增加 mode selector。
- 默认 demo question 改成地震事件分类。
- 保留 Scientific Data Agent，新增 Seismic Data Adapter / Seismic Data Agent mock。
- ResearchRun 增加 mode、idea_brief、seismic_data_profile 等字段。
- Workflow 中增加最小模式分支，但仍复用现有 planner、literature、evidence、report 链路。

验收：

- 用户可以选择 Discovery / Idea Refinement / Experiment Assistance。
- 系统能为地震分类问题生成结构化 IdeaBrief。
- 现有 v1/v2 tests 不因领域扩展失效。

### Sprint V3-2：Baseline Discovery

目标：让系统能从文献和代码来源中发现 baseline，并记录可追溯 provenance。

交付：

- 增加 BaselineCandidate schema。
- Literature Miner / Baseline Discovery Agent 支持识别 code_url。
- 明确 baseline code source：paper metadata、arXiv/PDF、Papers with Code、GitHub search、README matching、用户手动 repo。
- 增加 Repository Verifier v1。
- 增加 baseline repo safety policy：隔离目录、命令白名单式执行、写路径限制、网络限制。
- 增加 Baseline Board 前端。
- 报告增加 Baseline Provenance。

验收：

- 每个 baseline candidate 都有 paper provenance 和 code provenance。
- Repository Verifier 能输出 reproducibility_score、risks、run_command 和 safety status。
- 未经验证的 repo 不允许进入自动运行阶段。

### Sprint V3-3：Code Experiment Loop v1

目标：建立受控地震分类实验框架，先跑最小可复现实验。

交付：

- 新建 `experiments/seismic_event_classification/`。
- 增加最小 dataset adapter。
- 增加 baseline adapter。
- 增加 proposed model demo。
- 增加 train / evaluate / result_card。
- 后端接入实验运行结果。
- 所有实验运行写入独立 artifacts 目录，不污染主代码。
- 外部 baseline 仅通过 Repository Verifier 认可的命令在隔离目录执行。

验收：

- 至少能运行一个 baseline 和一个 proposed method。
- 生成 result card，包含 dataset、split、metrics、artifacts、logs。
- 失败实验也能记录 exit code、错误日志和失败原因。

### Sprint V3-4：Feedback Loop 与消融

目标：跑完实验后能判断结果是否支持假设，并在失败时进入诊断与改进循环。

交付：

- 增加 Result Evaluator。
- 增加 Ablation Agent。
- 增加 ExperimentIteration。
- 增加 failure diagnosis。
- 前端展示 feedback loop。
- 增加 pass / partial / fail 判断。
- 增加最多 3 轮 feedback iteration 的记录。

验收：

- proposed method 不如 baseline 时，不直接写成成功。
- 系统能给出数据问题、模型问题、假设问题或复现问题诊断。
- 用户可以选择继续、停止、接受 partial result 或修订假设。

### Sprint V3-5：Demo Freeze

目标：形成可提交、可录屏、可复现的地震事件分类 demo。

交付：

- 固定地震分类 demo input。
- 固定 baseline paper/repo。
- 固定 dataset subset。
- 固定 result card。
- 固定 final report。
- 准备截图、视频脚本、Qwen 调用日志和技术方案 PDF。

验收：

- 新环境按 README 能跑通 demo。
- 最终报告包含 Baseline Provenance、Citation Audit Log、Claim Audit Report、Ablation Report 和 Experiment Iteration Log。
- demo 视频能展示三种模式中的至少一种完整闭环，优先展示 Idea Refinement Mode。

### Sprint V3-6：Post-MVP Hardening

目标：在 MVP 可演示后增强鲁棒性和真实可用性。

交付：

- 更完整的公开地震数据集接入。
- 更强的 GitHub / Papers with Code 检索。
- baseline repo cache。
- dependency resolution report。
- workspace bundle export。
- 服务重启后从 workspace 恢复 run state。
- 更强的 Qwen / embedding claim-evidence semantic verification。

验收：

- baseline 发现和复现失败时有稳定 fallback。
- workspace artifacts 可打包提交。
- Claim Verifier 不再只依赖词汇匹配。

## 15. 风险与应对

### 风险 1：地震公开数据和标签不足

应对：

- MVP 使用公开数据或构造小型 demo subset。
- 飞机失事等罕见事件不作为主标签。
- 将罕见冲击事件放入 OOD 扩展。

### 风险 2：文献 baseline 代码不可复现

应对：

- baseline 分 Tier。
- 记录 reproduction status。
- 允许第三方复现或 reimplementation。
- 通用 baseline 只作为 fallback。

### 风险 3：proposed method 不如 baseline

应对：

- 进入 Experiment Feedback Loop。
- 做失败诊断。
- 调整数据、模型或假设。
- 最多 3 轮后输出 partial / negative result。

### 风险 4：系统变成普通训练平台

应对：

- 保留 Evidence Engine、Citation Verifier、Hypothesis Arena 和 Report Writer。
- 强调 AI Scientist 做科研决策和证据审计，训练代码只是验证工具。

### 风险 5：LLM 生成代码不可控

应对：

- 使用受控实验框架。
- 优先生成配置和局部模块。
- 每次运行保存 logs 和 result card。
- 不直接信任未运行代码。

## 16. v3 最终提交材料

1. 技术方案 PDF，不超过 20 页。
2. 源代码。
3. Docker Compose / README。
4. 地震事件分类 demo 数据或数据准备脚本。
5. 文献 baseline provenance。
6. baseline 复现记录。
7. proposed method 代码。
8. 消融实验结果。
9. Result card。
10. Citation Audit Log。
11. Claim Audit Report。
12. Qwen / 百炼调用日志截图。
13. 前端截图。
14. 10 分钟内演示视频。

## 17. v3 结论

PRD v3 的核心不是把 TrustSci-Agent 简单改成地震分类模型，而是：

> 在可信 AI Scientist 基础流程上，加入三种科研入口模式（分支）、竞技式假设筛选（Discovery 排名竞技 / Idea Refinement 消融式竞技）、微观 ReAct 代码调试循环、宏观 ReAct 实验反馈循环、Hypothesis Switchback 假设回退机制、文献代码 baseline 发现、受控代码实验执行和消融验证，并以地震事件分类作为垂直 demo，能源材料作为保留的第二 domain。

这样既保留 v1/v2 的可信证据链和多智能体优势，也能满足老师希望聚焦地球物理地震领域的要求，并通过 LangGraph 实现分支/循环/回退的图结构编排，增强比赛中最重要的三点：

1. 科学假设有真实文献和数据支撑，并通过竞技机制筛选。
2. 实验有文献 baseline、代码和结果验证，并通过双层 ReAct 确保代码能跑通、结果可迭代。
3. 系统过程可复现、可审计、可展示，失败时有假设回退而非包装成功。
