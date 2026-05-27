#!/usr/bin/env python3
"""测试 OpenAI API 连接配置 - 多种方式尝试"""
import os
import asyncio
import sys
from pathlib import Path

# 加载 .env 文件
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                key, _, value = line.partition("=")
                os.environ[key.strip()] = value.strip()

API_KEY = os.getenv("OPENAI_API_KEY", "")
BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
MODEL = os.getenv("MODEL", "gpt-4o-mini")


async def test_with_url(url: str, label: str):
    """测试指定 URL 的 API 连接"""
    print(f"\n测试 {label}: {url}")
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(
            api_key=API_KEY,
            base_url=url,
            timeout=30.0,
        )

        response = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "user", "content": "Say 'OK' in one word."}
            ],
            max_tokens=10,
        )

        reply = response.choices[0].message.content
        print(f"  ✅ 成功! 响应: {reply}")
        return True

    except Exception as e:
        print(f"  ❌ 失败: {type(e).__name__}: {e}")
        return False


async def main():
    print(f"配置信息:")
    print(f"  API Key: {API_KEY[:20]}...{API_KEY[-4:]}" if len(API_KEY) > 24 else f"  API Key: {API_KEY}")
    print(f"  Base URL: {BASE_URL}")
    print(f"  Model: {MODEL}")

    if not API_KEY:
        print("❌ 错误: OPENAI_API_KEY 未配置")
        return False

    # 尝试多种 URL 格式
    urls_to_try = [
        (BASE_URL, "原始 URL"),
        ("https://v2.aicode.com/v1", "HTTPS + 点号替换"),
        ("https://v2.aicode.com", "HTTPS 无路径"),
        ("http://v2.aicode.com", "HTTP 无路径"),
    ]

    for url, label in urls_to_try:
        success = await test_with_url(url, label)
        if success:
            return True

    print("\n所有 URL 格式均失败")
    return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
