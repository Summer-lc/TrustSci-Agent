# 环境配置、启动与验证

## 1. 推荐环境

- Windows 10/11 + Docker Desktop，或 Linux/WSL2 + Docker Engine。
- Python 3.11（本轮验证使用 3.11.9）。
- Node.js 20 以上（本轮环境为 24.14.0）、npm。
- 可选：阿里云百炼 `DASHSCOPE_API_KEY`、GitHub Token 和各文献/材料服务 Key。

## 2. 最短启动路径：Docker

在仓库根目录执行：

```powershell
Copy-Item .env.example .env
docker compose up --build
```

开发热重载：

```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

服务地址：

- 前端：http://localhost:3000
- 后端 Swagger：http://localhost:8000/docs
- 后端健康检查：http://localhost:8000/health
- browser-worker：http://localhost:8010/health

停止服务：

```powershell
docker compose down
```

## 3. `.env` 配置

`.env` 只用于本机，禁止提交。主要变量：

| 变量 | 用途 | 无值时行为 |
|---|---|---|
| `DASHSCOPE_API_KEY` | 调用百炼 Qwen | 使用可审计的确定性 fallback |
| `QWEN_MODEL` | Qwen 模型名 | 示例默认 `qwen-plus` |
| `WORKFLOW_ENGINE` | `classic` 或 `langgraph` | 代码默认 classic；团队 V3 演示建议 langgraph |
| `OPENALEX_EMAIL` / `CROSSREF_EMAIL` | 文献服务礼貌池/联系信息 | 仍可尝试匿名访问 |
| `SEMANTIC_SCHOLAR_API_KEY` | Semantic Scholar | 默认不开启该来源 |
| `GITHUB_TOKEN` | 提升 GitHub API 额度 | 匿名请求额度较低 |
| `MATERIALS_PROJECT_API_KEY` | Materials Project | 使用本地样例或降级 |
| `DATA_DIR` | 运行和输出目录 | 本地默认 `data`，容器内 `/app/data` |
| `BROWSER_WORKER_URL` | 网页抓取服务 | 容器内默认 `http://browser-worker:8010` |

检查 Qwen 连接：

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/api/system/qwen/ping
```

响应只返回配置状态、模型名和短预览，不返回 Key。

## 4. 本地后端开发

```powershell
python -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
$env:DATA_DIR = 'data'
$env:WORKFLOW_ENGINE = 'langgraph'
backend/.venv/Scripts/python.exe -m uvicorn app.main:app --app-dir backend --reload --port 8000
```

环境自检必须从仓库根运行：

```powershell
backend/.venv/Scripts/python.exe scripts/check_dev_env.py
```

## 5. 本地前端开发

```powershell
Push-Location frontend
npm install
$env:NEXT_PUBLIC_API_BASE = 'http://localhost:8000'
npm run dev
Pop-Location
```

## 6. 测试命令

后端完整测试应从仓库根运行：

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

## 7. 无 Key 演示

无 `DASHSCOPE_API_KEY` 时，Qwen 客户端返回各智能体定义的确定性 fallback，并在 LLM 审计记录中标记 `fallback_used=true`。这适合验证界面、接口和数据流，不应宣传为真实 Qwen 推理。

## 8. 常见问题

### 后端测试找不到 `scripts`

不要在 `backend/` 目录运行完整测试；回到仓库根，使用上面的完整命令。

### 前端连不上后端

检查 `NEXT_PUBLIC_API_BASE`、8000 端口和 CORS；Docker 模式默认允许 localhost:3000。

### 文献很少或 baseline 为空

可能是外部源限流、网络不可达、检索结果被地震相关性规则过滤，或论文没有可验证代码。系统会降级，但文档必须保留限制说明。

### Qwen 调用慢或进入 fallback

检查 ping、模型名、超时和网络。不要把 Key 打印到日志；只查看状态、错误类型和脱敏调用记录。

### browser-worker 无法预览论文

论文预览失败不会改变引用核验状态。检查 8010 健康端点和共享数据目录；必要时保留 metadata-only 结果。

### Windows 下 pytest 有临时目录清理警告

本轮测试在全部通过后出现过 Windows 文件权限清理提示。若不影响退出码和测试结果，可记录后再手工检查临时目录；不要把该提示误判为业务测试失败。

