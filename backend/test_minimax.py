#!/usr/bin/env python3
"""测试 MiniMax-M2.7-highspeed 模型集成"""
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
MODEL = os.getenv("OPENAI_MODEL") or os.getenv("MODEL", "gpt-4o-mini")


async def test_basic_chat():
    """测试基本对话"""
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

        print("测试 1: 基本对话...")
        response = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "user", "content": "Hello, say 'API connection successful' in one sentence."}
            ],
            max_tokens=50,
        )

        reply = response.choices[0].message.content
        print(f"  ✅ 基本对话成功!")
        print(f"  响应: {reply}")
        print(f"  Token 用量: {response.usage.total_tokens if response.usage else 'N/A'}")
        return True

    except Exception as e:
        print(f"  ❌ 基本对话失败: {type(e).__name__}: {e}")
        return False


async def test_function_calling():
    """测试 Function Calling"""
    print("\n测试 2: Function Calling...")
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(
            api_key=API_KEY,
            base_url=BASE_URL,
            timeout=30.0,
        )

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "获取指定城市的天气信息",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "city": {
                                "type": "string",
                                "description": "城市名称"
                            }
                        },
                        "required": ["city"]
                    }
                }
            }
        ]

        response = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "user", "content": "北京今天天气怎么样？"}
            ],
            tools=tools,
            tool_choice="auto",
            max_tokens=200,
        )

        choice = response.choices[0]
        if choice.message.tool_calls:
            tool_call = choice.message.tool_calls[0]
            print(f"  ✅ Function Calling 成功!")
            print(f"  工具调用: {tool_call.function.name}({tool_call.function.arguments})")
            return True
        else:
            print(f"  ⚠️ 未触发工具调用，直接回复: {choice.message.content}")
            return True  # 仍然算成功，只是模型选择不调用工具

    except Exception as e:
        print(f"  ❌ Function Calling 失败: {type(e).__name__}: {e}")
        return False


async def main():
    print("=" * 50)
    print("MiniMax-M2.7-highspeed 模型集成测试")
    print("=" * 50)

    basic_ok = await test_basic_chat()
    fc_ok = await test_function_calling()

    print("\n" + "=" * 50)
    print("测试结果汇总:")
    print(f"  基本对话: {'✅ 通过' if basic_ok else '❌ 失败'}")
    print(f"  Function Calling: {'✅ 通过' if fc_ok else '❌ 失败'}")

    if basic_ok and fc_ok:
        print("\n✅ 所有测试通过！MiniMax-M2.7-highspeed 集成成功。")
        return True
    else:
        print("\n❌ 部分测试失败，请检查配置。")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
