# TrustSci-Agent

TrustSci-Agent 是一个基于阿里云百炼 Qwen 的本地优先多智能体 AI Scientist 原型，面向“基于国产开源大模型的 AI Scientist 的研发与应用”赛题。系统围绕真实文献、引用核验、证据账本、科学假设、受控实验、结果解释和研究报告建立可追踪闭环。

V3 主展示领域为地震事件分类，同时保留能源材料/固态电解质经典流程。

> 新成员请从 [项目交接资料入口](docs/onboarding/README.md) 开始。这里集中说明完成度、架构、运行流程、输入输出、模型算法、结果、环境、代码地图、后续分工和 PPT 素材。

## 当前状态（2026-08-21）

- FastAPI 后端、Next.js 前端和 browser-worker 三服务架构已形成。
- discovery、idea_refinement、experiment_assistance 三种研究模式已有代码和测试。
- LangGraph 支持模式分支、人工检查点、文献重搜、实验重设计、失败处理和恢复。
- 文献/引用/证据、假设 Arena、baseline、代码实验、结果分析、报告与审计链已实现。
- 三栏工作台、任务暂停/恢复/废除、失败步骤 retry/skip 和论文预览已实现。
- 本轮验证：后端 279 项测试通过；前端 22 项测试通过；生产构建和 Compose 配置通过。
- 地震实验当前使用确定性合成波形，只能验证软件闭环，不能代表真实地震数据性能。
- 仓库没有预训练模型权重；Qwen 通过 API 调用，实验 `model.py` 在运行时生成。

详细矩阵见 [项目现状与完成度](docs/onboarding/01_PROJECT_STATUS.md)，实测数字见 [已有结果与证据](docs/onboarding/06_RESULTS_EVIDENCE.md)。

## 系统服务

| 服务 | 技术 | 默认地址 | 职责 |
|---|---|---|---|
| frontend | Next.js / React | http://localhost:3000 | 研究任务、阶段、论文、实验和报告工作台 |
| backend | FastAPI / LangGraph | http://localhost:8000 | API、智能体编排、存储、实验和导出 |
| browser-worker | FastAPI / Playwright | http://localhost:8010 | 网页抓取、截图、PDF 链接和论文预览 |

## 快速启动

```powershell
Copy-Item .env.example .env
docker compose up --build
```

开发热重载：

```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

打开：

- 前端：http://localhost:3000
- 后端 API：http://localhost:8000/docs
- browser-worker：http://localhost:8010/health

没有 `DASHSCOPE_API_KEY` 时，系统使用带审计标记的确定性 fallback，可用于验证界面和流程；这不等同于真实 Qwen 推理。

完整环境说明见 [环境配置与启动](docs/onboarding/07_SETUP_GUIDE.md)。

## 三种研究模式

- `discovery`：从科研问题出发，检索证据、生成和筛选假设、设计并验证实验。
- `idea_refinement`：对用户已有想法进行批判、收窄、新颖性检查和验证。
- `experiment_assistance`：分析用户已有指标、日志和代码文本，不执行用户提交代码，输出结果判断、消融建议、限制和报告。

## 核心运行链路

```text
任务输入
→ 意图识别与规划
→ 文献检索、引用核验、证据账本
→ 假设生成、竞技与新颖性检查
→ 可信 baseline 接入与质量门
→ 实验设计、生成代码与受控执行
→ 结果评价、消融、解释与实验重设计
→ 报告生成、主张审计、修订、翻译与导出
```

LangGraph 中还包含 guided 检查点、重搜回边、实验重设计回边、步骤 retry/skip 和任务恢复。详见 [代码运行流程](docs/onboarding/03_RUNTIME_FLOW.md)。

## 模型与实验

- LLM：阿里云百炼 Qwen OpenAI 兼容接口，默认示例模型 `qwen-plus`。
- 编排：LangChain LCEL + LangGraph；classic 引擎保留兼容。
- 固定 baseline：每通道时域统计特征 + LogisticRegression。
- 生成模型：运行时生成符合 `fit/predict` 接口的 sklearn `SeismicModel`。
- 指标：accuracy、macro-F1、per-class F1。
- 安全：AST 拒绝规则、固定 harness、脚本白名单、Python `-I`、最小环境变量和超时。

当前隔离是本地演示的防御纵深，不是能够执行任意敌意代码的生产级安全沙箱。详见 [模型、算法与安全机制](docs/onboarding/05_MODELS_ALGORITHMS.md)。

## 本地验证

后端测试必须从仓库根运行：

```powershell
backend/.venv/Scripts/python.exe -m pytest backend/tests -q
```

前端：

```powershell
Push-Location frontend
npm test
npm run build
Pop-Location
```

Compose 配置：

```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml config --quiet
```

## 关键目录

- `backend/app/api/`：接口。
- `backend/app/workflows/`：classic/LangGraph 编排和运行控制。
- `backend/app/agents/`：多智能体角色。
- `backend/app/tools/`：文献、核验、Qwen、PDF、数据和安全执行工具。
- `backend/app/schemas/`：前后端数据合同。
- `frontend/components/workbench/`：三栏科研工作台组件。
- `experiments/seismic_event_classification/`：固定地震实验 harness。
- `docs/onboarding/`：新成员交接资料。
- `项目展示/`：正式演示 PPT 和最终预览。

推荐阅读顺序见 [代码文件地图](docs/onboarding/08_CODEBASE_MAP.md)。

## API 主流程

1. `POST /api/runs`
2. 可选：`POST /api/runs/{run_id}/baseline-intake`
3. experiment_assistance 模式：`POST /api/runs/{run_id}/experiment-assistance`
4. `POST /api/runs/{run_id}/start`
5. `GET /api/runs/{run_id}`
6. 按需读取 papers、evidence、hypotheses、report 和 artifacts
7. `GET /api/runs/{run_id}/report/export?format=md|json|pdf`
8. `GET /api/runs/{run_id}/workspace/export`

完整列表见 [FastAPI API Surface](docs/API.md)。

## 数据、隐私与 GitHub

- `.env`、API Key、Token 和私钥禁止提交。
- 原始运行工作区、完整 LLM 提示/响应日志、浏览器 trace 和构建缓存默认保留本地。
- 小型演示数据可以提交，但必须标记“合成/样例”。
- 大型真实数据和模型权重应使用正式数据/模型仓库或 Git LFS，并补充许可证、哈希和版本。

本分支的具体包含/排除清单见 [GitHub 内容与安全边界](docs/onboarding/11_GITHUB_CONTENTS.md)。

## 后续重点

比赛提交前优先完成真实地震数据子集、可复现公开 baseline、真实 Qwen 固定案例、新机器 Docker 冷启动、生产级执行隔离和最终 demo freeze。两位成员的建议分工见 [后续工作与路线图](docs/onboarding/09_NEXT_WORK.md)。

## 相关文档

- [整体架构](docs/onboarding/02_ARCHITECTURE.md)
- [输入与输出](docs/onboarding/04_INPUT_OUTPUT.md)
- [PPT 素材提纲](docs/onboarding/10_PPT_SOURCE_OUTLINE.md)
- [Qwen 配置](docs/BAILIAN_QWEN.md)
- [前端结构](docs/FRONTEND.md)
- [演示冻结](docs/DEMO_FREEZE.md)
- [提交检查单](docs/SUBMISSION_CHECKLIST.md)
