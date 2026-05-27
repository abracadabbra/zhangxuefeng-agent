"""
会话管理 + 上下文管理 单元测试
"""
import pytest
from app.services.context import extract_entities, merge_entities, ExtractedEntities


# ========== 实体提取测试 ==========

class TestExtractEntities:
    """测试从消息中提取实体"""

    def test_extract_score(self):
        entities = extract_entities("我考了600分")
        assert entities.score == 600

    def test_extract_score_with_space(self):
        entities = extract_entities("考了 580 分")
        assert entities.score == 580

    def test_extract_province(self):
        entities = extract_entities("我是河南的考生")
        assert entities.province == "河南"

    def test_extract_subject_liberal(self):
        entities = extract_entities("我是文科生")
        assert entities.subject == "文科"

    def test_extract_subject_science(self):
        entities = extract_entities("孩子学的理科")
        assert entities.subject == "理科"

    def test_extract_family_business(self):
        entities = extract_entities("家里做生意的")
        assert entities.family_background == "经商家庭"

    def test_extract_family_worker(self):
        entities = extract_entities("普通工薪家庭")
        assert entities.family_background == "工薪阶层"

    def test_extract_no_entities(self):
        entities = extract_entities("你好")
        assert entities.score is None
        assert entities.province is None
        assert entities.subject is None
        assert entities.family_background is None


# ========== 实体合并测试 ==========

class TestMergeEntities:
    """测试实体合并"""

    def test_merge_new_over_none(self):
        existing = ExtractedEntities()
        new = ExtractedEntities(score=600, province="河南")
        merged = merge_entities(existing, new)
        assert merged.score == 600
        assert merged.province == "河南"

    def test_merge_existing_preserved(self):
        existing = ExtractedEntities(score=600)
        new = ExtractedEntities(province="河南")
        merged = merge_entities(existing, new)
        assert merged.score == 600
        assert merged.province == "河南"

    def test_merge_new_overwrites_none(self):
        existing = ExtractedEntities(score=None)
        new = ExtractedEntities(score=580)
        merged = merge_entities(existing, new)
        assert merged.score == 580

    def test_merge_existing_not_overwritten(self):
        existing = ExtractedEntities(score=600)
        new = ExtractedEntities(score=580)
        merged = merge_entities(existing, new)
        assert merged.score == 580  # 新值覆盖旧值
