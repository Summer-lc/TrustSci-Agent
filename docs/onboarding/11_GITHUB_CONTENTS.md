# GitHub 内容与安全边界

> 核验日期：2026-08-21　目标分支：`codex/project-handover-docs`

## 1. 本分支包含什么

- `backend/`：FastAPI 接口、工作流、智能体、工具、数据结构、存储与测试。
- `frontend/`：Next.js 科研工作台、API 类型与前端测试。
- `browser-worker/`：网页快照、截图和论文预览服务源码。
- `experiments/seismic_event_classification/`：固定地震实验 harness，包括合成数据生成、弱基线、训练协议和验收测试。
- Docker Compose、Dockerfile、依赖锁定文件、`.env.example` 和环境检查脚本。
- PRD、Sprint 计划、当前架构/API 文档及 `docs/onboarding/` 新成员交接资料。
- 小型样例数据：`data/seismic_demo/events.csv` 与 `data/sample_datasets/solid_electrolyte_candidates.csv`。
- 正式演示资产：完整 16 页 PPT、最终预览图和相关正式说明。

## 2. 本分支不包含什么

以下内容可能存在于开发者本机，但不会上传：

- `.env`、API Key、GitHub Token、私钥及其他凭据；
- Python/Node 依赖目录、编译缓存、类型检查缓存和测试缓存；
- `data/workspace/`、`backend/data/` 等原始运行工作区；
- `data/outputs/llm_calls/` 中的完整提示词和模型调用日志；
- 浏览器 trace、网页缓存、临时截图、日志和 `tmp/`；
- `.pptx-build/`、早期预览版本、PPT 生成缓存和非最终导出；
- 本地助手配置与会话状态。

这些排除项不是项目源码缺失，而是出于隐私、体积、可维护性和可复现性考虑。需要共享运行结果时，应优先整理成脱敏摘要，并说明数据来源和验证条件。

## 3. 数据与结果边界

- `data/seismic_demo/events.csv` 是构造的地震事件元数据。
- 实验 harness 在运行时使用 NumPy 生成确定性合成三通道波形，不是真实 STEAD 波形子集。
- 固态电解质 CSV 是样例候选数据，不代表系统已经完成真实材料实验。
- 冻结演示结果和界面截图只用于展示系统能力，不能替代真实数据上的独立科学验证。
- 原始运行目录和 LLM 日志默认保留在本机；GitHub 文档只引用经过核验、脱敏的代表性摘要。

## 4. 模型文件状态

仓库当前没有 `.pt`、`.pth`、`.ckpt`、`.onnx`、`.safetensors`、`.pkl` 或 `.joblib` 预训练权重文件。

系统通过阿里云百炼的 OpenAI 兼容接口调用 Qwen；API Key 只放在本地 `.env`。地震代码实验中的 `model.py` 由模型在运行时生成，经过静态安全检查后复制到单次运行的隔离目录，不作为预训练权重提交。仓库仅保留固定的 `model_template.py`、传统机器学习 baseline 和可复现实验协议。

## 5. 敏感信息与大文件核验

2026-08-21 的初步扫描结果：

- 未发现 OpenAI 风格密钥、Bearer Token 或私钥块；
- 文档和测试中出现的 `DASHSCOPE_API_KEY`、`GITHUB_TOKEN` 均为空值、测试值或占位示例；
- 未发现符合上传条件且达到 50 MB 的文件；
- 最大的正式资产是约 2.8 MB 的完整 16 页 PPT，低于 GitHub 单文件限制。

最终推送前还会对“已暂存文件”重新扫描；只有暂存区通过核验才允许提交和推送。

## 6. 分支策略

- 开发基线：现有本地 `main` 及其未提交项目成果。
- 交接分支：`codex/project-handover-docs`。
- 本轮只推送交接分支，不向远程 `main` 合并或直接提交。
- 提交按安全边界、交接文档、源码快照和读者测试修订分组，便于复核和回退。

## 7. 新成员拿到仓库后

1. 不要向 GitHub 提交自己的 `.env`。
2. 从 `.env.example` 复制本地配置；没有 Qwen Key 时使用确定性 fallback 验证界面和流程。
3. 如需共享新运行结果，先删除提示词、用户输入、Token、绝对路径和不必要的原始网页内容。
4. 大型真实数据集和模型权重应使用正式数据/模型仓库或 Git LFS，并补充来源、许可证、哈希和版本说明。
5. 以 [`docs/onboarding/README.md`](README.md) 为后续阅读入口。
