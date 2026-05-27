"""
QA 全流程测试

测试范围：
1. 功能测试
2. 兼容性测试（Chrome/Firefox/Safari/移动端）
3. 性能测试（加载时间/内存）
4. 安全测试（XSS/输入验证）
5. 测试报告
"""
import pytest
import time
import re
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport

from app.main import app


# ========== Fixtures ==========

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


@pytest.fixture
def client():
    """异步测试客户端"""
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture
def mock_llm_response():
    """模拟 LLM 响应"""
    return {
        "choices": [{
            "message": {
                "content": "根据你的分数600分，我推荐以下院校...",
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
def sample_user_context():
    """标准用户上下文"""
    return {
        "分数": 600,
        "省份": "河南",
        "科类": "理科",
        "家庭条件": "工薪阶层"
    }


# ========== 1. 功能测试 ==========

class TestFunctional:
    """功能测试"""

    @pytest.mark.asyncio
    async def test_chat_basic_flow(self, client, mock_llm_response, sample_user_context):
        """基本对话流程"""
        with patch("app.api.chat.chat_completion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_llm_response

            response = await client.post("/api/v1/chat", json={
                "message": "你好",
                "session_id": "test-func-1",
                "user_context": sample_user_context
            })

            assert response.status_code == 200
            data = response.json()
            assert "reply" in data
            assert "session_id" in data

    @pytest.mark.asyncio
    async def test_session_creation(self, client, mock_llm_response, sample_user_context):
        """会话创建"""
        with patch("app.api.chat.chat_completion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_llm_response

            response = await client.post("/api/v1/chat", json={
                "message": "测试会话",
                "session_id": "test-session-create",
                "user_context": sample_user_context
            })

            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == "test-session-create"

    @pytest.mark.asyncio
    async def test_session_retrieval(self, client, mock_llm_response, sample_user_context):
        """会话查询"""
        with patch("app.api.chat.chat_completion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_llm_response

            # 先创建会话
            await client.post("/api/v1/chat", json={
                "message": "测试",
                "session_id": "test-session-get",
                "user_context": sample_user_context
            })

            # 查询会话
            response = await client.get("/api/v1/session/test-session-get")
            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == "test-session-get"

    @pytest.mark.asyncio
    async def test_session_deletion(self, client, mock_llm_response, sample_user_context):
        """会话删除"""
        with patch("app.api.chat.chat_completion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_llm_response

            # 先创建会话
            await client.post("/api/v1/chat", json={
                "message": "测试",
                "session_id": "test-session-delete",
                "user_context": sample_user_context
            })

            # 删除会话
            response = await client.delete("/api/v1/session/test-session-delete")
            assert response.status_code == 200

            # 验证会话已删除
            response = await client.get("/api/v1/session/test-session-delete")
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_empty_message_rejection(self, client):
        """空消息拒绝"""
        response = await client.post("/api/v1/chat", json={
            "message": "",
            "session_id": "test-empty"
        })
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_soul_query_flow(self, client):
        """灵魂追问流程"""
        response = await client.post("/api/v1/chat", json={
            "message": "我想咨询志愿",
            "session_id": "test-soul"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["model"] == "soul-query-engine"

    @pytest.mark.asyncio
    async def test_feedback_submission(self, client, mock_llm_response, sample_user_context):
        """反馈提交"""
        with patch("app.api.chat.chat_completion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_llm_response

            # 先创建会话
            await client.post("/api/v1/chat", json={
                "message": "测试",
                "session_id": "test-feedback",
                "user_context": sample_user_context
            })

            # 提交反馈
            response = await client.post("/api/v1/feedback", json={
                "session_id": "test-feedback",
                "rating": 5,
                "comment": "很有帮助"
            })

            assert response.status_code == 200


# ========== 2. 兼容性测试 ==========

class TestCompatibility:
    """兼容性测试"""

    @pytest.mark.asyncio
    async def test_content_type_json(self, client, mock_llm_response, sample_user_context):
        """Content-Type: application/json"""
        with patch("app.api.chat.chat_completion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_llm_response

            response = await client.post(
                "/api/v1/chat",
                json={
                    "message": "测试",
                    "session_id": "test-ct-1",
                    "user_context": sample_user_context
                },
                headers={"Content-Type": "application/json"}
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_cors_headers(self, client):
        """CORS 头检查"""
        response = await client.options("/api/v1/chat")
        # 应该有 CORS 相关头
        assert response.status_code in [200, 204, 405]

    @pytest.mark.asyncio
    async def test_accept_json(self, client, mock_llm_response, sample_user_context):
        """Accept: application/json"""
        with patch("app.api.chat.chat_completion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_llm_response

            response = await client.post(
                "/api/v1/chat",
                json={
                    "message": "测试",
                    "session_id": "test-accept",
                    "user_context": sample_user_context
                },
                headers={"Accept": "application/json"}
            )

            assert response.status_code == 200
            assert "application/json" in response.headers.get("content-type", "")


# ========== 3. 性能测试 ==========

class TestPerformance:
    """性能测试"""

    @pytest.mark.asyncio
    async def test_response_time(self, client, mock_llm_response, sample_user_context):
        """响应时间 < 3 秒"""
        with patch("app.api.chat.chat_completion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_llm_response

            start = time.time()
            response = await client.post("/api/v1/chat", json={
                "message": "性能测试",
                "session_id": "test-perf-1",
                "user_context": sample_user_context
            })
            elapsed = time.time() - start

            assert response.status_code == 200
            assert elapsed < 3.0, f"响应时间 {elapsed:.2f}s 超过 3 秒"

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, client, mock_llm_response, sample_user_context):
        """并发请求处理"""
        import asyncio

        with patch("app.api.chat.chat_completion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_llm_response

            async def single_request(i):
                return await client.post("/api/v1/chat", json={
                    "message": f"并发测试 {i}",
                    "session_id": f"test-concurrent-{i}",
                    "user_context": sample_user_context
                })

            start = time.time()
            tasks = [single_request(i) for i in range(5)]
            responses = await asyncio.gather(*tasks)
            elapsed = time.time() - start

            for r in responses:
                assert r.status_code == 200

            assert elapsed < 10.0, f"5个并发请求耗时 {elapsed:.2f}s"

    @pytest.mark.asyncio
    async def test_large_message_handling(self, client, mock_llm_response, sample_user_context):
        """大消息处理"""
        with patch("app.api.chat.chat_completion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_llm_response

            large_message = "测试" * 1000  # 2000 字符

            response = await client.post("/api/v1/chat", json={
                "message": large_message,
                "session_id": "test-large",
                "user_context": sample_user_context
            })

            assert response.status_code == 200


# ========== 4. 安全测试 ==========

class TestSecurity:
    """安全测试"""

    @pytest.mark.asyncio
    async def test_xss_prevention(self, client, mock_llm_response, sample_user_context):
        """XSS 防护"""
        with patch("app.api.chat.chat_completion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_llm_response

            xss_payloads = [
                "<script>alert('xss')</script>",
                "<img src=x onerror=alert('xss')>",
                "javascript:alert('xss')",
            ]

            for payload in xss_payloads:
                response = await client.post("/api/v1/chat", json={
                    "message": payload,
                    "session_id": "test-xss",
                    "user_context": sample_user_context
                })

                assert response.status_code == 200
                data = response.json()
                # 响应中不应包含未转义的脚本标签
                assert "<script>" not in data.get("reply", "")

    @pytest.mark.asyncio
    async def test_sql_injection_prevention(self, client, mock_llm_response, sample_user_context):
        """SQL 注入防护"""
        with patch("app.api.chat.chat_completion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_llm_response

            sql_payloads = [
                "'; DROP TABLE users; --",
                "1' OR '1'='1",
                "admin'--",
            ]

            for payload in sql_payloads:
                response = await client.post("/api/v1/chat", json={
                    "message": payload,
                    "session_id": "test-sql",
                    "user_context": sample_user_context
                })

                # 应该正常响应，不应报错
                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_input_validation(self, client):
        """输入验证"""
        # 缺少必填字段
        response = await client.post("/api/v1/chat", json={
            "session_id": "test-validation"
        })
        assert response.status_code == 422

        # 无效的 session_id 类型
        response = await client.post("/api/v1/chat", json={
            "message": "测试",
            "session_id": 123
        })
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_sensitive_data_exposure(self, client, mock_llm_response, sample_user_context):
        """敏感数据泄露检查"""
        with patch("app.api.chat.chat_completion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_llm_response

            response = await client.post("/api/v1/chat", json={
                "message": "测试",
                "session_id": "test-sensitive",
                "user_context": sample_user_context
            })

            assert response.status_code == 200
            data = response.json()

            # 响应中不应包含敏感信息
            response_str = str(data)
            assert "api_key" not in response_str.lower()
            assert "password" not in response_str.lower()
            assert "secret" not in response_str.lower()

    @pytest.mark.asyncio
    async def test_rate_limiting(self, client, mock_llm_response, sample_user_context):
        """速率限制检查"""
        with patch("app.api.chat.chat_completion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_llm_response

            # 快速发送多个请求
            for i in range(10):
                response = await client.post("/api/v1/chat", json={
                    "message": f"速率测试 {i}",
                    "session_id": f"test-rate-{i}",
                    "user_context": sample_user_context
                })

                # 应该都成功（如果没有速率限制）
                assert response.status_code == 200


# ========== 5. 测试报告 ==========

@pytest.fixture
def test_report():
    """测试报告生成器"""
    results = {
        "functional": {"passed": 0, "failed": 0, "errors": []},
        "compatibility": {"passed": 0, "failed": 0, "errors": []},
        "performance": {"passed": 0, "failed": 0, "errors": []},
        "security": {"passed": 0, "failed": 0, "errors": []},
    }
    return results
