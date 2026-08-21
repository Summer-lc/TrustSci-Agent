import pytest
from langchain_core.tools import StructuredTool
from pydantic import BaseModel

from app.schemas.paper import Paper
from app.tools.langchain_literature_tools import search_literature_with_tools


class SearchInput(BaseModel):
    query: str
    limit: int = 5


def _search_tool(calls: list[int]) -> StructuredTool:
    async def _search(query: str, limit: int = 5) -> list[dict]:
        calls.append(limit)
        call_no = len(calls)
        return [
            Paper(
                paper_id=f"fake-{call_no}-{idx}",
                title=f"Seismic waveform classification method {idx}",
                source_api="fake",
            ).model_dump(mode="json")
            for idx in range(limit)
        ]

    return StructuredTool.from_function(
        coroutine=_search,
        name="fake_search",
        description="fake search",
        args_schema=SearchInput,
    )


@pytest.mark.asyncio
async def test_langchain_literature_search_uses_router_sized_candidate_pool() -> None:
    calls: list[int] = []
    tool = _search_tool(calls)

    papers, _stats = await search_literature_with_tools(
        queries=["seismic event classification"],
        max_papers=3,
        openalex_search_tool=tool,
        arxiv_search_tool=tool,
        crossref_search_tool=None,
        enable_arxiv=False,
        domain="seismic_event_classification",
    )

    assert calls
    assert all(limit == 8 for limit in calls)
    assert len(papers) == 3
