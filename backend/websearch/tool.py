"""
WebSearch 工具定义 — 注册到 Function Calling 框架

提供 web_search 工具供 Agent 调用
"""
from .searcher import WebSearcher
from ..tools.registry import register_tool

# 全局搜索器实例
_searcher: WebSearcher = None


def get_searcher() -> WebSearcher:
    global _searcher
    if _searcher is None:
        _searcher = WebSearcher()
    return _searcher


@register_tool(
    name="web_search",
    description="实时网络搜索。当需要查询最新政策、分数线、就业数据等实时信息时使用。返回带可信度评分的搜索结果。",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索查询词",
            },
            "search_type": {
                "type": "string",
                "enum": ["general", "policy", "admission", "employment"],
                "description": "搜索类型：general(通用), policy(政策), admission(录取), employment(就业)",
            },
            "school_name": {
                "type": "string",
                "description": "学校名称（admission 搜索时使用）",
            },
            "major_name": {
                "type": "string",
                "description": "专业名称（employment 搜索时使用）",
            },
        },
        "required": ["query"],
    },
)
async def web_search(
    query: str,
    search_type: str = "general",
    school_name: str = "",
    major_name: str = "",
) -> str:
    """执行网络搜索并返回带可信度评分的结果"""
    import json

    searcher = get_searcher()

    if search_type == "policy":
        response = await searcher.search_education_policy(query)
    elif search_type == "admission" and school_name:
        response = await searcher.search_admission_data(school_name)
    elif search_type == "employment" and major_name:
        response = await searcher.search_employment_data(major_name)
    else:
        response = await searcher.search(query)

    # 转换为可序列化的格式
    results = []
    for r in response.results:
        results.append({
            "title": r.title,
            "url": r.url,
            "snippet": r.snippet[:200] + "..." if len(r.snippet) > 200 else r.snippet,
            "source_type": r.source_type.value,
            "credibility_score": r.credibility_score,
            "freshness_level": r.freshness_level.value,
            "freshness_reason": r.freshness_reason,
            "published_date": r.published_date.isoformat() if r.published_date else None,
        })

    return json.dumps({
        "query": response.query,
        "total_results": response.total_results,
        "search_time_ms": response.search_time_ms,
        "results": results,
    }, ensure_ascii=False)
