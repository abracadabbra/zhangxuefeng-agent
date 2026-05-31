"""
对话导出 PDF 模块 — 报纸风格排版，支持中文

使用 reportlab 生成 PDF，内置 CID 中文字体（STSong-Light）。
"""
import io
import logging
import re
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

logger = logging.getLogger(__name__)

# 注册中文 CID 字体（无需外部字体文件）
pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))

# ── 颜色方案 ──
_COLOR_PRIMARY = colors.HexColor("#1a1a2e")
_COLOR_ACCENT = colors.HexColor("#16213e")
_COLOR_USER_BG = colors.HexColor("#e8f4fd")
_COLOR_AI_BG = colors.HexColor("#f0f0f0")
_COLOR_HIGHLIGHT = colors.HexColor("#c0392b")
_COLOR_MUTED = colors.HexColor("#7f8c8d")
_COLOR_BORDER = colors.HexColor("#bdc3c7")

# ── 样式 ──
def _build_styles() -> dict[str, ParagraphStyle]:
    """构建所有段落样式"""
    base = {
        "fontName": "STSong-Light",
    }
    return {
        "masthead": ParagraphStyle(
            "masthead",
            **base,
            fontSize=28,
            leading=36,
            alignment=TA_CENTER,
            textColor=_COLOR_PRIMARY,
            spaceAfter=2 * mm,
        ),
        "subtitle": ParagraphStyle(
            "subtitle",
            **base,
            fontSize=11,
            leading=16,
            alignment=TA_CENTER,
            textColor=_COLOR_MUTED,
            spaceAfter=6 * mm,
        ),
        "section_title": ParagraphStyle(
            "section_title",
            **base,
            fontSize=16,
            leading=22,
            textColor=_COLOR_ACCENT,
            spaceBefore=8 * mm,
            spaceAfter=4 * mm,
            borderPadding=(0, 0, 2, 0),
        ),
        "body": ParagraphStyle(
            "body",
            **base,
            fontSize=10.5,
            leading=17,
            alignment=TA_JUSTIFY,
            spaceAfter=2 * mm,
        ),
        "user_label": ParagraphStyle(
            "user_label",
            **base,
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#2980b9"),
            spaceBefore=3 * mm,
            spaceAfter=1 * mm,
        ),
        "ai_label": ParagraphStyle(
            "ai_label",
            **base,
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#27ae60"),
            spaceBefore=3 * mm,
            spaceAfter=1 * mm,
        ),
        "msg_content": ParagraphStyle(
            "msg_content",
            **base,
            fontSize=10.5,
            leading=17,
            alignment=TA_LEFT,
            leftIndent=8 * mm,
            rightIndent=4 * mm,
            spaceAfter=2 * mm,
        ),
        "info_label": ParagraphStyle(
            "info_label",
            **base,
            fontSize=10,
            leading=15,
            textColor=_COLOR_MUTED,
        ),
        "info_value": ParagraphStyle(
            "info_value",
            **base,
            fontSize=10.5,
            leading=15,
            textColor=_COLOR_PRIMARY,
        ),
        "footer": ParagraphStyle(
            "footer",
            **base,
            fontSize=8,
            leading=11,
            alignment=TA_CENTER,
            textColor=_COLOR_MUTED,
        ),
        "tag": ParagraphStyle(
            "tag",
            **base,
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#8e44ad"),
        ),
    }


def _escape(text: str) -> str:
    """转义 XML 特殊字符，防止 reportlab 解析出错"""
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    return text


def _format_markdown_to_flowables(text: str, style: ParagraphStyle) -> list:
    """将简单的 Markdown 文本转为 reportlab Paragraph 列表"""
    lines = text.split("\n")
    result = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            result.append(Spacer(1, 3 * mm))
            continue

        # 处理标题 ### / ## / #
        heading_match = re.match(r"^(#{1,3})\s+(.+)$", stripped)
        if heading_match:
            level = len(heading_match.group(1))
            heading_text = _escape(heading_match.group(2))
            sz = {1: 14, 2: 12, 3: 11}.get(level, 11)
            result.append(Paragraph(
                f'<font size="{sz}"><b>{heading_text}</b></font>',
                ParagraphStyle(
                    f"heading{level}",
                    fontName="STSong-Light",
                    fontSize=sz,
                    leading=sz + 6,
                    spaceBefore=3 * mm,
                    spaceAfter=1 * mm,
                    textColor=_COLOR_ACCENT,
                ),
            ))
            continue

        # 处理加粗 **text**
        formatted = _escape(stripped)
        formatted = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", formatted)
        # 处理行内代码 `code`
        formatted = re.sub(
            r"`([^`]+)`",
            r'<font face="Courier" size="9" color="#c0392b">\1</font>',
            formatted,
        )
        # 处理列表项 - / *
        if re.match(r"^[-*]\s+", formatted):
            formatted = re.sub(r"^[-*]\s+", "  • ", formatted)

        result.append(Paragraph(formatted, style))
    return result


