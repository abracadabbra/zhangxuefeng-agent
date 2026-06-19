"""
7 个工具定义 — 完整实现，对接数据库查询

工具列表：
- search_admission：搜索高校录取分数线
- search_enrollment_plan：搜索高校招生计划
- search_employment：搜索专业就业数据
- compare_schools：院校对比
- search_policy：搜索招生政策
- calculate_match：分数匹配院校推荐
- semantic_search：语义搜索学校和专业
"""
import json
from contextlib import contextmanager

from sqlalchemy.orm import Session

from ..crud.admission_score import get_admission_scores
from ..crud.enrollment_plan import get_enrollment_plans
from ..crud.major import get_major_by_name
from ..crud.school import get_school_by_name
from ..data_pipeline.lineage import (
    build_answer_source_policy,
    get_sources_for_entity,
    summarize_sources,
)
from ..database import SessionLocal
from ..schemas.admission_score import AdmissionScoreQuery
from ..schemas.enrollment_plan import EnrollmentPlanQuery
from .registry import register_tool


@contextmanager
def _get_db() -> Session:
    """获取数据库会话（上下文管理器，自动关闭）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _attach_sources_to_items(
    db: Session,
    items: list[dict],
    entity_type: str,
) -> list[dict]:
    """Attach source metadata without changing existing item fields."""
    enriched = []
    for item in items:
        item_with_sources = dict(item)
        entity_id = item.get("id")
        if entity_id is None:
            sources = []
        else:
            sources = get_sources_for_entity(
                db,
                entity_type,
                int(entity_id),
            )
        item_with_sources["sources"] = sources
        item_with_sources["source_summary"] = summarize_sources(sources)
        enriched.append(item_with_sources)
    return enriched


def _summarize_result_sources(items: list[dict]) -> dict:
    """Summarize item-level source metadata for one tool response."""
    summaries = [item.get("source_summary", {}) for item in items]
    items_with_sources = sum(
        1 for summary in summaries if summary.get("citation_ready") is True
    )
    items_needing_caution = sum(
        1 for summary in summaries if summary.get("needs_caution") is True
    )
    source_count = sum(int(summary.get("source_count") or 0) for summary in summaries)
    source_metadata_complete = bool(items) and all(
        summary.get("source_metadata_complete") is True
        for summary in summaries
    )

    return {
        "item_count": len(items),
        "items_with_sources": items_with_sources,
        "items_needing_caution": items_needing_caution,
        "source_count": source_count,
        "citation_ready": bool(items) and items_with_sources == len(items),
        "needs_caution": not items or items_needing_caution > 0,
        "source_metadata_complete": source_metadata_complete,
    }


def _unsupported_source_summary(item_count: int) -> dict:
    """Build a conservative source summary for legacy untraced tool results."""
    return {
        "item_count": item_count,
        "items_with_sources": 0,
        "items_needing_caution": item_count,
        "source_count": 0,
        "citation_ready": False,
        "needs_caution": True,
        "source_metadata_complete": False,
        "source_status": "legacy_untraced",
    }


@register_tool(
    name="search_admission",
    description="搜索高校录取分数线。输入学校名称和可选的省份/年份，返回该校近年录取分数线数据。",
    parameters={
        "type": "object",
        "properties": {
            "school_name": {
                "type": "string",
                "description": "学校名称，如 '北京大学'、'清华大学'",
            },
            "province": {
                "type": "string",
                "description": "考生所在省份，如 '山东'、'河南'",
            },
            "year": {
                "type": "integer",
                "description": "查询年份，默认最近一年",
            },
            "category": {
                "type": "string",
                "enum": ["理科", "文科", "综合"],
                "description": "科类",
            },
        },
        "required": ["school_name"],
    },
)
async def search_admission(school_name: str, province: str = "", year: int = 0, category: str = "") -> str:
    """搜索高校录取分数线"""
    with _get_db() as db:
        school = get_school_by_name(db, school_name)
        if not school:
            return json.dumps({
                "status": "not_found",
                "message": f"未找到学校：{school_name}",
                "hint": "school_name 必须是具体学校名称（如'北京大学'），不能是省份、批次或科类。如需按省份查询，请使用 province 参数。"
            }, ensure_ascii=False)

        query = AdmissionScoreQuery(
            school_id=school.id,
            province=province if province else None,
            year=year if year else None,
            subject_type=category if category else None,
            page=1,
            page_size=20
        )

        results, total = get_admission_scores(db, query)
        results = _attach_sources_to_items(db, results, "admission_score")
        result_source_summary = _summarize_result_sources(results)

        return json.dumps({
            "status": "success",
            "school": {
                "id": school.id,
                "name": school.name,
                "province": school.province,
                "level": school.level,
                "ranking": school.ranking
            },
            "scores": results,
            "source_summary": result_source_summary,
            "answer_source_policy": build_answer_source_policy(
                result_source_summary,
            ),
            "total": total
        }, ensure_ascii=False, default=str)


@register_tool(
    name="search_enrollment_plan",
    description="搜索高校招生计划。输入学校名称和可选专业/省份/年份，返回招生人数、选科要求、学制和学费等信息。",
    parameters={
        "type": "object",
        "properties": {
            "school_name": {
                "type": "string",
                "description": "学校名称，如 '山东大学'、'郑州大学'",
            },
            "major_name": {
                "type": "string",
                "description": "专业名称，如 '计算机科学与技术'，可选",
            },
            "province": {
                "type": "string",
                "description": "招生省份，如 '山东'、'河南'",
            },
            "year": {
                "type": "integer",
                "description": "查询年份，默认最近一年",
            },
        },
        "required": ["school_name"],
    },
)
async def search_enrollment_plan(
    school_name: str,
    major_name: str = "",
    province: str = "",
    year: int = 0,
) -> str:
    """搜索高校招生计划"""
    with _get_db() as db:
        school = get_school_by_name(db, school_name)
        if not school:
            return json.dumps({
                "status": "not_found",
                "message": f"未找到学校：{school_name}",
                "hint": "school_name 必须是具体学校名称，如'山东大学'。",
            }, ensure_ascii=False)

        query = EnrollmentPlanQuery(
            school_id=school.id,
            major_name=major_name if major_name else None,
            province=province if province else None,
            year=year if year else None,
            page=1,
            page_size=20,
        )

        results, total = get_enrollment_plans(db, query)
        results = _attach_sources_to_items(db, results, "enrollment_plan")
        result_source_summary = _summarize_result_sources(results)

        return json.dumps({
            "status": "success",
            "school": {
                "id": school.id,
                "name": school.name,
                "province": school.province,
                "level": school.level,
                "ranking": school.ranking,
            },
            "plans": results,
            "source_summary": result_source_summary,
            "answer_source_policy": build_answer_source_policy(
                result_source_summary,
            ),
            "total": total,
        }, ensure_ascii=False, default=str)


@register_tool(
    name="search_employment",
    description="搜索专业就业数据。输入专业名称，返回就业率、平均薪资、就业方向等信息。",
    parameters={
        "type": "object",
        "properties": {
            "major_name": {
                "type": "string",
                "description": "专业名称，如 '计算机科学与技术'、'金融学'",
            },
            "degree_level": {
                "type": "string",
                "enum": ["本科", "硕士", "博士"],
                "description": "学历层次",
            },
        },
        "required": ["major_name"],
    },
)
async def search_employment(major_name: str, degree_level: str = "") -> str:
    """搜索专业就业数据"""
    with _get_db() as db:
        major = get_major_by_name(db, major_name)
        if not major:
            return json.dumps({
                "status": "not_found",
                "message": f"未找到专业：{major_name}",
                "hint": "major_name 必须是具体专业名称（如'计算机科学与技术'），不能是大类（如'工科'）或行业（如'互联网'）。"
            }, ensure_ascii=False)

        source_summary = _unsupported_source_summary(1)
        return json.dumps({
            "status": "success",
            "major": {
                "id": major.id,
                "name": major.name,
                "category": major.category,
                "sub_category": major.sub_category,
                "description": major.description
            },
            "employment": {
                "employment_rate": major.employment_rate,
                "avg_salary": major.avg_salary,
                "job_directions": major.job_directions,
                "is_hot": major.is_hot
            },
            "source_summary": source_summary,
            "answer_source_policy": build_answer_source_policy(source_summary),
        }, ensure_ascii=False)


@register_tool(
    name="compare_schools",
    description="对比多所院校的综合实力、学科排名、就业数据等。输入学校名称列表，返回对比表格。",
    parameters={
        "type": "object",
        "properties": {
            "school_names": {
                "type": "array",
                "items": {"type": "string"},
                "description": "要对比的学校名称列表，如 ['北京大学', '清华大学', '复旦大学']",
            },
            "dimensions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "对比维度，如 ['综合排名', '学科实力', '就业率', '地理位置']",
            },
        },
        "required": ["school_names"],
    },
)
async def compare_schools(school_names: list[str], dimensions: list[str] | None = None) -> str:
    """对比多所院校"""
    with _get_db() as db:
        schools = []
        for name in school_names:
            school = get_school_by_name(db, name)
            if school:
                schools.append({
                    "id": school.id,
                    "name": school.name,
                    "province": school.province,
                    "city": school.city,
                    "level": school.level,
                    "school_type": school.school_type,
                    "ranking": school.ranking,
                    "is_985": school.is_985,
                    "is_211": school.is_211,
                    "is_double_first_class": school.is_double_first_class,
                    "website": school.website,
                    "description": school.description
                })

        if not schools:
            return json.dumps({
                "status": "not_found",
                "message": "未找到任何匹配的学校",
                "hint": "请确保传入的是具体学校名称列表（如['北京大学','清华大学']），不是省份或批次。"
            }, ensure_ascii=False)

        source_summary = _unsupported_source_summary(len(schools))
        return json.dumps({
            "status": "success",
            "schools": schools,
            "comparison_count": len(schools),
            "source_summary": source_summary,
            "answer_source_policy": build_answer_source_policy(source_summary),
        }, ensure_ascii=False)


@register_tool(
    name="search_policy",
    description="搜索招生政策。输入关键词或学校名称，返回相关的招生政策、录取规则、特殊要求等。",
    parameters={
        "type": "object",
        "properties": {
            "keyword": {
                "type": "string",
                "description": "搜索关键词，如 '强基计划'、'提前批'、'艺术特长生'",
            },
            "school_name": {
                "type": "string",
                "description": "学校名称（可选），限定搜索范围",
            },
            "year": {
                "type": "integer",
                "description": "政策年份",
            },
        },
        "required": ["keyword"],
    },
)
async def search_policy(keyword: str, school_name: str = "", year: int = 0) -> str:
    """搜索招生政策（基于预置政策库）"""
    policy_db = {
        "强基计划": {
            "title": "强基计划",
            "summary": "教育部自2020年起实施的招生改革计划，聚焦高端芯片与软件、智能科技、新材料、先进制造和国家安全等关键领域。36所双一流A类高校参与，高考成绩占比不低于85%，校测成绩占比不超过15%。",
            "key_points": ["报名时间一般在4月", "只能报考1所高校", "录取在提前批之前", "入校后原则上不得转专业"],
            "source": "教育部阳光高考平台",
        },
        "提前批": {
            "title": "提前批次录取",
            "summary": "在普通批次之前进行录取的批次，包括军事、公安、航海、消防、公费师范生、定向医学生等类型。未被录取不影响后续批次。",
            "key_points": ["一般在6月底填报", "不影响后续批次录取", "部分有体检/面试要求", "公费师范生需回生源地任教6年"],
            "source": "各省教育考试院",
        },
        "综合评价": {
            "title": "综合评价招生",
            "summary": "综合高考成绩、校测成绩和学业水平考试成绩进行录取的招生模式。高考成绩占比一般不低于60%。",
            "key_points": ["部分高校在部分省份试点", "需要额外申请和参加校测", "录取批次一般在提前批", "代表高校：南科大、上科大、昆山杜克等"],
            "source": "各高校招生简章",
        },
        "艺术特长生": {
            "title": "艺术特长生招生",
            "summary": "2024年起已取消高校高水平艺术团招生，改为从在校生中遴选。艺术类专业招生仍保留，但文化课要求提高。",
            "key_points": ["2024年起取消高水平艺术团招生", "艺术类专业招生仍保留", "文化课成绩要求逐步提高至普通类本科线"],
            "source": "教育部2021年艺考改革文件",
        },
        "专项计划": {
            "title": "高校专项计划",
            "summary": "面向农村和脱贫地区学生的定向招生计划，包括国家专项、地方专项和高校专项三类。可降分录取，最多可降20分。",
            "key_points": ["国家专项：面向集中连片特殊困难县等", "地方专项：面向各省实施区域农村学生", "高校专项：95所高校，需单独报名", "一般可降5-20分录取"],
            "source": "教育部高校招生工作规定",
        },
    }

    # 模糊匹配
    matched_policies = []
    for key, policy in policy_db.items():
        if key in keyword or keyword in key:
            matched_policies.append(policy)

    # 如果没有精确匹配，返回关键词相关的通用建议
    if not matched_policies:
        # 尝试匹配部分关键词
        for key, policy in policy_db.items():
            for char in keyword:
                if char in key:
                    matched_policies.append(policy)
                    break
            if matched_policies:
                break

    if matched_policies:
        source_summary = _unsupported_source_summary(len(matched_policies))
        return json.dumps({
            "status": "success",
            "query": keyword,
            "results": matched_policies,
            "source": "预置政策库（仅供参考，请以各省教育考试院最新公告为准）",
            "disclaimer": "政策信息可能存在时效性，请以官方最新发布为准。",
            "source_summary": source_summary,
            "answer_source_policy": build_answer_source_policy(source_summary),
        }, ensure_ascii=False)

    return json.dumps({
        "status": "not_found",
        "message": f"未找到与「{keyword}」直接相关的政策信息。常见政策包括：强基计划、提前批、综合评价、专项计划等。",
        "suggestions": "请尝试更具体的关键词，如「强基计划」「提前批」「综合评价」「专项计划」。",
        "source": "预置政策库",
    }, ensure_ascii=False)


@register_tool(
    name="calculate_match",
    description="根据考生分数和条件，推荐匹配的院校。输入分数、省份、科类等，返回推荐院校列表及录取概率。",
    parameters={
        "type": "object",
        "properties": {
            "score": {
                "type": "number",
                "description": "考生分数",
            },
            "province": {
                "type": "string",
                "description": "考生所在省份",
            },
            "category": {
                "type": "string",
                "enum": ["理科", "文科", "综合"],
                "description": "科类",
            },
            "strategy": {
                "type": "string",
                "enum": ["冲", "稳", "保"],
                "description": "填报策略：冲一冲、稳一稳、保一保",
            },
            "limit": {
                "type": "integer",
                "description": "返回结果数量，默认 10",
            },
        },
        "required": ["score", "province", "category"],
    },
)
async def calculate_match(score: float, province: str, category: str, strategy: str = "", limit: int = 10) -> str:
    """分数匹配院校推荐"""
    with _get_db() as db:
        if strategy == "冲":
            min_score = score
            max_score = score + 30
        elif strategy == "保":
            min_score = score - 50
            max_score = score
        else:
            min_score = score - 20
            max_score = score + 10

        query = AdmissionScoreQuery(
            province=province,
            subject_type=category,
            min_score_floor=int(min_score),
            max_score_ceil=int(max_score),
            page=1,
            page_size=limit * 2
        )

        results, total = get_admission_scores(db, query)
        results = _attach_sources_to_items(db, results, "admission_score")

        school_map = {}
        for r in results:
            sid = r["school_id"]
            if sid not in school_map or r["min_score"] < school_map[sid]["min_score"]:
                school_map[sid] = r

        matched = sorted(school_map.values(), key=lambda x: x["min_score"])[:limit]
        result_source_summary = _summarize_result_sources(matched)

        return json.dumps({
            "status": "success",
            "query": {
                "score": score,
                "province": province,
                "category": category,
                "strategy": strategy or "稳",
                "score_range": f"{int(min_score)}-{int(max_score)}"
            },
            "matched_schools": matched,
            "source_summary": result_source_summary,
            "answer_source_policy": build_answer_source_policy(
                result_source_summary,
            ),
            "total_matches": len(matched)
        }, ensure_ascii=False, default=str)


@register_tool(
    name="semantic_search",
    description="语义搜索学校和专业。支持自然语言查询，如'计算机相关专业'、'北京的985高校'等。使用向量相似度匹配，能理解查询意图。",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索查询，支持自然语言，如 '计算机相关专业'、'就业率高的医学专业'、'北京的985高校'",
            },
            "type": {
                "type": "string",
                "enum": ["school", "major"],
                "description": "搜索类型：school（学校）或 major（专业）",
            },
            "province": {
                "type": "string",
                "description": "省份过滤（仅对学校有效），如 '北京'、'上海'",
            },
            "category": {
                "type": "string",
                "description": "学科门类过滤（仅对专业有效），如 '工学'、'医学'",
            },
            "top_k": {
                "type": "integer",
                "description": "返回结果数量，默认 10",
            },
        },
        "required": ["query", "type"],
    },
)
async def semantic_search(
    query: str,
    type: str,
    province: str = "",
    category: str = "",
    top_k: int = 10,
) -> str:
    """语义搜索学校和专业"""
    from ..search.crud import semantic_search_majors, semantic_search_schools

    try:
        if type == "school":
            results = await semantic_search_schools(
                query=query,
                province=province if province else None,
                top_k=top_k,
            )
            source_summary = _unsupported_source_summary(len(results))
            return json.dumps({
                "status": "success",
                "type": "school",
                "query": query,
                "results": results,
                "total": len(results),
                "source_summary": source_summary,
                "answer_source_policy": build_answer_source_policy(source_summary),
            }, ensure_ascii=False)
        elif type == "major":
            results = await semantic_search_majors(
                query=query,
                category=category if category else None,
                top_k=top_k,
            )
            source_summary = _unsupported_source_summary(len(results))
            return json.dumps({
                "status": "success",
                "type": "major",
                "query": query,
                "results": results,
                "total": len(results),
                "source_summary": source_summary,
                "answer_source_policy": build_answer_source_policy(source_summary),
            }, ensure_ascii=False)
        else:
            return json.dumps({
                "status": "error",
                "message": f"不支持的搜索类型: {type}，请使用 'school' 或 'major'",
            }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"语义搜索失败: {str(e)}",
            "hint": "请确保已运行数据嵌入脚本: python -m backend.seeds.embed_data",
        }, ensure_ascii=False)


# 导出所有工具定义供 Agent 使用
from .registry import tool_registry

TOOLS = tool_registry.get_all_definitions()
