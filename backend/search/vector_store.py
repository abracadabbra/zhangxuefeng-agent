"""
ChromaDB 向量存储管理

提供 ChromaDB 客户端初始化和 Collection 管理
"""

import logging
import os
from functools import lru_cache

import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)

# ChromaDB 持久化路径，默认放在 backend 目录下
CHROMA_PERSIST_DIR = os.getenv(
    "CHROMA_PERSIST_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), "chroma_data")
)

# Collection 名称
SCHOOL_COLLECTION = "schools"
MAJOR_COLLECTION = "majors"


@lru_cache
def get_vector_store() -> chromadb.ClientAPI:
    """
    获取 ChromaDB 客户端（单例模式）

    使用持久化存储，数据保存在磁盘上
    """
    logger.info(f"初始化 ChromaDB，持久化目录: {CHROMA_PERSIST_DIR}")
    client = chromadb.PersistentClient(
        path=CHROMA_PERSIST_DIR,
        settings=Settings(
            anonymized_telemetry=False,
            allow_reset=True,
        ),
    )
    return client


def get_or_create_collection(name: str, metadata: dict | None = None) -> chromadb.Collection:
    """
    获取或创建 Collection

    Args:
        name: Collection 名称
        metadata: Collection 元数据（如 distance_metric）

    Returns:
        ChromaDB Collection 对象
    """
    client = get_vector_store()
    collection = client.get_or_create_collection(
        name=name, metadata=metadata or {"hnsw:space": "cosine"}
    )
    logger.info(f"Collection '{name}' 已就绪，当前文档数: {collection.count()}")
    return collection


def get_school_collection() -> chromadb.Collection:
    """获取学校 Collection"""
    return get_or_create_collection(SCHOOL_COLLECTION)


def get_major_collection() -> chromadb.Collection:
    """获取专业 Collection"""
    return get_or_create_collection(MAJOR_COLLECTION)


def reset_collections():
    """重置所有 Collection（仅用于测试）"""
    client = get_vector_store()
    client.reset()
    logger.warning("ChromaDB 已重置，所有数据已清除")
