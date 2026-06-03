import httpx
import pytest

from app.tools.arxiv_client import ArxivClient


ARXIV_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2401.01234v1</id>
    <updated>2024-01-04T00:00:00Z</updated>
    <published>2024-01-03T00:00:00Z</published>
    <title>Solid Electrolyte Discovery with Machine Learning</title>
    <summary> We study ionic conductivity in solid electrolytes. </summary>
    <author><name>Ada Lovelace</name></author>
    <arxiv:doi>10.48550/arXiv.2401.01234</arxiv:doi>
    <arxiv:primary_category term="cond-mat.mtrl-sci" />
    <link href="http://arxiv.org/abs/2401.01234v1" rel="alternate" type="text/html" />
    <link title="pdf" href="http://arxiv.org/pdf/2401.01234v1" rel="related" type="application/pdf" />
  </entry>
</feed>
"""


@pytest.mark.asyncio
async def test_arxiv_client_maps_atom_entry_to_paper() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["search_query"] == "all:solid electrolyte"
        assert "TrustSci-Agent/0.1" in request.headers["user-agent"]
        return httpx.Response(200, text=ARXIV_FEED)

    papers = await ArxivClient(transport=httpx.MockTransport(handler)).search("solid electrolyte", 2)

    assert len(papers) == 1
    paper = papers[0]
    assert paper.paper_id == "arxiv:2401.01234v1"
    assert paper.arxiv_id == "2401.01234v1"
    assert paper.doi == "10.48550/arXiv.2401.01234"
    assert paper.year == 2024
    assert paper.pdf_url == "http://arxiv.org/pdf/2401.01234v1"
    assert paper.source_api == "arxiv"
    assert paper.verified_by == ["arxiv"]


@pytest.mark.asyncio
async def test_arxiv_client_handles_empty_query_and_http_errors() -> None:
    assert await ArxivClient().search(" ", 2) == []
    assert await ArxivClient().search("solid", 0) == []

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    assert await ArxivClient(transport=httpx.MockTransport(handler)).search("solid", 2) == []
