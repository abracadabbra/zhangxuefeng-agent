"""
5 个工具定义 — 完整实现，对接数据库查询

工具列表：
- search_admission：搜索高校录取分数线
- search_employment：搜索专业就业数据
- compare_schools：院校对比
- search_policy：搜索招生政策
- calculate_match：分数匹配院校推荐
"""
import json
from sqlalchemy.orm import Session

from .registry import register_tool
from ..database import SessionLocal
from ..models.school import School
from ..models.major import Major
from ..models.admission_score import AdmissionScore
from ..crud.school import get_school_by_name, get_schools
from ..crud.major import get_major_by_name, get_majors_by_employment
from ..crud.admission_score import get_admission_scores, get_score_stats
from ..schemas.school import SchoolQuery
from ..schemas.major import MajorQuery
from ..schemas.admission_score import AdmissionScoreQuery


def _get_db() -> Session:
    """获取数据库会话"""
    return SessionLocal()


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
    db = _get_db()
    try:
        # 查找学校
        school = get_school_by_name(db, school_name)
        if not school:
            return json.dumps({
                "status": "not_found",
                "message": f"未找到学校：{school_name}",
                "suggestions": "请检查学校名称是否正确"
            }, ensure_ascii=False)

        # 构建查询
        query = AdmissionScoreQuery(
            school_id=school.id,
            province=province if province else None,
            year=year if year else None,
            subject_type=category if category else None,
            page=1,
            page_size=20
        )

        results, total = get_admission_scores(db, query)

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
            "total": total
        }, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"查询失败：{str(e)}"
        }, ensure_ascii=False)
    finally:
        db.close()


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
    db = _get_db()
    try:
        major = get_major_by_name(db, major_name)
        if not major:
            return json.dumps({
                "status": "not_found",
                "message": f"未找到专业：{major_name}",
                "suggestions": "请检查专业名称是否正确"
            }, ensure_ascii=False)

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
            }
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"查询失败：{str(e)}"
        }, ensure_ascii=False)
    finally:
        db.close()


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
    db = _get_db()
    try:
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
                "message": "未找到任何匹配的学校"
            }, ensure_ascii=False)

        return json.dumps({
            "status": "success",
            "schools": schools,
            "comparison_count": len(schools)
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"对比失败：{str(e)}"
        }, ensure_ascii=False)
    finally:
        db.close()


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
    """搜索招生政策（当前为 stub，后续对接政策数据源）"""
    return json.dumps({
        "status": "not_implemented",
        "message": "招生政策搜索功能待实现",
        "keyword": keyword,
        "school_name": school_name,
        "year": year
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
    db = _get_db()
    try:
        # 根据策略设置分数范围
        if strategy == "冲":
            min_score = score
            max_score = score + 30
        elif strategy == "保":
            min_score = score - 50
            max_score = score
        else:  # 稳
            min_score = score - 20
            max_score = score + 10

        # 查询匹配的分数线记录
        query = AdmissionScoreQuery(
            province=province,
            subject_type=category,
            min_score_floor=int(min_score),
            max_score_ceil=int(max_score),
            page=1,
            page_size=limit * 2  # 多查一些用于去重
        )

        results, total = get_admission_scores(db, query)

        # 按学校去重，取最低分
        school_map = {}
        for r in results:
            sid = r["school_id"]
            if sid not in school_map or r["min_score"] < school_map[sid]["min_score"]:
                school_map[sid] = r

        # 排序并截取
        matched = sorted(school_map.values(), key=lambda x: x["min_score"])[:limit]

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
            "total_matches": len(matched)
        }, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"匹配失败：{str(e)}"
        }, ensure_ascii=False)
    finally:
        db.close()


# 导出所有工具定义供 Agent 使用
from .registry import tool_registry
TOOLS = tool_registry.get_all_definitions()
