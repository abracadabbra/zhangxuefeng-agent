"""
反馈服务单元测试
"""
import pytest
from app.services.feedback import classify_feedback, FeedbackItem


# ========== 问题分类测试 ==========

class TestClassifyFeedback:
    """测试反馈自动分类"""

    def test_classify_volunteer(self):
        assert classify_feedback("志愿填报有问题") == "志愿填报"
        assert classify_feedback("平行志愿怎么填") == "志愿填报"

    def test_classify_university(self):
        assert classify_feedback("985学校推荐") == "院校选择"
        assert classify_feedback("双一流大学") == "院校选择"

    def test_classify_major(self):
        assert classify_feedback("专业就业前景") == "专业选择"
        assert classify_feedback("选什么专业好") == "专业选择"

    def test_classify_score(self):
        assert classify_feedback("分数线多少") == "分数分析"
        assert classify_feedback("位次怎么算") == "分数分析"

    def test_classify_city(self):
        assert classify_feedback("城市选择很重要") == "地域选择"
        assert classify_feedback("不同地区差别大") == "地域选择"

    def test_classify_family(self):
        assert classify_feedback("家庭条件一般") == "家庭规划"
        assert classify_feedback("预算有限") == "家庭规划"

    def test_classify_other(self):
        assert classify_feedback("谢谢") == "其他"
        assert classify_feedback("") == "其他"
        assert classify_feedback(None) == "其他"


# ========== 反馈模型测试 ==========

class TestFeedbackItem:
    """测试反馈数据模型"""

    def test_create_feedback(self):
        fb = FeedbackItem(
            feedback_id="test-123",
            session_id="session-456",
            message_index=0,
            rating=5,
            comment="很好",
        )
        assert fb.feedback_id == "test-123"
        assert fb.rating == 5
        assert fb.comment == "很好"

    def test_feedback_without_comment(self):
        fb = FeedbackItem(
            feedback_id="test-123",
            session_id="session-456",
            message_index=0,
            rating=4,
        )
        assert fb.comment is None

    def test_feedback_category_auto(self):
        fb = FeedbackItem(
            feedback_id="test-123",
            session_id="session-456",
            message_index=0,
            rating=3,
        )
        # 分类在 save_feedback 时自动设置
        assert fb.category is None
