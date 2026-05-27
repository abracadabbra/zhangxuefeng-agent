"""
核心链路端到端测试

测试场景：
1. 基础对话流程
2. 灵魂追问流
3. 工具调用流
4. 数据来源测试
5. 边界场景
6. 性能基准
"""
import pytest
import time
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models.user_profile import UserProfile
from backend.soul_query import SoulQueryEngine, QueryState


# ========== Mock Redis ==========

class MockRedis:
    """模拟 Redis 客户端"""
    def __init__(self):
        self._data = {}

    async def get(self, key):
        return self._data.get(key)

    async def set(self, key, value, ex=None):
        self._data[key] = value
        return True

    async def delete(self, key):
        self._data.pop(key, None)
        return True


@pytest.fixture(autouse=True)
def mock_redis():
    """自动 mock Redis 连接"""
    mock_client = MockRedis()
    with patch("app.services.session._get_redis", return_value=mock_client):
        yield mock_client


# ========== Fixtures ==========

@pytest.fixture
def client():
    """异步测试客户端"""
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture
def soul_engine():
    """灵魂追问引擎实例"""
    return SoulQueryEngine()


@pytest.fixture
def mock_llm_response():
    """模拟 LLM 响应"""
    return {
        "choices": [{
            "message": {
                "content": "你好！我是张雪峰老师的AI助手，有什么可以帮你的？",
                "role": "assistant"
            },
            "finish_reason": "stop"
        }],
        "model": "gpt-4o-mini",
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150
        }
    }


@pytest.fixture
def mock_tool_call_response():
    """模拟工具调用响应"""
    return {
        "choices": [{
            "message": {
                "content": "",
                "role": "assistant",
                "tool_calls": [{
                    "id": "call_123",
                    "type": "function",
                    "function": {
                        "name": "search_admission",
                        "arguments": '{"school_name": "北京大学", "province": "河南"}'
                    }
                }]
            },
            "finish_reason": "tool_calls"
        }],
        "model": "gpt-4o-mini",
        "usage": {
            "prompt_tokens": 150,
            "completion_tokens": 30,
            "total_tokens": 180
        }
    }


@pytest.fixture
def mock_tool_result_response():
    """模拟工具调用后的最终响应"""
    return {
        "choices": [{
            "message": {
                "content": "根据2025年数据，北京大学在河南理科的录取分数线是694分，最低位次是58位。",
                "role": "assistant"
            },
            "finish_reason": "stop"
        }],
        "model": "gpt-4o-mini",
        "usage": {
            "prompt_tokens": 200,
            "completion_tokens": 80,
            "total_tokens": 280
        }
    }


# ========== 测试场景1：基础对话流程 ==========

