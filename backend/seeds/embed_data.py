"""
全量数据嵌入脚本

将学校和专业数据批量嵌入到 ChromaDB 向量数据库
"""

import asyncio
import logging
import os
import sys
from typing import Any, cast

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models.major import Major
from backend.models.school import School
from backend.search.embeddings import (
    build_major_text,
    build_school_text,
    generate_embeddings_batch,
)
from backend.search.vector_store import get_major_collection, get_school_collection

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def embed_schools(db: Session, batch_size: int = 50):
    """
    嵌入所有学校数据

    Args:
        db: 数据库会话
        batch_size: 每批处理的学校数量
    """
    collection = get_school_collection()

    # 查询所有学校
    schools = db.query(School).all()
    logger.info(f"共有 {len(schools)} 所学校需要嵌入")

    if not schools:
        logger.warning("没有找到学校数据")
        return

    # 检查已嵌入的学校数量
    existing_count = collection.count()
    if existing_count > 0:
        logger.info(f"Collection 中已有 {existing_count} 所学校，将跳过已存在的")

    # 分批处理
    for i in range(0, len(schools), batch_size):
        batch = schools[i : i + batch_size]

        # 构建文本和元数据
        texts = []
        ids = []
        metadatas = []

        for school in batch:
            school_id = f"school_{school.id}"

            # 跳过已存在的学校
            try:
                existing = collection.get(ids=[school_id])
                if existing and existing["ids"]:
                    logger.debug(f"跳过已存在的学校: {school.name}")
                    continue
            except Exception:
                pass

            school_data = {
                "name": school.name,
                "province": school.province,
                "city": school.city,
                "level": school.level,
                "school_type": school.school_type,
                "description": school.description or "",
                "is_985": school.is_985,
                "is_211": school.is_211,
                "is_double_first_class": school.is_double_first_class,
            }

            text = build_school_text(school_data)
            texts.append(text)
            ids.append(school_id)
            metadatas.append(
                {
                    "name": school.name,
                    "province": school.province,
                    "city": school.city,
                    "level": school.level,
                    "school_type": school.school_type,
                    "ranking": school.ranking,
                    "is_985": school.is_985 or 0,
                    "is_211": school.is_211 or 0,
                    "is_double_first_class": school.is_double_first_class or 0,
                }
            )

        if not texts:
            continue

        # 生成嵌入向量
        logger.info(f"正在嵌入第 {i // batch_size + 1} 批学校 ({len(texts)} 所)...")
        embeddings = await generate_embeddings_batch(texts)

        # 添加到 Collection
        collection.add(
            ids=ids,
            embeddings=cast(Any, embeddings),
            documents=texts,
            metadatas=cast(Any, metadatas),
        )

        logger.info(f"已嵌入 {min(i + batch_size, len(schools))}/{len(schools)} 所学校")

    logger.info(f"学校嵌入完成，Collection 共有 {collection.count()} 条记录")


async def embed_majors(db: Session, batch_size: int = 50):
    """
    嵌入所有专业数据

    Args:
        db: 数据库会话
        batch_size: 每批处理的专业数量
    """
    collection = get_major_collection()

    # 查询所有专业
    majors = db.query(Major).all()
    logger.info(f"共有 {len(majors)} 个专业需要嵌入")

    if not majors:
        logger.warning("没有找到专业数据")
        return

    # 分批处理
    for i in range(0, len(majors), batch_size):
        batch = majors[i : i + batch_size]

        # 构建文本和元数据
        texts = []
        ids = []
        metadatas = []

        for major in batch:
            major_id = f"major_{major.id}"

            # 跳过已存在的专业
            try:
                existing = collection.get(ids=[major_id])
                if existing and existing["ids"]:
                    logger.debug(f"跳过已存在的专业: {major.name}")
                    continue
            except Exception:
                pass

            major_data = {
                "name": major.name,
                "category": major.category,
                "sub_category": major.sub_category,
                "description": major.description or "",
                "job_directions": major.job_directions or "",
            }

            text = build_major_text(major_data)
            texts.append(text)
            ids.append(major_id)
            metadatas.append(
                {
                    "name": major.name,
                    "category": major.category,
                    "sub_category": major.sub_category,
                    "employment_rate": major.employment_rate,
                    "avg_salary": major.avg_salary,
                    "is_hot": major.is_hot or 0,
                }
            )

        if not texts:
            continue

        # 生成嵌入向量
        logger.info(f"正在嵌入第 {i // batch_size + 1} 批专业 ({len(texts)} 个)...")
        embeddings = await generate_embeddings_batch(texts)

        # 添加到 Collection
        collection.add(
            ids=ids,
            embeddings=cast(Any, embeddings),
            documents=texts,
            metadatas=cast(Any, metadatas),
        )

        logger.info(f"已嵌入 {min(i + batch_size, len(majors))}/{len(majors)} 个专业")

    logger.info(f"专业嵌入完成，Collection 共有 {collection.count()} 条记录")


async def main():
    """主函数"""
    logger.info("=" * 50)
    logger.info("开始全量数据嵌入")
    logger.info("=" * 50)

    db = SessionLocal()
    try:
        # 嵌入学校数据
        await embed_schools(db)

        # 嵌入专业数据
        await embed_majors(db)

        logger.info("=" * 50)
        logger.info("全量数据嵌入完成！")
        logger.info("=" * 50)
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
