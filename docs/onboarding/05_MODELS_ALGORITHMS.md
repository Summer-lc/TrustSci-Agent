# 模型、算法与安全机制

## 1. Qwen/Bailian

系统的 LLM 实现是 `QwenClient`，通过阿里云百炼 OpenAI 兼容 `/chat/completions` 接口调用。仓库默认模型名为 `qwen-plus`，可在 `.env` 中替换；历史本地记录使用过其他 Qwen 型号，但不应写成当前仓库硬编码事实。

每次调用记录模型、agent、时延、提示、解析结果、token usage、错误和 fallback 标记，不记录 API Key。无 Key、请求失败或解析失败时返回 agent 自带的确定性 fallback。

## 2. LangChain 与 LangGraph

- LCEL 适配层把统一 `LLMRequest/LLMResponse` 接口接到 QwenClient，并负责 prompt、parser 和 fallback。
- LangGraph 负责可恢复状态图、三模式分支、人工检查点、重搜回边、实验重设计回边和结束条件。
- classic 工作流保留兼容路径；V3 展示建议使用 LangGraph。

LangGraph 不是科学算法本身，它解决的是状态、分支、循环和恢复。

## 3. 多智能体算法分工

| 阶段 | 代表 agent | 主要输出 |
|---|---|---|
| 意图与规划 | IntentRouter、IdeaIntake、Planner | mode、IdeaBrief、查询与研究计划 |
| 文献与数据 | LiteratureMiner、PaperTypeClassifier、ScientificDataAgent | 论文提炼、角色分类、数据 profile |
| 假设 | Hypothesis、CriticArena、Challenger、HypothesisArena | 候选、批判矩阵、排名与挑战 |
| 创新性 | NoveltyChecker、Revision | verdict、先验工作、收窄后的主张 |
| baseline | BaselineIntake、BaselineDiscovery、RepositoryVerifier | 来源、可信级别、候选与仓库验证 |
| 实验 | ExperimentDesigner、CodeWriter、ExperimentRedesign | 实验计划、model.py、重设计建议 |
| 结果 | ResultEvaluator、Ablation、ResultInterpreter | pass/partial/fail、消融、限制和下一步 |
| 报告 | ReportWriter、ClaimVerifier、ReportReviser、Translator | 报告、主张审计、修订和双语版本 |

## 4. 文献和证据方法

- 多源候选检索后进行领域相关性和噪声过滤。
- Crossref 等服务校验 DOI、标题相似度和元数据。
- PaperTypeClassifier 区分 method/model、dataset/benchmark、survey 等角色，地震相关性还有本地 guardrail。
- Evidence Ledger 将 claim 与论文/片段、核验状态和人工决定绑定。
- ClaimVerifier 检查报告主张是否被当前证据支持；未支持内容进入修订或限制说明。

这些规则降低幻觉风险，但不能替代领域专家阅读论文和判断因果关系。

## 5. 地震合成数据算法

固定生成器参数：

- 120 个事件，earthquake 60、explosion 35、noise 25。
- 3 通道 Z/N/E，每段 30 秒，100 Hz，共 3000 点。
- earthquake：1–3 Hz 正弦；explosion：10–20 Hz 正弦；noise：白噪声。
- 每个事件单位 RMS 归一化，再加少量通道噪声。
- 确定性 event-level 60%/20%/20% train/val/test 划分，固定种子 `20260629`。

设计意图是让纯时域统计不容易区分低频和高频正弦，而频谱特征可能带来改进。它是可控软件测试数据，不是地震学数据模拟器。

## 6. 固定 baseline 与生成模型

`BaselineModel` 使用每通道 mean、std、absolute max、mean square 共 12 个特征，加 class-weighted LogisticRegression。

`CodeWriterAgent` 只能生成一个实现 `fit(X, y)`、`predict(X)` 的 `SeismicModel`。fallback/template 与 baseline 类似；真实 Qwen 可能选择 FFT 频域特征、RandomForest 或其他已安装 sklearn 算法。

公平比较固定：

- 同一 event-level split；
- 同一原始波形输入；
- baseline 与方法分别训练；
- 指标为 accuracy、macro-F1、per-class F1；
- 必须产生 `metrics.json` 和 `comparison.json`。

## 7. 反馈算法

- 原子步骤自动尝试上限为 2 次；仍失败时进入人工可处理状态，并按步骤策略决定能否 retry/skip。
- 新颖性循环：`already_done` 最多进行 2 轮新颖性判断，再继续但标记限制。
- baseline 质量门：无可信来源时最多重搜 2 轮；达到上限后允许 degraded 比较，但报告降级。
- 微观修复：`model.py` 导入、接口或预测失败时按 harness manifest 重写，当前默认最多 3 轮。
- 宏观修复最多 1 轮；若方法比 baseline 低至少 0.05，还可触发最多 1 轮实验重设计。之后接受并如实记录负结果，避免无限循环。
- 结果分析：把“测试通过”“超过 baseline”“科学主张得到支持”分成不同判断。

## 8. 代码安全

静态拒绝规则禁止危险导入/调用、动态执行、文件/进程/网络等高风险能力；`SandboxExecutor`：

- 只复制固定 harness 和生成的 model.py；
- 仅允许运行 tests.py、train.py；
- 使用 Python `-I` 隔离标志；
- 只传递最小环境变量，不传 API Key；
- 设置超时；
- 在运行前清理旧指标产物。

限制：执行仍发生在后端宿主或容器内。这是本地演示的防御纵深，不是能够承载任意敌意代码的 OS 级沙箱。

## 9. 模型文件

仓库没有预训练权重。需区分：

- Qwen：远程 API 模型，不随仓库分发。
- `model_template.py`：接口参考源码，不是权重。
- 运行时 `model.py`：单次生成的 sklearn 模型实现源码。
- sklearn 训练后的对象：当前正式源码快照不提交 pickle/joblib。

如果后续加入真实模型权重，应提供模型卡、许可证、训练数据说明、哈希和版本，并使用模型仓库或 Git LFS。

## 10. 本轮基准结果

模板方法与固定 baseline 都得到 accuracy 0.8333、macro-F1 0.8492，因此系统正确输出 `completed_negative`。详见 [结果与证据](06_RESULTS_EVIDENCE.md)。
