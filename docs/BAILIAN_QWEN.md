# Bailian Qwen Integration

The backend uses Alibaba Cloud Model Studio / Bailian through the OpenAI-compatible chat completions endpoint.

## Local Configuration

Create `.env` from the template:

```bash
cp .env.example .env
```

Set these values in `.env`:

```bash
DASHSCOPE_API_KEY=<your_bailian_api_key>
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen-plus
QWEN_TEMPERATURE=0.2
QWEN_TIMEOUT_SECONDS=60
QWEN_MAX_RETRIES=1
```

Never commit `.env`. It is ignored by git.

## Connectivity Check

Start the backend, then run:

```bash
curl -X POST http://localhost:8000/api/system/qwen/ping
```

For the current local dev server on port `8011`:

```bash
curl -X POST http://localhost:8011/api/system/qwen/ping
```

The response reports whether the key is configured, the selected model, and a short response preview.

## Runtime Logs

Every Qwen call writes an audit record:

```text
data/outputs/llm_calls/{run_id}.jsonl
```

The log includes:

- model
- agent
- status
- fallback flag
- latency
- prompts and parsed response
- token usage when returned by the API
- error message when fallback is used

The API key is never written to the log.

