"""
WebSearch 模块 — 实时数据检索 + 可信度评分

提供 Tavily/SerpAPI 集成，实现可信度评分、新鲜度标记、数据来源引用
"""
from .searcher import WebSearcher
from .credibility import CredibilityScorer, FreshnessLevel
from .models import SearchResult, SearchResponse

__all__ = ["WebSearcher", "CredibilityScorer", "FreshnessLevel", "SearchResult", "SearchResponse"]
