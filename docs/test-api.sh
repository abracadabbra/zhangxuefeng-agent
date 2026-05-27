#!/bin/bash

# 张雪峰 AI 咨询 Agent — API 测试脚本
# 使用方式：chmod +x test-api.sh && ./test-api.sh

BASE_URL="http://localhost:8000"
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "=========================================="
echo "张雪峰 AI 咨询 Agent — API 测试"
echo "=========================================="
echo ""

# 检查服务是否运行
echo "1. 检查服务状态..."
response=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/health")
if [ "$response" = "200" ]; then
    echo -e "${GREEN}✓ 服务运行正常${NC}"
else
    echo -e "${RED}✗ 服务未运行，请先启动服务${NC}"
    echo "  启动命令：cd backend && uvicorn main:app --reload"
    exit 1
fi

echo ""
echo "2. 健康检查..."
curl -s "$BASE_URL/health" | python3 -m json.tool

echo ""
echo "3. 数据库状态..."
curl -s "$BASE_URL/db/status" | python3 -m json.tool

echo ""
echo "=========================================="
echo "数据查询接口测试"
echo "=========================================="

echo ""
echo "4. 查询院校 - 按 ID..."
curl -s "$BASE_URL/schools/1" | python3 -m json.tool

echo ""
echo "5. 查询院校 - 按名称..."
curl -s "$BASE_URL/schools/by-name/北京大学" | python3 -m json.tool

echo ""
echo "6. 查询 985 院校..."
curl -s -X POST "$BASE_URL/schools/search" \
  -H "Content-Type: application/json" \
  -d '{"level": "985", "page": 1, "page_size": 5}' | python3 -m json.tool

echo ""
echo "7. 查询热门专业..."
curl -s "$BASE_URL/majors/hot/list?limit=5" | python3 -m json.tool

echo ""
echo "8. 查询分数线..."
curl -s -X POST "$BASE_URL/scores/search" \
  -H "Content-Type: application/json" \
  -d '{"province": "河南", "year": 2025, "page": 1, "page_size": 5}' | python3 -m json.tool

echo ""
echo "=========================================="
echo "对话接口测试"
echo "=========================================="

echo ""
echo "9. 非流式对话..."
curl -s -X POST "$BASE_URL/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "你好，我是河南考生，560分，理科，能上什么学校？",
    "user_context": {
      "分数": 560,
      "省份": "河南",
      "科类": "理科"
    }
  }' | python3 -m json.tool

echo ""
echo "10. SSE 流式对话（前 5 条事件）..."
echo "（按 Ctrl+C 停止）"
echo ""
curl -N -X POST "$BASE_URL/chat" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "message": "简单介绍一下计算机专业",
    "stream": true
  }' 2>/dev/null | head -20

echo ""
echo "=========================================="
echo "用户画像测试"
echo "=========================================="

SESSION_ID="test-session-$(date +%s)"

echo ""
echo "11. 创建会话并获取画像..."
curl -s "$BASE_URL/profile/$SESSION_ID" | python3 -m json.tool

echo ""
echo "12. 更新用户画像..."
curl -s -X PUT "$BASE_URL/profile/$SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{"field": "score", "value": "580"}' | python3 -m json.tool

echo ""
echo "13. 获取追问问题..."
curl -s "$BASE_URL/profile/$SESSION_ID/next-question" | python3 -m json.tool

echo ""
echo "=========================================="
echo "工具定义测试"
echo "=========================================="

echo ""
echo "14. 获取工具定义..."
curl -s "$BASE_URL/tools" | python3 -m json.tool

echo ""
echo "=========================================="
echo "测试完成！"
echo "=========================================="
echo ""
echo "更多测试请使用："
echo "  - VS Code REST Client: 打开 docs/api-tests.http"
echo "  - Swagger UI: http://localhost:8000/docs"
echo "  - ReDoc: http://localhost:8000/redoc"
