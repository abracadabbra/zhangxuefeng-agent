"""
Tool 集成测试 — 验证 Agent ↔ Tool ↔ 数据层完整链路

测试场景：
1. 5 个 Tool 定义正确性
2. Tool 注册与调度
3. 数据库查询集成
4. SSE 流式输出
5. 错误处理
"""
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport

from backend.tools.registry import tool_registry
from backend.tools.definitions import TOOLS


# ========== Tool 定义测试 ==========

class TestToolDefinitions:
    """Tool 定义正确性测试"""

    def test_all_tools_registered(self):
        """5 个工具应全部注册"""
        expected = {"search_admission", "search_employment", "compare_schools", "search_policy", "calculate_match"}
        actual = set(tool_registry.tool_names)
        assert expected == actual, f"缺少工具: {expected - actual}"

    def test_tool_definitions_format(self):
        """工具定义应符合 OpenAI function calling 格式"""
        assert len(TOOLS) == 5
        for tool in TOOLS:
            assert tool["type"] == "function"
            func = tool["function"]
            assert "name" in func
            assert "description" in func
            assert "parameters" in func
            assert func["parameters"]["type"] == "object"
            assert "properties" in func["parameters"]

    def test_search_admission_schema(self):
        """search_admission 参数 schema 验证"""
        tool = next(t for t in TOOLS if t["function"]["name"] == "search_admission")
        params = tool["function"]["parameters"]
        assert "school_name" in params["properties"]
        assert "school_name" in params["required"]
        assert "province" in params["properties"]
        assert "year" in params["properties"]
        assert "category" in params["properties"]

    def test_search_employment_schema(self):
        """search_employment 参数 schema 验证"""
        tool = next(t for t in TOOLS if t["function"]["name"] == "search_employment")
        params = tool["function"]["parameters"]
        assert "major_name" in params["properties"]
        assert "major_name" in params["required"]

    def test_compare_schools_schema(self):
        """compare_schools 参数 schema 验证"""
        tool = next(t for t in TOOLS if t["function"]["name"] == "compare_schools")
        params = tool["function"]["parameters"]
        assert "school_names" in params["properties"]
        assert "school_names" in params["required"]
        assert params["properties"]["school_names"]["type"] == "array"

    def test_calculate_match_schema(self):
        """calculate_match 参数 schema 验证"""
        tool = next(t for t in TOOLS if t["function"]["name"] == "calculate_match")
        params = tool["function"]["parameters"]
        assert "score" in params["required"]
        assert "province" in params["required"]
        assert "category" in params["required"]
        assert params["properties"]["strategy"]["enum"] == ["冲", "稳", "保"]


# ========== Tool 调度测试 ==========

class TestToolDispatch:
    """Tool 调度执行测试"""

    @pytest.mark.asyncio
    async def test_dispatch_unknown_tool(self):
        """调度未知工具应返回错误"""
        result = await tool_registry.dispatch("nonexistent_tool", {})
        assert "error" in result
        assert "Unknown tool" in result

    @pytest.mark.asyncio
    async def test_dispatch_search_admission_no_db(self):
        """search_admission 无数据库时应返回错误或空结果"""
        with patch("backend.tools.definitions._get_db") as mock_db:
            mock_session = MagicMock()
            mock_db.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = None

            result = await tool_registry.dispatch("search_admission", {"school_name": "不存在的学校"})
            data = json.loads(result)
            assert data["status"] == "not_found"

    @pytest.mark.asyncio
    async def test_dispatch_search_employment_no_db(self):
        """search_employment 无数据时应返回 not_found"""
        with patch("backend.tools.definitions._get_db") as mock_db:
            mock_session = MagicMock()
            mock_db.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = None

            result = await tool_registry.dispatch("search_employment", {"major_name": "不存在的专业"})
            data = json.loads(result)
            assert data["status"] == "not_found"

    @pytest.mark.asyncio
    async def test_dispatch_compare_schools_empty(self):
        """compare_schools 无匹配学校应返回 not_found"""
        with patch("backend.tools.definitions._get_db") as mock_db:
            mock_session = MagicMock()
            mock_db.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = None

            result = await tool_registry.dispatch("compare_schools", {"school_names": ["不存在的学校"]})
            data = json.loads(result)
            assert data["status"] == "not_found"

    @pytest.mark.asyncio
    async def test_dispatch_search_policy_stub(self):
        """search_policy 当前为 stub，应返回 not_implemented"""
        result = await tool_registry.dispatch("search_policy", {"keyword": "强基计划"})
        data = json.loads(result)
        assert data["status"] == "not_implemented"

    @pytest.mark.asyncio
    async def test_dispatch_calculate_match_no_data(self):
        """calculate_match 无数据时应返回空结果"""
        with patch("backend.tools.definitions._get_db") as mock_db:
            mock_session = MagicMock()
            mock_db.return_value = mock_session
            mock_session.query.return_value.filter.return_value.all.return_value = []

            result = await tool_registry.dispatch("calculate_match", {
                "score": 600, "province": "河南", "category": "理科"
            })
            data = json.loads(result)
            assert data["status"] == "success"
            assert data["total_matches"] == 0


