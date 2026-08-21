import re

from app.schemas.paper import Paper
from app.tools.code_url_extractor import GITHUB_RE, extract_code_urls


def test_github_regex_matches_owner_repo() -> None:
    m = GITHUB_RE.search("code available at https://github.com/owner/repo for details")
    assert m is not None
    assert m.group(1) == "owner/repo"


def test_extract_from_abstract_sets_code_url() -> None:
    p = Paper(paper_id="p1", title="t",
              abstract="We propose X. Code is available at https://github.com/foo/bar.",
              pdf_url=None)
    out = extract_code_urls([p])
    assert out[0].code_url == "https://github.com/foo/bar"


def test_extract_skips_when_no_github_mention() -> None:
    p = Paper(paper_id="p1", title="t", abstract="no link here", pdf_url=None)
    out = extract_code_urls([p])
    assert out[0].code_url is None


def test_extract_does_not_overwrite_existing_code_url() -> None:
    p = Paper(paper_id="p1", title="t", abstract="see https://github.com/a/b", code_url="https://github.com/keep/this")
    out = extract_code_urls([p])
    assert out[0].code_url == "https://github.com/keep/this"
