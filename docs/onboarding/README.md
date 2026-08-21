# TrustSci-Agent 新成员交接入口

> 本目录按 2026-08-21 的当前代码和重新验证结果编写。历史 PRD 与 Sprint 计划用于理解设计过程；如果描述冲突，以当前代码和本目录为准。

## 15 分钟了解项目

按顺序阅读：

1. [项目现状与完成度](01_PROJECT_STATUS.md)
2. [整体架构](02_ARCHITECTURE.md)
3. [代码运行流程](03_RUNTIME_FLOW.md)
4. [已有结果与证据边界](06_RESULTS_EVIDENCE.md)
5. [后续工作与两人分工](09_NEXT_WORK.md)

## 准备开发环境

1. [环境配置与启动](07_SETUP_GUIDE.md)
2. [代码文件地图](08_CODEBASE_MAP.md)
3. [输入、输出与数据格式](04_INPUT_OUTPUT.md)
4. [模型与算法](05_MODELS_ALGORITHMS.md)
5. [API 明细](../API.md)

## 准备 PPT 或技术文档

1. [PPT 页级素材提纲](10_PPT_SOURCE_OUTLINE.md)
2. [项目现状与完成度](01_PROJECT_STATUS.md)
3. [整体架构](02_ARCHITECTURE.md)
4. [模型与算法](05_MODELS_ALGORITHMS.md)
5. [结果与可信边界](06_RESULTS_EVIDENCE.md)
6. [GitHub 内容与排除规则](11_GITHUB_CONTENTS.md)

## 一句话定位

TrustSci-Agent 是一个基于阿里云百炼 Qwen 的本地优先多智能体 AI Scientist 原型，围绕“真实文献—引用核验—证据账本—科学假设—受控实验—结果解释—研究报告”建立可追踪科研闭环。V3 主展示领域是地震事件分类，同时保留能源材料经典流程。

## 当前最重要的事实

- 后端、前端、LangGraph 工作流、三种研究模式和报告链路都已有代码与自动化测试。
- 2026-08-21 重新验证：后端 279 项测试通过，前端 22 项测试通过，Next.js 生产构建与 Docker Compose 配置通过。
- 地震实验 harness 可重复运行，但当前使用确定性合成波形，不代表真实地震数据效果。
- 当前仓库不包含预训练模型权重；Qwen 通过 API 调用，实验模型源码在运行时生成。
- 无 Qwen Key 时会进入可审计的确定性 fallback，适合软件演示，不等同于真实大模型推理结果。
- 历史 `SESSION_HANDOFF.md` 主体停留在 S6，本目录已经按后续代码重新核对。

## 资料索引

| 文件 | 回答的问题 |
|---|---|
| [01_PROJECT_STATUS.md](01_PROJECT_STATUS.md) | 目前完成到哪里，哪些结论还不能下？ |
| [02_ARCHITECTURE.md](02_ARCHITECTURE.md) | 服务、智能体、工具和数据如何组合？ |
| [03_RUNTIME_FLOW.md](03_RUNTIME_FLOW.md) | 一次任务从提交到报告怎样运行？ |
| [04_INPUT_OUTPUT.md](04_INPUT_OUTPUT.md) | 输入字段、中间产物和最终输出是什么？ |
| [05_MODELS_ALGORITHMS.md](05_MODELS_ALGORITHMS.md) | 使用哪些模型、算法、指标和安全规则？ |
| [06_RESULTS_EVIDENCE.md](06_RESULTS_EVIDENCE.md) | 已验证什么，结果能说明什么？ |
| [07_SETUP_GUIDE.md](07_SETUP_GUIDE.md) | 新电脑怎样配置、启动和测试？ |
| [08_CODEBASE_MAP.md](08_CODEBASE_MAP.md) | 关键代码文件在哪里，先读什么？ |
| [09_NEXT_WORK.md](09_NEXT_WORK.md) | 后续优先级和两位成员如何分工？ |
| [10_PPT_SOURCE_OUTLINE.md](10_PPT_SOURCE_OUTLINE.md) | 后续 PPT 每页可以讲什么？ |
| [11_GITHUB_CONTENTS.md](11_GITHUB_CONTENTS.md) | GitHub 包含和排除了什么？ |

## 历史与扩展资料

- [根 README](../../README.md)
- [PRD v1](../../PRD_v1.md)、[PRD v2](../../PRD_v2.md)、[PRD v3](../../PRD_v3.md)
- [当前架构说明](../ARCHITECTURE.md)
- [前端结构](../FRONTEND.md)
- [百炼/Qwen 配置](../BAILIAN_QWEN.md)
- [演示冻结流程](../DEMO_FREEZE.md)
- [开发工作流](../DEVELOPMENT_WORKFLOW.md)
- [提交检查单](../SUBMISSION_CHECKLIST.md)