# ========== 数据库集成测试 ==========

class TestDatabaseIntegration:
    """数据库查询集成测试（使用真实 SQLite）"""

    @pytest.fixture
    def db_session(self):
        """创建测试数据库会话"""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from backend.database import Base
        from backend.models.school import School
        from backend.models.major import Major
        from backend.models.admission_score import AdmissionScore

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()

        # 插入测试数据
        school = School(
            name="测试大学", province="北京", city="北京",
            level="985", school_type="综合", ranking=1,
            is_985=1, is_211=1, is_double_first_class=1,
            website="https://test.edu.cn", description="测试大学简介"
        )
        session.add(school)
        session.flush()

        major = Major(
            name="计算机科学与技术", category="工学", sub_category="计算机类",
            description="计算机专业", employment_rate=0.95, avg_salary=15000,
            job_directions="互联网、金融",
            is_hot=1
        )
        session.add(major)
        session.flush()

        score = AdmissionScore(
            school_id=school.id, province="河南", year=2025,
            batch="本科一批", subject_type="理科",
            min_score=694, avg_score=702, max_score=710, min_rank=58
        )
        session.add(score)
        session.commit()

        yield session
        session.close()

    @pytest.mark.asyncio
    async def test_search_admission_with_data(self, db_session):
        """search_admission 有数据时应返回正确结果"""
        with patch("backend.tools.definitions._get_db", return_value=db_session):
            result = await tool_registry.dispatch("search_admission", {"school_name": "测试大学"})
            data = json.loads(result)
            assert data["status"] == "success"
            assert data["school"]["name"] == "测试大学"
            assert len(data["scores"]) > 0

    @pytest.mark.asyncio
    async def test_search_employment_with_data(self, db_session):
        """search_employment 有数据时应返回正确结果"""
        with patch("backend.tools.definitions._get_db", return_value=db_session):
            result = await tool_registry.dispatch("search_employment", {"major_name": "计算机科学与技术"})
            data = json.loads(result)
            assert data["status"] == "success"
            assert data["major"]["name"] == "计算机科学与技术"
            assert data["employment"]["employment_rate"] == 0.95

    @pytest.mark.asyncio
    async def test_compare_schools_with_data(self, db_session):
        """compare_schools 有数据时应返回对比结果"""
        with patch("backend.tools.definitions._get_db", return_value=db_session):
            result = await tool_registry.dispatch("compare_schools", {"school_names": ["测试大学"]})
            data = json.loads(result)
            assert data["status"] == "success"
            assert data["comparison_count"] == 1
            assert data["schools"][0]["is_985"] == 1

    @pytest.mark.asyncio
    async def test_calculate_match_with_data(self, db_session):
        """calculate_match 有数据时应返回匹配院校"""
        with patch("backend.tools.definitions._get_db", return_value=db_session):
            result = await tool_registry.dispatch("calculate_match", {
                "score": 690, "province": "河南", "category": "理科", "strategy": "稳"
            })
            data = json.loads(result)
            assert data["status"] == "success"
            assert "matched_schools" in data


# ========== SSE 流式输出测试 ==========

try:
    import sse_starlette
    has_sse = True
except ImportError:
    has_sse = False


