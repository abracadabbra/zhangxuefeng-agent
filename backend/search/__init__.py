"""
RAG 检索增强生成模块

提供向量存储、嵌入生成和语义搜索功能
"""

from backend.search.crud import semantic_search_majors, semantic_search_schools
from backend.search.embeddings import generate_embedding, generate_embeddings_batch
from backend.search.vector_store import get_or_create_collection, get_vector_store

__all__ = [
    "get_vector_store",
    "get_or_create_collection",
    "generate_embedding",
    "generate_embeddings_batch",
    "semantic_search_schools",
    "semantic_search_majors",
]
