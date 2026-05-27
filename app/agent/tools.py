"""
Function Calling 工具定义

定义 Agent 可以调用的工具：
- web_search: 搜索实时信息
- search_admission: 查询录取分数线
- search_employment: 查询就业数据
- compare_schools: 院校对比
- calculate_match: 分数匹配
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "搜索实时信息。用于查询行业报告、政策变化、最新就业数据等。当用户问题涉及需要最新信息时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词，如 '人工智能专业 就业率 2026'",
                    },
                    "search_type": {
                        "type": "string",
                        "enum": ["general", "employment", "admission", "industry"],
                        "description": "搜索类型：general=通用, employment=就业, admission=录取, industry=行业",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_admission",
            "description": "查询院校录取分数线。返回指定学校在指定省份的历年录取数据，包括最低分、平均分、位次。",
            "parameters": {
                "type": "object",
                "properties": {
                    "school": {
                        "type": "string",
                        "description": "学校名称，如 '清华大学'",
                    },
                    "province": {
                        "type": "string",
                        "description": "省份，如 '河南'",
                    },
                    "year": {
                        "type": "integer",
                        "description": "年份，如 2025",
                    },
                },
                "required": ["school", "province"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_employment",
            "description": "查询专业就业数据。返回就业率、薪资中位数、主要就业方向、行业分布。",
            "parameters": {
                "type": "object",
                "properties": {
                    "major": {
                        "type": "string",
                        "description": "专业名称，如 '计算机科学与技术'",
                    },
                    "region": {
                        "type": "string",
                        "description": "地区，如 '北京' 或 '全国'",
                    },
                },
                "required": ["major"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_schools",
            "description": "多维度对比院校。返回排名、就业率、保研率、地理位置等对比数据。",
            "parameters": {
                "type": "object",
                "properties": {
                    "schools": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "学校名称列表，如 ['清华大学', '北京大学']",
                    },
                    "metrics": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["ranking", "employment", "postgrad", "location", "cost"],
                        },
                        "description": "对比维度：ranking=排名, employment=就业, postgrad=保研, location=位置, cost=费用",
                    },
                },
                "required": ["schools"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_match",
            "description": "根据分数和偏好匹配院校。返回可冲、稳妥、保底三个梯度的院校推荐。",
            "parameters": {
                "type": "object",
                "properties": {
                    "score": {
                        "type": "integer",
                        "description": "高考分数",
                    },
                    "province": {
                        "type": "string",
                        "description": "考生所在省份",
                    },
                    "subject": {
                        "type": "string",
                        "description": "文理科：文科/理科/物理类/历史类",
                    },
                    "preference": {
                        "type": "string",
                        "enum": ["school_first", "major_first", "city_first", "balanced"],
                        "description": "偏好：school_first=学校优先, major_first=专业优先, city_first=城市优先, balanced=均衡",
                    },
                },
                "required": ["score", "province", "subject"],
            },
        },
    },
]


def get_tools() -> list[dict]:
    """获取所有工具定义"""
    return TOOLS


def get_tool_descriptions() -> str:
    """获取工具描述文本（用于 Prompt）"""
    lines = ["## 可用工具\n"]
    for tool in TOOLS:
        func = tool["function"]
        lines.append(f"### {func['name']}")
        lines.append(f"**描述**：{func['description']}")
        params = func["parameters"]["properties"]
        lines.append("**参数**：")
        for param_name, param_info in params.items():
            required = param_name in func["parameters"].get("required", [])
            req_str = "（必填）" if required else "（可选）"
            lines.append(f"- `{param_name}` {req_str}: {param_info.get('description', '')}")
        lines.append("")
    return "\n".join(lines)
