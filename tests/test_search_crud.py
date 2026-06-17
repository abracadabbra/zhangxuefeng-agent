import pytest

from backend.search import crud


class FakeCollection:
    def __init__(self, result):
        self.result = result
        self.last_query = None

    def count(self):
        return 1

    def query(self, **kwargs):
        self.last_query = kwargs
        return self.result


@pytest.mark.asyncio
async def test_semantic_search_schools_builds_filters_and_applies_threshold(monkeypatch):
    collection = FakeCollection(
        {
            "ids": [["school_1", "school_2"]],
            "metadatas": [
                [
                    {
                        "name": "测试大学",
                        "province": "北京",
                        "level": "985",
                        "school_type": "综合",
                        "ranking": 1,
                        "is_985": 1,
                        "is_211": 1,
                    },
                    {
                        "name": "低相似大学",
                        "province": "北京",
                        "level": "985",
                        "school_type": "综合",
                    },
                ]
            ],
            "distances": [[0.2, 1.2]],
        }
    )

    async def fake_embedding(query):
        assert query == "北京 综合"
        return [0.1, 0.2]

    monkeypatch.setattr(crud, "get_school_collection", lambda: collection)
    monkeypatch.setattr(crud, "generate_embedding", fake_embedding)

    results = await crud.semantic_search_schools(
        "北京 综合",
        province="北京",
        level="985",
        is_985=True,
        top_k=5,
        distance_threshold=0.5,
    )

    assert collection.last_query["n_results"] == 5
    assert collection.last_query["where"] == {
        "$and": [{"province": "北京"}, {"level": "985"}, {"is_985": 1}]
    }
    assert results == [
        {
            "id": 1,
            "name": "测试大学",
            "province": "北京",
            "level": "985",
            "school_type": "综合",
            "ranking": 1,
            "is_985": 1,
            "is_211": 1,
            "similarity": 0.9,
            "confidence": "high",
            "source_type": "vector_index",
            "source": "chroma:school:school_1",
        }
    ]


@pytest.mark.asyncio
async def test_semantic_search_majors_requires_numeric_employment_rate_when_filtered(
    monkeypatch,
):
    collection = FakeCollection(
        {
            "ids": [["major_1", "major_2", "major_3"]],
            "metadatas": [
                [
                    {
                        "name": "计算机科学与技术",
                        "category": "工学",
                        "sub_category": "计算机类",
                        "employment_rate": 0.92,
                        "avg_salary": 18000,
                        "is_hot": 1,
                    },
                    {
                        "name": "低就业专业",
                        "category": "工学",
                        "employment_rate": 0.7,
                    },
                    {
                        "name": "缺失就业率专业",
                        "category": "工学",
                    },
                ]
            ],
            "distances": [[0.1, 0.1, 0.1]],
        }
    )

    async def fake_embedding(_query):
        return [0.1, 0.2]

    monkeypatch.setattr(crud, "get_major_collection", lambda: collection)
    monkeypatch.setattr(crud, "generate_embedding", fake_embedding)

    results = await crud.semantic_search_majors(
        "高就业 工科",
        category="工学",
        is_hot=True,
        min_employment_rate=0.85,
    )

    assert collection.last_query["where"] == {"$and": [{"category": "工学"}, {"is_hot": 1}]}
    assert [item["name"] for item in results] == ["计算机科学与技术"]
    assert results[0]["employment_rate"] == 0.92
    assert results[0]["confidence"] == "high"
    assert results[0]["source_type"] == "vector_index"
    assert results[0]["source"] == "chroma:major:major_1"
