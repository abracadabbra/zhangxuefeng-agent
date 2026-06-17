"""
嵌入向量生成模块

默认使用本地 bge-small-zh-v1.5 模型（免费、离线、中文效果好）
可通过环境变量切换为 OpenAI API 模式

环境变量配置：
- EMBEDDING_PROVIDER: "local"（默认）或 "openai"
- EMBEDDING_MODEL: 模型名称（本地默认 BAAI/bge-small-zh-v1.5，OpenAI 默认 text-embedding-3-small）
- EMBEDDING_BASE_URL: OpenAI 嵌入专用 API 端点（仅 openai 模式）
- OPENAI_BASE_URL: 通用 OpenAI API 端点（仅 openai 模式，回退选项）
"""

import logging
import os
from functools import lru_cache

logger = logging.getLogger(__name__)

# 嵌入配置
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "local")

# 本地模型维度：bge-small-zh-v1.5 = 512
LOCAL_EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")
LOCAL_EMBEDDING_DIMENSION = 512

# OpenAI 模型维度
OPENAI_EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
OPENAI_EMBEDDING_DIMENSION = 1536

# 当前使用的维度
EMBEDDING_DIMENSION = (
    LOCAL_EMBEDDING_DIMENSION if EMBEDDING_PROVIDER == "local" else OPENAI_EMBEDDING_DIMENSION
)


@lru_cache
def _get_local_model():
    """获取本地 SentenceTransformer 模型（单例）"""
    from sentence_transformers import SentenceTransformer

    logger.info(f"加载本地嵌入模型: {LOCAL_EMBEDDING_MODEL}")
    model = SentenceTransformer(LOCAL_EMBEDDING_MODEL)
    logger.info("本地嵌入模型加载完成")
    return model


@lru_cache
def _get_openai_client():
    """获取 OpenAI 异步客户端（单例）"""
    from openai import AsyncOpenAI

    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
    base_url = (
        os.getenv("EMBEDDING_BASE_URL") or os.getenv("OPENAI_BASE_URL") or os.getenv("LLM_BASE_URL")
    )
    if not api_key:
        raise ValueError("OPENAI_API_KEY 或 LLM_API_KEY 环境变量未设置")
    return AsyncOpenAI(api_key=api_key, base_url=base_url)


async def generate_embedding(text: str) -> list[float]:
    """
    生成单个文本的嵌入向量

    Args:
        text: 要嵌入的文本

    Returns:
        嵌入向量
    """
    import asyncio

    text = text.replace("\n", " ").strip()
    if not text:
        raise ValueError("文本不能为空")

    if EMBEDDING_PROVIDER == "local":
        model = _get_local_model()
        # 本地推理是同步的，放到线程池避免阻塞事件循环
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(None, lambda: model.encode(text).tolist())
        return embedding
    else:
        client = _get_openai_client()
        response = await client.embeddings.create(model=OPENAI_EMBEDDING_MODEL, input=text)
        return response.data[0].embedding


async def generate_embeddings_batch(
    texts: list[str],
    batch_size: int = 100,
) -> list[list[float]]:
    """
    批量生成嵌入向量

    Args:
        texts: 要嵌入的文本列表
        batch_size: 每批处理的文本数量（仅 openai 模式使用）

    Returns:
        嵌入向量列表
    """
    import asyncio

    cleaned_texts = [t.replace("\n", " ").strip() for t in texts]

    if EMBEDDING_PROVIDER == "local":
        model = _get_local_model()
        loop = asyncio.get_event_loop()
        # 本地模型一次性批量编码，效率更高
        embeddings = await loop.run_in_executor(None, lambda: model.encode(cleaned_texts).tolist())
        return embeddings
    else:
        client = _get_openai_client()
        all_embeddings = []
        for i in range(0, len(cleaned_texts), batch_size):
            batch = cleaned_texts[i : i + batch_size]
            valid_indices = [j for j, t in enumerate(batch) if t]
            valid_texts = [batch[j] for j in valid_indices]

            if not valid_texts:
                all_embeddings.extend([[0.0] * OPENAI_EMBEDDING_DIMENSION] * len(batch))
                continue

            logger.info(f"生成嵌入: 第 {i // batch_size + 1} 批，共 {len(valid_texts)} 个文本")
            response = await client.embeddings.create(
                model=OPENAI_EMBEDDING_MODEL, input=valid_texts
            )

            batch_embeddings = [[0.0] * OPENAI_EMBEDDING_DIMENSION] * len(batch)
            for idx, emb_data in enumerate(response.data):
                batch_embeddings[valid_indices[idx]] = emb_data.embedding
            all_embeddings.extend(batch_embeddings)

        return all_embeddings


def build_school_text(school: dict) -> str:
    """
    构建学校的文本表示（用于生成嵌入）

    Args:
        school: 学校信息字典

    Returns:
        拼接后的文本
    """
    parts = [
        school.get("name", ""),
        f"位于{school.get('province', '')}{school.get('city', '')}",
        f"层次：{school.get('level', '')}",
        f"类型：{school.get('school_type', '')}",
    ]

    if school.get("is_985"):
        parts.append("985工程高校")
    if school.get("is_211"):
        parts.append("211工程高校")
    if school.get("is_double_first_class"):
        parts.append("双一流高校")

    if school.get("description"):
        parts.append(school["description"])

    return "，".join(filter(None, parts))


def build_major_text(major: dict) -> str:
    """
    构建专业的文本表示（用于生成嵌入）

    Args:
        major: 专业信息字典

    Returns:
        拼接后的文本
    """
    parts = [
        major.get("name", ""),
        f"学科门类：{major.get('category', '')}",
        f"二级类别：{major.get('sub_category', '')}",
    ]

    if major.get("description"):
        parts.append(major["description"])

    if major.get("job_directions"):
        parts.append(f"就业方向：{major['job_directions']}")

    return "，".join(filter(None, parts))
