"""
向量查询 CRUD 操作

提供语义搜索功能，支持元数据过滤
"""

import logging
from typing import TypeGuard, cast

from chromadb.api.types import Embeddings, Metadata, QueryResult, Where

from backend.search.embeddings import generate_embedding
from backend.search.vector_store import get_major_collection, get_school_collection

logger = logging.getLogger(__name__)

# 默认搜索参数
DEFAULT_TOP_K = 10
DEFAULT_DISTANCE_THRESHOLD = 0.5  # 相似度阈值，越小越严格


def _is_number(value: object) -> TypeGuard[int | float]:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _metadata_number(metadata: Metadata, key: str) -> int | float | None:
    value = metadata.get(key)
    if _is_number(value):
        return value
    return None


def _confidence_from_similarity(similarity: float) -> str:
    if similarity >= 0.85:
        return "high"
    if similarity >= 0.7:
        return "medium"
    return "low"


def _result_source(kind: str, doc_id: str) -> dict[str, str]:
    return {
        "source_type": "vector_index",
        "source": f"chroma:{kind}:{doc_id}",
    }


async def semantic_search_schools(
    query: str,
    province: str | None = None,
    level: str | None = None,
    is_985: bool | None = None,
    is_211: bool | None = None,
    top_k: int = DEFAULT_TOP_K,
    distance_threshold: float = DEFAULT_DISTANCE_THRESHOLD,
) -> list[dict]:
    """
    语义搜索学校

    Args:
        query: 用户查询文本
        province: 省份过滤
        level: 学校层次过滤（985/211/双一流/普通）
        is_985: 是否 985 高校
        is_211: 是否 211 高校
        top_k: 返回结果数量
        distance_threshold: 相似度阈值（0-1，越小越严格）

    Returns:
        匹配的学校列表，包含相似度分数
    """
    collection = get_school_collection()

    if collection.count() == 0:
        logger.warning("学校 Collection 为空，请先运行数据嵌入脚本")
        return []

    # 生成查询向量
    query_embedding = await generate_embedding(query)

    # 构建元数据过滤条件
    where_conditions: list[Where] = []
    if province:
        where_conditions.append({"province": province})
    if level:
        where_conditions.append({"level": level})
    if is_985 is not None:
        where_conditions.append({"is_985": 1 if is_985 else 0})
    if is_211 is not None:
        where_conditions.append({"is_211": 1 if is_211 else 0})

    where: Where | None = None
    if len(where_conditions) == 1:
        where = where_conditions[0]
    elif len(where_conditions) > 1:
        where = {"$and": where_conditions}

    # 执行向量搜索
    results: QueryResult = collection.query(
        query_embeddings=cast(Embeddings, [query_embedding]),
        n_results=top_k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    # 处理结果
    schools = []
    metadatas = results.get("metadatas")
    distances = results.get("distances")
    if results["ids"] and results["ids"][0] and metadatas and distances:
        for i, doc_id in enumerate(results["ids"][0]):
            distance = distances[0][i]
            # cosine distance: 0 = 完全相同，2 = 完全不同
            # 转换为相似度分数: 1 - distance/2
            similarity = 1 - distance / 2

            if similarity >= (1 - distance_threshold):
                metadata = metadatas[0][i]
                schools.append(
                    {
                        "id": int(doc_id.replace("school_", "")),
                        "name": metadata.get("name", ""),
                        "province": metadata.get("province", ""),
                        "level": metadata.get("level", ""),
                        "school_type": metadata.get("school_type", ""),
                        "ranking": metadata.get("ranking"),
                        "is_985": metadata.get("is_985", 0),
                        "is_211": metadata.get("is_211", 0),
                        "similarity": round(similarity, 4),
                        "confidence": _confidence_from_similarity(similarity),
                        **_result_source("school", doc_id),
                    }
                )

    logger.info(f"语义搜索 '{query}'，找到 {len(schools)} 所学校")
    return schools


async def semantic_search_majors(
    query: str,
    category: str | None = None,
    is_hot: bool | None = None,
    min_employment_rate: float | None = None,
    top_k: int = DEFAULT_TOP_K,
    distance_threshold: float = DEFAULT_DISTANCE_THRESHOLD,
) -> list[dict]:
    """
    语义搜索专业

    Args:
        query: 用户查询文本
        category: 学科门类过滤
        is_hot: 是否热门专业
        min_employment_rate: 最低就业率
        top_k: 返回结果数量
        distance_threshold: 相似度阈值

    Returns:
        匹配的专业列表，包含相似度分数
    """
    collection = get_major_collection()

    if collection.count() == 0:
        logger.warning("专业 Collection 为空，请先运行数据嵌入脚本")
        return []

    # 生成查询向量
    query_embedding = await generate_embedding(query)

    # 构建元数据过滤条件
    where_conditions: list[Where] = []
    if category:
        where_conditions.append({"category": category})
    if is_hot is not None:
        where_conditions.append({"is_hot": 1 if is_hot else 0})

    where: Where | None = None
    if len(where_conditions) == 1:
        where = where_conditions[0]
    elif len(where_conditions) > 1:
        where = {"$and": where_conditions}

    # 执行向量搜索
    results: QueryResult = collection.query(
        query_embeddings=cast(Embeddings, [query_embedding]),
        n_results=top_k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    # 处理结果
    majors = []
    metadatas = results.get("metadatas")
    distances = results.get("distances")
    if results["ids"] and results["ids"][0] and metadatas and distances:
        for i, doc_id in enumerate(results["ids"][0]):
            distance = distances[0][i]
            similarity = 1 - distance / 2

            if similarity >= (1 - distance_threshold):
                metadata = metadatas[0][i]

                # 就业率过滤（ChromaDB 不支持浮点数范围过滤，这里手动过滤）
                employment_rate = _metadata_number(metadata, "employment_rate")
                if min_employment_rate is not None:
                    if employment_rate is None or employment_rate < min_employment_rate:
                        continue

                majors.append(
                    {
                        "id": int(doc_id.replace("major_", "")),
                        "name": metadata.get("name", ""),
                        "category": metadata.get("category", ""),
                        "sub_category": metadata.get("sub_category", ""),
                        "employment_rate": employment_rate,
                        "avg_salary": metadata.get("avg_salary"),
                        "is_hot": metadata.get("is_hot", 0),
                        "similarity": round(similarity, 4),
                        "confidence": _confidence_from_similarity(similarity),
                        **_result_source("major", doc_id),
                    }
                )

    logger.info(f"语义搜索 '{query}'，找到 {len(majors)} 个专业")
    return majors


async def add_school_to_index(school_id: int, school_data: dict, embedding: list[float]):
    """
    将学校添加到向量索引

    Args:
        school_id: 学校 ID
        school_data: 学校数据
        embedding: 嵌入向量
    """
    collection = get_school_collection()

    collection.add(
        ids=[f"school_{school_id}"],
        embeddings=cast(Embeddings, [embedding]),
        documents=[school_data.get("description", "")],
        metadatas=[
            {
                "name": school_data.get("name", ""),
                "province": school_data.get("province", ""),
                "city": school_data.get("city", ""),
                "level": school_data.get("level", ""),
                "school_type": school_data.get("school_type", ""),
                "ranking": school_data.get("ranking"),
                "is_985": school_data.get("is_985", 0),
                "is_211": school_data.get("is_211", 0),
                "is_double_first_class": school_data.get("is_double_first_class", 0),
            }
        ],
    )


async def add_major_to_index(major_id: int, major_data: dict, embedding: list[float]):
    """
    将专业添加到向量索引

    Args:
        major_id: 专业 ID
        major_data: 专业数据
        embedding: 嵌入向量
    """
    collection = get_major_collection()

    collection.add(
        ids=[f"major_{major_id}"],
        embeddings=cast(Embeddings, [embedding]),
        documents=[major_data.get("description", "")],
        metadatas=[
            {
                "name": major_data.get("name", ""),
                "category": major_data.get("category", ""),
                "sub_category": major_data.get("sub_category", ""),
                "employment_rate": major_data.get("employment_rate"),
                "avg_salary": major_data.get("avg_salary"),
                "is_hot": major_data.get("is_hot", 0),
            }
        ],
    )
