from pathlib import Path
from urllib.parse import urljoin, urlparse
from uuid import uuid4

import httpx
from bs4 import BeautifulSoup
from fastapi import FastAPI
from playwright.async_api import async_playwright
from pydantic import BaseModel

app = FastAPI(title="TrustSci Browser Worker", version="0.1.0")


class CaptureRequest(BaseModel):
    url: str
    download_pdfs: bool = True
    max_pdf_downloads: int = 3


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/capture")
async def capture(payload: CaptureRequest) -> dict:
    trace_id = f"trace_{uuid4().hex[:10]}"
    trace_dir = Path("data/browser_traces")
    trace_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 1000})
        response = await page.goto(payload.url, wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(250)
        final_url = page.url
        title = await page.title()
        html = await page.content()
        blocked_reason = _detect_access_challenge(title, html)
        screenshot_path = trace_dir / f"{trace_id}.png" if not blocked_reason else None
        if screenshot_path:
            await page.screenshot(path=str(screenshot_path), full_page=False, timeout=10000)
        await browser.close()

    status_code = response.status if response else None
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for link in soup.find_all("a"):
        href = link.get("href")
        if href:
            absolute = urljoin(final_url, href)
            links.append({"text": link.get_text(" ", strip=True)[:120], "href": absolute})

    html_path = trace_dir / f"{trace_id}.html"
    html_path.write_text(html, encoding="utf-8")
    pdf_links = [item for item in links if ".pdf" in item["href"].lower()][:20]
    downloaded_pdfs = []
    if payload.download_pdfs and pdf_links:
        downloaded_pdfs = await _download_pdfs(pdf_links[: payload.max_pdf_downloads], trace_dir, trace_id)

    return {
        "trace_id": trace_id,
        "url": final_url,
        "domain": urlparse(final_url).netloc,
        "status_code": status_code,
        "title": title,
        "html_path": str(html_path),
        "screenshot_path": str(screenshot_path) if screenshot_path else "",
        "blocked_reason": blocked_reason,
        "links": links[:50],
        "pdf_links": pdf_links,
        "downloaded_pdfs": downloaded_pdfs,
    }


def _detect_access_challenge(title: str, html: str) -> str | None:
    normalized_title = " ".join(title.lower().split())
    title_markers = (
        "just a moment",
        "attention required",
        "verify you are human",
        "security verification",
        "人机验证",
        "安全验证",
    )
    if any(marker in normalized_title for marker in title_markers):
        return "human_verification"

    normalized_html = html.lower()
    html_markers = (
        "cf-chl-",
        "challenge-platform",
        "verify you are human",
        "g-recaptcha",
        "hcaptcha-container",
        "人机验证",
    )
    if any(marker in normalized_html for marker in html_markers):
        return "human_verification"
    return None


async def _download_pdfs(pdf_links: list[dict], trace_dir: Path, trace_id: str) -> list[dict]:
    downloaded = []
    async with httpx.AsyncClient(timeout=45, follow_redirects=True) as client:
        for index, link in enumerate(pdf_links, start=1):
            try:
                response = await client.get(link["href"], headers={"User-Agent": "TrustSci-Agent/0.1"})
                response.raise_for_status()
                if "pdf" not in response.headers.get("content-type", "").lower() and not link["href"].lower().endswith(".pdf"):
                    continue
                pdf_path = trace_dir / f"{trace_id}_{index:02d}.pdf"
                pdf_path.write_bytes(response.content)
                downloaded.append({"url": str(response.url), "path": str(pdf_path), "bytes": len(response.content)})
            except Exception as exc:
                downloaded.append({"url": link["href"], "error": str(exc)})
    return downloaded
