import json
from collections.abc import Iterator
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from backend.search import crud
from backend.tools import definitions


@contextmanager
def fake_db() -> Iterator[object]:
    yield object()


@pytest.mark.asyncio
async def test_database_tools_return_source_metadata(monkeypatch: pytest.MonkeyPatch):
    school = SimpleNamespace(
        id=1,
        name="北京大学",
        province="北京",
        city="北京",
        level="本科",
        ranking=1,
        school_type="综合",
        is_985=True,
        is_211=True,
        is_double_first_class=True,
        website="https://www.pku.edu.cn",
        description="综合性大学",
    )
    major = SimpleNamespace(
        id=10,
        name="计算机科学与技术",
        category="工学",
        sub_category="计算机类",
        description="计算机专业",
        employment_rate=0.95,
        avg_salary=12000,
        job_directions=["软件开发"],
        is_hot=True,
    )

    monkeypatch.setattr(definitions, "_get_db", fake_db)
    monkeypatch.setattr(definitions, "get_school_by_name", lambda db, name: school)
    monkeypatch.setattr(definitions, "get_major_by_name", lambda db, name: major)
    monkeypatch.setattr(
        definitions,
        "get_admission_scores",
        lambda db, query: ([{"school_id": school.id, "min_score": 650}], 1),
    )

    payloads = [
        json.loads(await definitions.search_admission("北京大学")),
        json.loads(await definitions.search_employment("计算机科学与技术")),
        json.loads(await definitions.compare_schools(["北京大学"])),
        json.loads(await definitions.calculate_match(650, "北京", "综合")),
    ]

    assert [payload["source"] for payload in payloads] == [
        "admission_scores",
        "majors",
        "schools",
        "admission_scores",
    ]
    for payload in payloads:
        assert payload["confidence"] == "high"
        assert payload["source_type"] == "database"


@pytest.mark.asyncio
async def test_semantic_search_tool_returns_top_level_source_metadata(
    monkeypatch: pytest.MonkeyPatch,
):
    async def fake_semantic_search_schools(**kwargs):
        return [
            {
                "name": "北京邮电大学",
                "confidence": "medium",
                "source_type": "vector_index",
                "source": "chroma:school:school_1",
            }
        ]

    monkeypatch.setattr(crud, "semantic_search_schools", fake_semantic_search_schools)

    payload = json.loads(await definitions.semantic_search("通信强校", "school", top_k=1))

    assert payload["status"] == "success"
    assert payload["confidence"] == "medium"
    assert payload["source_type"] == "vector_index"
    assert payload["source"] == "chroma:school"
    assert payload["results"][0]["source"] == "chroma:school:school_1"