def _build_info_table(session_data: dict, styles: dict) -> Table:
    """构建会话信息表格"""
    fields = []
    ctx = session_data.get("user_context", {}) or {}

    label_map = {
        "score": ("高考分数", str(ctx.get("分数", "未填写"))),
        "province": ("所在省份", ctx.get("省份", "未填写")),
        "subject": ("科类", ctx.get("科类", "未填写")),
        "family_background": ("家庭条件", ctx.get("家庭条件", "未填写")),
        "target_city": ("目标城市", ctx.get("目标城市", "未填写")),
        "risk_tolerance": ("风险偏好", ctx.get("风险偏好", "未填写")),
        "career_goal": ("职业方向", ctx.get("职业方向", "未填写")),
    }

    for _key, (label, value) in label_map.items():
        fields.append([
            Paragraph(f"<b>{label}</b>", styles["info_label"]),
            Paragraph(str(value), styles["info_value"]),
        ])

    if not fields:
        fields.append([
            Paragraph("<b>用户画像</b>", styles["info_label"]),
            Paragraph("暂无画像信息", styles["info_value"]),
        ])

    table = Table(fields, colWidths=[35 * mm, 130 * mm])
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, _COLOR_BORDER),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#fafafa")),
        ("LEFTPADDING", (0, 0), (0, -1), 6),
    ]))
    return table


def _build_chat_messages(history: list[dict], styles: dict) -> list:
    """将对话历史转为 PDF 流式元素"""
    elements = []
    role_config = {
        "user": ("用户", styles["user_label"]),
        "assistant": ("张雪峰 AI", styles["ai_label"]),
    }

    for idx, msg in enumerate(history):
        role = msg.get("role", "")
        content = msg.get("content", "").strip()
        if not content or role not in role_config:
            continue

        label_text, label_style = role_config[role]
        # 序号 + 角色标签
        seq = idx // 2 + 1 if role == "user" else ""
        prefix = f"[{seq}] " if seq else ""
        elements.append(Paragraph(
            f'{prefix}<b>{label_text}</b> <font size="8" color="#95a5a6">#{idx + 1}</font>',
            label_style,
        ))

        # 消息内容 — 支持简单 Markdown
        msg_flowables = _format_markdown_to_flowables(content, styles["msg_content"])
        elements.extend(msg_flowables)

        # 分隔线
        elements.append(HRFlowable(
            width="85%",
            thickness=0.3,
            color=_COLOR_BORDER,
            spaceBefore=2 * mm,
            spaceAfter=2 * mm,
        ))

    return elements


def generate_chat_pdf(session_data: dict) -> bytes:
    """
    根据会话数据生成 PDF 字节流。

    Args:
        session_data: 包含 session_id, created_at, user_context, history 的字典

    Returns:
        PDF 文件的 bytes
    """
    styles = _build_styles()
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        title="张雪峰 AI 咨询记录",
        author="张雪峰 AI 咨询 Agent",
    )

    story = []

    # ── 报头 ──
    story.append(Paragraph("张雪峰 AI 咨询记录", styles["masthead"]))
    story.append(Paragraph(
        "高考 / 考研 / 职业规划 — 智能咨询报告",
        styles["subtitle"],
    ))

    # 顶部装饰线
    story.append(HRFlowable(
        width="100%", thickness=2, color=_COLOR_PRIMARY, spaceBefore=0, spaceAfter=4 * mm,
    ))
    story.append(HRFlowable(
        width="100%", thickness=0.5, color=_COLOR_ACCENT, spaceBefore=0, spaceAfter=6 * mm,
    ))

    # ── 会话基本信息 ──
    session_id = session_data.get("session_id", "unknown")
    created_at = session_data.get("created_at", "")
    msg_count = session_data.get("message_count", 0)

    story.append(Paragraph("会话信息", styles["section_title"]))
    info_rows = [
        [
            Paragraph("<b>会话 ID</b>", styles["info_label"]),
            Paragraph(_escape(str(session_id)), styles["info_value"]),
        ],
        [
            Paragraph("<b>创建时间</b>", styles["info_label"]),
            Paragraph(_escape(str(created_at)), styles["info_value"]),
        ],
        [
            Paragraph("<b>消息数</b>", styles["info_label"]),
            Paragraph(str(msg_count), styles["info_value"]),
        ],
    ]
    info_table = Table(info_rows, colWidths=[35 * mm, 130 * mm])
    info_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, _COLOR_BORDER),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#fafafa")),
        ("LEFTPADDING", (0, 0), (0, -1), 6),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 4 * mm))

    # ── 用户画像 ──
    story.append(Paragraph("用户画像", styles["section_title"]))
    story.append(_build_info_table(session_data, styles))
    story.append(Spacer(1, 4 * mm))

    # ── 对话记录 ──
    history = session_data.get("history", [])
    if history:
        story.append(Paragraph("对话记录", styles["section_title"]))
        story.append(HRFlowable(
            width="100%", thickness=1, color=_COLOR_ACCENT, spaceBefore=0, spaceAfter=4 * mm,
        ))
        story.extend(_build_chat_messages(history, styles))
    else:
        story.append(Paragraph(
            '<font color="#95a5a6">暂无对话记录</font>',
            styles["body"],
        ))

    # ── 页脚 ──
    story.append(Spacer(1, 10 * mm))
    story.append(HRFlowable(
        width="100%", thickness=1, color=_COLOR_PRIMARY, spaceBefore=0, spaceAfter=3 * mm,
    ))
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    story.append(Paragraph(
        f"本报告由张雪峰 AI 咨询 Agent 自动生成 | {now_str}",
        styles["footer"],
    ))
    story.append(Paragraph(
        "仅供参考，不构成任何招生或职业决策建议",
        styles["footer"],
    ))

    # 构建 PDF
    doc.build(story)
    return buffer.getvalue()
