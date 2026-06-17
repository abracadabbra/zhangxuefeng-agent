from backend.export import generate_chat_markdown, generate_chat_pdf


def _session_data():
    return {
        "session_id": "session-export-001",
        "created_at": "2026-06-06T10:00:00",
        "message_count": 2,
        "user_context": {
            "分数": 650,
            "省份": "河南",
            "科类": "理科",
            "家庭条件": "工薪阶层",
            "目标城市": "北京",
            "风险偏好": "稳健",
            "职业方向": "计算机",
            "省份批次": "本科一批",
            "选科限制": "物理+化学",
            "位次": 4200,
            "家庭预算": "每年 2 万以内",
            "地域偏好": "华北优先",
            "城市层级": "一线/新一线",
            "职业偏好权重": 8,
        },
        "recommendations": [
            {
                "school_name": "北京邮电大学",
                "admission_probability": 0.62,
                "reason": "计算机和通信学科强，符合职业方向。",
                "risk_points": ["热门专业分数波动大"],
                "alternatives": ["南京邮电大学"],
            }
        ],
        "gradient_summary": {
            "冲": ["清华大学"],
            "稳": ["北京邮电大学"],
            "保": ["南京邮电大学"],
        },
        "favorite_keys": ["school:北京邮电大学"],
        "summary": "建议按冲稳保分层填报，并保留至少两所保底院校。",
        "history": [
            {"role": "user", "content": "河南理科650分，想学计算机。"},
            {"role": "assistant", "content": "可以重点看北京邮电大学，同时准备稳妥替代。"},
        ],
    }


def test_generate_chat_markdown_includes_report_sections():
    markdown = generate_chat_markdown(_session_data())

    assert "# 张雪峰 AI 志愿建议报告" in markdown
    assert "## 用户画像" in markdown
    assert "**高考分数**: 650" in markdown
    assert "**位次**: 4200" in markdown
    assert "**家庭预算**: 每年 2 万以内" in markdown
    assert "**地域偏好**: 华北优先" in markdown
    assert "**城市层级**: 一线/新一线" in markdown
    assert "**职业偏好权重**: 8" in markdown
    assert "## 推荐梯度" in markdown
    assert "### 梯度概览" in markdown
    assert "- **冲**：清华大学" in markdown
    assert "- **稳**：北京邮电大学" in markdown
    assert "- **保**：南京邮电大学" in markdown
    assert "[稳] 北京邮电大学" in markdown
    assert "状态：已收藏" in markdown
    assert "为什么适合：计算机和通信学科强" in markdown
    assert "风险点：热门专业分数波动大" in markdown
    assert "替代方案：南京邮电大学" in markdown
    assert "## 对话记录" in markdown


def test_generate_chat_markdown_falls_back_to_latest_assistant_message():
    data = _session_data()
    data.pop("recommendations")
    data.pop("summary")

    markdown = generate_chat_markdown(data)

    assert "未保存结构化推荐列表" in markdown
    assert "可以重点看北京邮电大学" in markdown


def test_generate_chat_pdf_returns_pdf_bytes():
    pdf = generate_chat_pdf(_session_data())

    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000
