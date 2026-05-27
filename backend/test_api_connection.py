#!/usr/bin/env python3
"""测试 OpenAI API 连接配置"""
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


async def test_connection():
    """测试 OpenAI API 连接"""
    print(f"配置信息:")
    print(f"  API Key: {API_KEY[:20]}...{API_KEY[-4:]}" if len(API_KEY) > 24 else f"  API Key: {API_KEY}")
    print(f"  Base URL: {BASE_URL}")
    print(f"  Model: {MODEL}")
    print()

    if not API_KEY:
        print("❌ 错误: OPENAI_API_KEY 未配置")
        return False

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(
            api_key=API_KEY,
            base_url=BASE_URL,
            timeout=30.0,
        )

        print("正在测试 API 连接...")
        response = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "user", "content": "Hello, say 'API connection successful' in one sentence."}
            ],
            max_tokens=50,
        )

        reply = response.choices[0].message.content
        print(f"✅ API 连接成功!")
        print(f"  模型响应: {reply}")
        print(f"  Token 用量: {response.usage.total_tokens if response.usage else 'N/A'}")
        return True

    except ImportError:
        print("❌ 错误: openai 库未安装，请运行 pip install openai")
        return False
    except Exception as e:
        print(f"❌ API 连接失败: {type(e).__name__}: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_connection())
    sys.exit(0 if success else 1)
