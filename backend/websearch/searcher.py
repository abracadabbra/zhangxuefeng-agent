"""
WebSearch 搜索器 — 集成 Tavily/SerpAPI 实时数据检索

提供搜索功能，结合可信度评分机制
"""
import os
import time
import logging
from datetime import datetime
from typing import Optional

import httpx

from .models import SearchResult, SearchResponse, SourceType
from .credibility import CredibilityScorer

logger = logging.getLogger(__name__)

# Tavily API 配置
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
TAVILY_BASE_URL = "https://api.tavily.com"


class WebSearcher:
    """Web 搜索器 — 集成 Tavily API"""

    def __init__(self, api_key: str = "", max_results: int = 10):
        self.api_key = api_key or TAVILY_API_KEY
        self.max_results = max_results
        self.scorer = CredibilityScorer()

    async def search(
        self,
        query: str,
        search_depth: str = "basic",
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
    ) -> SearchResponse:
        """
        执行搜索

        Args:
            query: 搜索查询
            search_depth: 搜索深度 "basic" 或 "advanced"
            include_domains: 限定搜索域名
            exclude_domains: 排除搜索域名

        Returns:
            SearchResponse 包含评分后的搜索结果
        """
        start_time = time.time()

        if not self.api_key:
            logger.warning("Tavily API key not configured, returning empty results")
            return SearchResponse(
                query=query,
                results=[],
                total_results=0,
                search_time_ms=0.0,
                source="tavily",
            )

        try:
            results = await self._call_tavily_api(
                query=query,
                search_depth=search_depth,
                include_domains=include_domains,
                exclude_domains=exclude_domains,
            )
        except Exception as e:
            logger.error(f"Search failed: {e}")
            results = []

        # 应用可信度评分
        scored_results = self.scorer.score_results(results)

        search_time = (time.time() - start_time) * 1000

        return SearchResponse(
            query=query,
            results=scored_results,
            total_results=len(scored_results),
            search_time_ms=round(search_time, 2),
            source="tavily",
        )

    async def _call_tavily_api(
        self,
        query: str,
        search_depth: str = "basic",
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
    ) -> list[SearchResult]:
        """调用 Tavily API"""
        payload = {
            "query": query,
            "search_depth": search_depth,
            "max_results": self.max_results,
            "include_answer": False,
            "include_raw_content": False,
        }

        if include_domains:
            payload["include_domains"] = include_domains
        if exclude_domains:
            payload["exclude_domains"] = exclude_domains

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{TAVILY_BASE_URL}/search",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        results = []
        for item in data.get("results", []):
            # 解析发布日期
            published_date = None
            if raw_date := item.get("published_date"):
                try:
                    published_date = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    pass

            results.append(SearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=item.get("content", ""),
                published_date=published_date,
            ))

        return results

    async def search_education_policy(self, keyword: str) -> SearchResponse:
        """搜索教育政策（限定政府和教育类网站）"""
        return await self.search(
            query=keyword,
            search_depth="advanced",
            include_domains=[
                "moe.gov.cn",
                "chsi.com.cn",
                "eol.cn",
                "gaokao.com",
            ],
        )

    async def search_admission_data(self, school_name: str, year: int = 0) -> SearchResponse:
        """搜索高校录取数据"""
        query = f"{school_name} 录取分数线"
        if year:
            query += f" {year}年"

        return await self.search(
            query=query,
            search_depth="advanced",
            include_domains=[
                "eol.cn",
                "gaokao.com",
                "chsi.com.cn",
            ],
        )

    async def search_employment_data(self, major_name: str) -> SearchResponse:
        """搜索专业就业数据"""
        return await self.search(
            query=f"{major_name} 就业前景 薪资",
            search_depth="basic",
            include_domains=[
                "people.com.cn",
                "xinhuanet.com",
                "eol.cn",
            ],
        )
