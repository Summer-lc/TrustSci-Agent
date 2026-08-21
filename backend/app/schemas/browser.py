from pydantic import BaseModel, Field, HttpUrl


class BrowserCaptureRequest(BaseModel):
    url: HttpUrl
    download_pdfs: bool = True
    max_pdf_downloads: int = Field(default=3, ge=0, le=10)


class BrowserCaptureResult(BaseModel):
    trace_id: str
    url: str
    domain: str
    status_code: int | None = None
    title: str
    html_path: str
    screenshot_path: str = ""
    blocked_reason: str | None = None
    links: list[dict] = Field(default_factory=list)
    pdf_links: list[dict] = Field(default_factory=list)
    downloaded_pdfs: list[dict] = Field(default_factory=list)
