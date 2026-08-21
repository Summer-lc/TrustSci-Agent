from dataclasses import dataclass

import httpx


SKIPPABLE_STEPS = {
    "literature_mining",
    "paper_classification",
    "ablation_analysis",
}


@dataclass(frozen=True)
class ErrorDecision:
    code: str
    retryable: bool
    summary: str


def classify_step_error(exc: Exception, step_name: str) -> ErrorDecision:
    if isinstance(exc, (httpx.TimeoutException, httpx.NetworkError)):
        return ErrorDecision(
            "temporary_network_error",
            True,
            "外部服务暂时不可用或请求超时",
        )
    message = str(exc).lower()
    if any(token in message for token in ("429", "rate limit", "temporarily unavailable")):
        return ErrorDecision(
            "temporary_service_error",
            True,
            "外部服务暂时限流或不可用",
        )
    if step_name == "browser_capture":
        return ErrorDecision(
            "browser_capture_error",
            True,
            "论文网页抓取暂时失败",
        )
    return ErrorDecision(
        "step_validation_error",
        False,
        str(exc) or "步骤执行失败",
    )
