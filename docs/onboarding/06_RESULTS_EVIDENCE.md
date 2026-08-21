# 已有运行结果与证据边界

> 本页只收录能说明来源和验证条件的结果。核验日期：2026-08-21。

## 1. 本轮新鲜验证

| 检查 | 命令/环境 | 结果 |
|---|---|---|
| 环境检查 | Windows Python 3.11.9 虚拟环境 | FastAPI、Pydantic、ReportLab、RapidFuzz、LangGraph、NumPy、scikit-learn 均可导入；Node、npm、Docker 可用 |
| Compose 配置 | `docker compose -f docker-compose.yml -f docker-compose.dev.yml config --quiet` | 通过 |
| 后端测试 | 从仓库根运行 `backend/.venv/Scripts/python.exe -m pytest backend/tests -q` | 279 passed，3 个 scikit-learn 弃用警告；另有 Windows 临时目录清理提示 |
| 前端测试 | `npm test` | 2 个测试文件、22 项测试通过 |
| 前端构建 | `npm run build` | Next.js 16.2.6、TypeScript 和静态页面构建成功 |
| 固定地震 harness | 模板 `SeismicModel`，独立临时目录运行 `tests.py` 与 `train.py` | 接口测试和训练成功，生成 `metrics.json` 与 `comparison.json` |

后端测试首次从 `backend/` 目录运行时，`test_dev_environment.py` 无法导入根目录 `scripts`。从仓库根目录运行同一测试后 2 项通过，完整套件也通过。因此正确的本地测试入口是仓库根，而不是 `cd backend` 后直接运行完整套件。

## 2. 固定地震 harness 结果

数据条件：120 个确定性合成事件，3 通道，每通道 30 秒、100 Hz；类别为 earthquake、explosion、noise。模板模型与弱基线使用相同的时域统计特征和 LogisticRegression。

| 模型 | Accuracy | Macro-F1 | earthquake F1 | explosion F1 | noise F1 |
|---|---:|---:|---:|---:|---:|
| 固定 baseline | 0.8333 | 0.8492 | 0.8333 | 0.7143 | 1.0000 |
| 模板 SeismicModel | 0.8333 | 0.8492 | 0.8333 | 0.7143 | 1.0000 |

比较结果：`method_beats_baseline=false`，`outcome=completed_negative`。

这个结果是合理的：模板模型与 baseline 采用同一特征设计，目标是验证接口、测试、指标和比较文件能稳定生成，不是预设一个虚假的性能提升。真实 Qwen 运行可生成不同 `model.py`，但必须单独记录模型源码、数据、随机种子和完整验证条件。

## 3. 本地保存的运行产物

本机 `data/workspace/` 中可解析到 470 条保存运行状态：167 completed、167 created、90 failed、34 paused、9 running、3 abandoned。它们覆盖 discovery、idea_refinement 和 experiment_assistance，也覆盖 energy_materials 与 seismic_event_classification。

这些数字主要用于证明运行生命周期、持久化和测试覆盖产生过多种状态。目录中包含自动化测试、开发调试和演示运行，不能把“167 completed”当成 167 次真实科研实验成功。原始目录也不会上传 GitHub。

## 4. 历史结果如何使用

历史交接记录提到：

- 2026-07-03：216 项后端测试通过；
- 2026-07-06：233 项后端测试通过、前端构建通过；
- 早期真实 Qwen 演示曾生成频域特征模型并记录优于弱 baseline 的结果。

这些记录可以用于项目时间线，但不作为本轮最新验收数字，也不应在没有对应冻结运行包的情况下作为核心科研结论。当前对外表述应优先使用本页的新鲜验证结果。

## 5. 这些结果能证明什么

- 当前源码在本机环境中通过较完整的后端和前端自动化验证。
- 前端可以生产构建，Docker Compose 配置语法有效。
- 地震实验接口、固定数据生成、传统基线、指标计算和比较文件可重复执行。
- 模板方法不会被系统误报为优于 baseline。

## 6. 这些结果不能证明什么

- 不能证明系统在真实地震波形上具有 0.8333 的泛化性能。
- 不能证明当前任一 AI 生成模型优于公开地震分类 baseline。
- 不能证明所有外部文献源、GitHub 和 Qwen 服务在任意网络环境都可用。
- 不能证明策略级 sandbox 可以安全执行任意不可信代码。
- 不能证明自动生成报告中的所有科学主张都经过领域专家认可。

## 7. 下一次正式结果应附带的材料

1. 数据集名称、版本、许可证、下载日期和哈希。
2. 训练/验证/测试划分及防泄漏说明。
3. baseline 代码、版本、运行命令和来源。
4. 生成的 `model.py`、依赖、随机种子和运行环境。
5. accuracy、macro-F1、per-class F1、混淆矩阵及重复实验统计。
6. Qwen 模型名称、调用日期、提示模板版本和脱敏审计摘要。
7. 失败运行和限制条件，而不只保留最佳结果。

