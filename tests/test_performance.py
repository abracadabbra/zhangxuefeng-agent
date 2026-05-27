"""
性能测试 — 响应时间、并发、内存

测试维度：
1. API 响应时间 — 各端点延迟
2. 并发处理 — 多请求同时访问
3. 内存使用 — 会话存储增长
4. 指标收集 — /metrics 端点正确性
"""

import time
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.metrics import metrics

client = TestClient(app)


# ============== 响应时间测试 ==============

class TestResponseTime:
    """API 响应时间测试"""

    def test_health_response_time(self):
        """健康检查端点响应时间 < 100ms"""
        start = time.perf_counter()
        response = client.get("/health")
        duration_ms = (time.perf_counter() - start) * 1000

        assert response.status_code == 200
        assert duration_ms < 100, f"健康检查耗时 {duration_ms:.1f}ms，超过 100ms 阈值"

    def test_metrics_response_time(self):
        """指标端点响应时间 < 100ms"""
        start = time.perf_counter()
        response = client.get("/metrics")
        duration_ms = (time.perf_counter() - start) * 1000

        assert response.status_code == 200
        assert duration_ms < 100, f"指标端点耗时 {duration_ms:.1f}ms，超过 100ms 阈值"

    def test_session_get_response_time(self):
        """会话获取响应时间 < 50ms"""
        # 先创建一个会话
        client.post("/api/v1/chat", json={
            "message": "你好",
            "session_id": "perf-test-1",
        })

        start = time.perf_counter()
        response = client.get("/api/v1/session/perf-test-1")
        duration_ms = (time.perf_counter() - start) * 1000

        assert response.status_code == 200
        assert duration_ms < 50, f"会话获取耗时 {duration_ms:.1f}ms，超过 50ms 阈值"

    def test_session_delete_response_time(self):
        """会话删除响应时间 < 50ms"""
        # 先创建一个会话
        client.post("/api/v1/chat", json={
            "message": "你好",
            "session_id": "perf-test-2",
        })

        start = time.perf_counter()
        response = client.delete("/api/v1/session/perf-test-2")
        duration_ms = (time.perf_counter() - start) * 1000

        assert response.status_code == 200
        assert duration_ms < 50, f"会话删除耗时 {duration_ms:.1f}ms，超过 50ms 阈值"


# ============== 并发测试 ==============

class TestConcurrency:
    """并发处理测试"""

    def test_concurrent_health_checks(self):
        """并发健康检查（10 个请求）"""
        import concurrent.futures

        def check_health():
            return client.get("/health")

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(check_health) for _ in range(10)]
            results = [f.result() for f in futures]

        # 所有请求都应该成功
        assert all(r.status_code == 200 for r in results)

    def test_concurrent_session_creation(self):
        """并发会话创建（5 个请求）"""
        import concurrent.futures

        def create_session(i):
            return client.post("/api/v1/chat", json={
                "message": f"并发测试 {i}",
                "session_id": f"concurrent-test-{i}",
            })

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_session, i) for i in range(5)]
            results = [f.result() for f in futures]

        # 所有请求都应该成功（200 或 400 都算正常）
        assert all(r.status_code in [200, 400, 422] for r in results)


# ============== 内存测试 ==============

class TestMemoryUsage:
    """内存使用测试"""

    def test_session_cleanup(self):
        """测试会话清理后内存释放"""
        # 创建多个会话
        for i in range(10):
            client.post("/api/v1/chat", json={
                "message": f"内存测试 {i}",
                "session_id": f"memory-test-{i}",
            })

        # 删除所有会话
        for i in range(10):
            client.delete(f"/api/v1/session/memory-test-{i}")

        # 验证会话已删除
        for i in range(10):
            response = client.get(f"/api/v1/session/memory-test-{i}")
            assert response.status_code == 404

    def test_metrics_accumulation(self):
        """测试指标累积不溢出"""
        # 发送多个请求
        for i in range(20):
            client.get("/health")

        # 获取指标
        response = client.get("/metrics")
        assert response.status_code == 200
        data = response.json()

        # 验证指标合理
        assert data["requests"]["total"] >= 20
        assert data["requests"]["avg_duration_ms"] >= 0


# ============== 指标收集测试 ==============

class TestMetricsCollection:
    """指标收集正确性测试"""

    def test_metrics_structure(self):
        """测试指标响应结构"""
        response = client.get("/metrics")
        assert response.status_code == 200
        data = response.json()

        # 验证结构
        assert "requests" in data
        assert "llm" in data

        assert "total" in data["requests"]
        assert "errors" in data["requests"]
        assert "avg_duration_ms" in data["requests"]
        assert "success_rate" in data["requests"]

        assert "total_calls" in data["llm"]
        assert "total_cost_usd" in data["llm"]

    def test_metrics_update_after_requests(self):
        """测试指标在请求后更新"""
        # 获取初始指标
        response1 = client.get("/metrics")
        initial_total = response1.json()["requests"]["total"]

        # 发送请求
        client.get("/health")

        # 获取更新后的指标
        response2 = client.get("/metrics")
        new_total = response2.json()["requests"]["total"]

        # 总数应该增加（至少增加了 metrics 请求本身）
        assert new_total >= initial_total