@pytest.mark.skipif(not has_sse, reason="sse_starlette not installed")
class TestSSEStreaming:
    """SSE 流式输出测试"""

    @pytest.fixture
    def client(self):
        from backend.main import app
        transport = ASGITransport(app=app)
        return AsyncClient(transport=transport, base_url="http://test")

    @pytest.mark.asyncio
    async def test_sse_endpoint_exists(self, client):
        """SSE 端点应存在并接受 stream=true"""
        with patch("backend.main.get_agent") as mock_get_agent:
            mock_agent = AsyncMock()
            mock_get_agent.return_value = mock_agent

            async def fake_stream(*args, **kwargs):
                yield {"type": "text", "content": "你好"}
                yield {"type": "done", "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}}

            mock_agent.chat_stream = fake_stream

            response = await client.post("/chat", json={
                "message": "你好",
                "stream": True
            })
            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_sse_events_format(self, client):
        """SSE 事件应包含正确的 data 字段"""
        with patch("backend.main.get_agent") as mock_get_agent:
            mock_agent = AsyncMock()
            mock_get_agent.return_value = mock_agent

            async def fake_stream(*args, **kwargs):
                yield {"type": "text", "content": "测试"}
                yield {"type": "done", "usage": None}

            mock_agent.chat_stream = fake_stream

            response = await client.post("/chat", json={
                "message": "测试",
                "stream": True
            })

            lines = response.text.strip().split("\n")
            data_lines = [l for l in lines if l.startswith("data: ")]
            assert len(data_lines) >= 2  # 至少 text + done

            # 验证 JSON 格式
            for line in data_lines:
                json_str = line[6:]  # 去掉 "data: " 前缀
                data = json.loads(json_str)
                assert "type" in data

    @pytest.mark.asyncio
    async def test_sse_tool_call_events(self, client):
        """SSE 应正确产出 tool_call 和 tool_result 事件"""
        with patch("backend.main.get_agent") as mock_get_agent:
            mock_agent = AsyncMock()
            mock_get_agent.return_value = mock_agent

            async def fake_stream(*args, **kwargs):
                yield {"type": "tool_call", "name": "search_admission", "arguments": {"school_name": "北京大学"}}
                yield {"type": "tool_result", "name": "search_admission", "result": '{"status": "success"}'}
                yield {"type": "text", "content": "北京大学的分数线是..."}
                yield {"type": "done", "usage": None}

            mock_agent.chat_stream = fake_stream

            response = await client.post("/chat", json={
                "message": "北京大学分数线",
                "stream": True
            })

            text = response.text
            assert "tool_call" in text
            assert "tool_result" in text
            assert "search_admission" in text


# ========== API 路由测试 ==========

@pytest.mark.skipif(not has_sse, reason="sse_starlette not installed")
class TestAPIRoutes:
    """API 路由测试"""

    @pytest.fixture
    def client(self):
        from backend.main import app
        transport = ASGITransport(app=app)
        return AsyncClient(transport=transport, base_url="http://test")

    @pytest.mark.asyncio
    async def test_health_endpoint(self, client):
        """健康检查端点"""
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_root_endpoint(self, client):
        """根端点应返回功能列表"""
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "function_calling" in data["features"]
        assert "sse_streaming" in data["features"]

    @pytest.mark.asyncio
    async def test_tools_endpoint(self, client):
        """工具列表端点"""
        response = await client.get("/tools")
        assert response.status_code == 200
        data = response.json()
        assert len(data["tools"]) == 5

    @pytest.mark.asyncio
    async def test_chat_empty_message(self, client):
        """空消息应返回 400"""
        response = await client.post("/chat", json={"message": ""})
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_session_crud(self, client):
        """会话 CRUD 操作"""
        # 创建会话
        with patch("backend.main.get_agent") as mock_get_agent:
            mock_agent = AsyncMock()
            mock_get_agent.return_value = mock_agent
            mock_agent.chat.return_value = {
                "reply": "你好",
                "tool_calls": [],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
            }

            response = await client.post("/chat", json={
                "message": "你好",
                "session_id": "test-session-crud",
                "user_context": {"分数": 600, "省份": "河南", "科类": "理科", "家庭条件": "工薪阶层"}
            })
            assert response.status_code == 200
            session_id = response.json()["session_id"]

        # 查询会话
        response = await client.get(f"/session/{session_id}")
        assert response.status_code == 200
        assert response.json()["session_id"] == session_id

        # 删除会话
        response = await client.delete(f"/session/{session_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"