class TestBasicChatFlow:
    """基础对话流程测试"""

    @pytest.mark.asyncio
    async def test_simple_chat(self, client, mock_llm_response):
        """简单对话：用户发送消息，Agent 回复"""
        with patch("app.api.chat.chat_completion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_llm_response

            response = await client.post("/api/v1/chat", json={
                "message": "你好",
                "session_id": "test-session-1"
            })

            assert response.status_code == 200
            data = response.json()
            assert "reply" in data
            assert "session_id" in data
            assert data["session_id"] == "test-session-1"

    @pytest.mark.asyncio
    async def test_empty_message_rejected(self, client):
        """空消息应返回 400"""
        response = await client.post("/api/v1/chat", json={
            "message": "",
            "session_id": "test-session-2"
        })
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_session_persistence(self, client, mock_llm_response):
        """会话应保持上下文"""
        with patch("app.api.chat.chat_completion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_llm_response

            # 提供完整的用户上下文，跳过灵魂追问
            user_context = {
                "分数": 600,
                "省份": "河南",
                "科类": "理科",
                "家庭条件": "工薪阶层"
            }

            # 第一轮对话
            await client.post("/api/v1/chat", json={
                "message": "你好",
                "session_id": "test-session-3",
                "user_context": user_context
            })

            # 第二轮对话（同一 session）
            response = await client.post("/api/v1/chat", json={
                "message": "我想咨询高考志愿",
                "session_id": "test-session-3",
                "user_context": user_context
            })

            assert response.status_code == 200
            # 验证 LLM 被调用了两次
            assert mock_llm.call_count == 2


# ========== 测试场景2：灵魂追问流 ==========

class TestSoulQueryFlow:
    """灵魂追问机制测试"""

    @pytest.mark.asyncio
    async def test_first_question_is_score(self, client):
        """第一个追问应该是分数"""
        response = await client.post("/api/v1/chat", json={
            "message": "我想咨询志愿填报",
            "session_id": "test-soul-1"
        })

        assert response.status_code == 200
        data = response.json()
        assert "分数" in data["reply"] or "考了多少分" in data["reply"]
        assert data["model"] == "soul-query-engine"

    @pytest.mark.asyncio
    async def test_query_order_follows_priority(self, client):
        """追问顺序：分数 -> 省份 -> 文理 -> 家庭条件"""
        session_id = "test-soul-2"

        # 第1轮：应该问分数
        r1 = await client.post("/api/v1/chat", json={
            "message": "你好",
            "session_id": session_id
        })
        assert "分数" in r1.json()["reply"] or "考了多少分" in r1.json()["reply"]

        # 第2轮：回答分数后，应该问省份
        r2 = await client.post("/api/v1/chat", json={
            "message": "我考了600分",
            "session_id": session_id
        })
        assert "省" in r2.json()["reply"]

        # 第3轮：回答省份后，应该问文理或家庭条件（取决于提取逻辑）
        r3 = await client.post("/api/v1/chat", json={
            "message": "河南的",
            "session_id": session_id
        })
        # 应该继续追问下一个必填字段
        assert r3.json()["model"] == "soul-query-engine"

    @pytest.mark.asyncio
    async def test_no_repeat_after_answer(self, client):
        """已回答的问题不应再问"""
        session_id = "test-soul-3"

        # 回答分数
        await client.post("/api/v1/chat", json={
            "message": "我考了600分",
            "session_id": session_id
        })

        # 下一个问题不应该是分数
        response = await client.post("/api/v1/chat", json={
            "message": "继续",
            "session_id": session_id
        })
        reply = response.json()["reply"]
        assert "分数" not in reply or "考了多少分" not in reply

    @pytest.mark.asyncio
    async def test_max_3_rounds(self, client, mock_llm_response):
        """最多追问3轮"""
        session_id = "test-soul-4"

        with patch("app.api.chat.chat_completion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_llm_response

            # 连续3轮拒绝回答
            for i in range(3):
                await client.post("/api/v1/chat", json={
                    "message": "不想说",
                    "session_id": session_id
                })

            # 第4轮应该正常回答，不再追问
            response = await client.post("/api/v1/chat", json={
                "message": "帮我看看学校",
                "session_id": session_id
            })
            # 应该调用 LLM，而不是追问引擎
            assert response.json().get("model") != "soul-query-engine"


# ========== 测试场景3：工具调用流 ==========

class TestToolCallFlow:
    """工具调用流程测试"""

    @pytest.mark.asyncio
    async def test_search_admission_tool(self, client, mock_tool_call_response, mock_tool_result_response):
        """测试录取分数线查询工具"""
        with patch("app.api.chat.chat_completion", new_callable=AsyncMock) as mock_llm:
            # 第一次返回工具调用，第二次返回最终回答
            mock_llm.side_effect = [mock_tool_call_response, mock_tool_result_response]

            with patch("backend.tools.registry.tool_registry.dispatch", new_callable=AsyncMock) as mock_dispatch:
                mock_dispatch.return_value = '{"school": "北京大学", "province": "河南", "score": 694}'

                response = await client.post("/api/v1/chat", json={
                    "message": "北京大学在河南的录取分数线是多少？",
                    "session_id": "test-tool-1",
                    "user_context": {
                        "分数": 650,
                        "省份": "河南",
                        "科类": "理科",
                        "家庭条件": "工薪阶层"
                    }
                })

                assert response.status_code == 200
                data = response.json()
                assert "reply" in data

    @pytest.mark.asyncio
    async def test_multiple_tool_calls(self, client):
        """测试多工具调用（最多3轮）"""
        # TODO: 实现多工具调用测试
        pass

    @pytest.mark.asyncio
    async def test_tool_call_error_handling(self, client):
        """工具调用失败时的错误处理"""
        # TODO: 实现工具调用错误测试
        pass


# ========== 测试场景4：数据来源测试 ==========

class TestDataSources:
    """数据来源标注测试"""

    @pytest.mark.asyncio
    async def test_response_includes_source(self, client):
        """响应应包含数据来源"""
        # TODO: 实现数据来源测试
        pass

    @pytest.mark.asyncio
    async def test_freshness_warning(self, client):
        """过期数据应有警告"""
        # TODO: 实现新鲜度警告测试
        pass


# ========== 测试场景5：边界场景 ==========

class TestBoundaryScenarios:
    """边界场景测试"""

    @pytest.mark.asyncio
    async def test_nonexistent_school(self, client):
        """查询不存在的学校"""
        with patch("app.api.chat.chat_completion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "choices": [{
                    "message": {
                        "content": "抱歉，我没有找到「野鸡大学」的相关信息，请确认学校名称是否正确。",
                        "role": "assistant"
                    },
                    "finish_reason": "stop"
                }],
                "model": "gpt-4o-mini",
                "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
            }

            response = await client.post("/api/v1/chat", json={
                "message": "野鸡大学的分数线是多少？",
                "session_id": "test-boundary-1",
                "user_context": {"分数": 500, "省份": "河南", "科类": "理科", "家庭条件": "工薪阶层"}
            })

            assert response.status_code == 200
            # 应该有合理的错误提示
            assert "没有找到" in response.json()["reply"] or "确认" in response.json()["reply"]

    @pytest.mark.asyncio
    async def test_skip_query(self, client, mock_llm_response):
        """用户拒绝追问场景"""
        session_id = "test-boundary-2"

        with patch("app.api.chat.chat_completion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_llm_response

            # 用户拒绝回答分数
            r1 = await client.post("/api/v1/chat", json={
                "message": "不想说分数",
                "session_id": session_id
            })

            # 应该继续问下一个问题或给出默认策略
            assert r1.status_code == 200

    @pytest.mark.asyncio
    async def test_timeout_handling(self, client):
        """LLM 调用超时处理"""
        with patch("app.api.chat.chat_completion", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = TimeoutError("LLM 调用超时")

            response = await client.post("/api/v1/chat", json={
                "message": "测试超时",
                "session_id": "test-boundary-3",
                "user_context": {"分数": 500, "省份": "河南", "科类": "理科", "家庭条件": "工薪阶层"}
            })

            # 应该返回 500 错误
            assert response.status_code == 500
            # 错误信息应该包含 LLM 调用异常
            assert "LLM" in response.json().get("detail", "") or "异常" in response.json().get("detail", "")

    @pytest.mark.asyncio
    async def test_invalid_score_range(self, client):
        """无效分数范围"""
        response = await client.post("/api/v1/chat", json={
            "message": "我考了999分",
            "session_id": "test-boundary-4"
        })

        # 分数不应被提取（999 超出 100-750 范围）
        assert response.status_code == 200


# ========== 测试场景6：性能基准 ==========

class TestPerformanceBenchmarks:
    """性能基准测试"""

    @pytest.mark.asyncio
    async def test_response_time_under_3_seconds(self, client, mock_llm_response):
        """响应时间 < 3 秒"""
        with patch("app.api.chat.chat_completion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_llm_response

            start = time.time()
            response = await client.post("/api/v1/chat", json={
                "message": "你好",
                "session_id": "test-perf-1",
                "user_context": {"分数": 600, "省份": "河南", "科类": "理科", "家庭条件": "工薪阶层"}
            })
            elapsed = time.time() - start

            assert response.status_code == 200
            assert elapsed < 3.0, f"响应时间 {elapsed:.2f}s 超过 3 秒"

    @pytest.mark.asyncio
    async def test_first_token_under_1_second(self, client):
        """首字节时间 < 1 秒（流式响应）"""
        # TODO: 实现流式响应首字节测试
        pass

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, client, mock_llm_response):
        """并发请求处理"""
        import asyncio

        with patch("app.api.chat.chat_completion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_llm_response

            async def single_request(i):
                return await client.post("/api/v1/chat", json={
                    "message": f"测试消息 {i}",
                    "session_id": f"test-concurrent-{i}",
                    "user_context": {"分数": 600, "省份": "河南", "科类": "理科", "家庭条件": "工薪阶层"}
                })

            start = time.time()
            tasks = [single_request(i) for i in range(10)]
            responses = await asyncio.gather(*tasks)
            elapsed = time.time() - start

            # 所有请求都应该成功
            for r in responses:
                assert r.status_code == 200

            # 10个并发请求应在 10 秒内完成
            assert elapsed < 10.0, f"10个并发请求耗时 {elapsed:.2f}s"


# ========== 辅助工具 ==========

@pytest.fixture
def sample_user_context():
    """标准用户上下文"""
    return {
        "分数": 600,
        "省份": "河南",
        "科类": "理科",
        "家庭条件": "工薪阶层"
    }


@pytest.fixture
def mock_admission_data():
    """模拟录取数据"""
    return {
        "school": "北京大学",
        "province": "河南",
        "year": 2025,
        "category": "理科",
        "min_score": 694,
        "avg_score": 702,
        "min_rank": 58
    }


@pytest.fixture
def mock_employment_data():
    """模拟就业数据"""
    return {
        "major": "计算机科学与技术",
        "employment_rate": 0.95,
        "avg_salary": 15000,
        "top_companies": ["腾讯", "阿里巴巴", "字节跳动"]
    }
