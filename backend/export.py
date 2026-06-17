"""
对话导出 PDF 模块 — 报纸风格排版，支持中文

使用 reportlab 生成 PDF，内置 CID 中文字体（STSong-Light）。
"""

import io
import logging
import re
from datetime import datetime
from typing import Any

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

_PROFILE_FIELDS = [
    ("高考分数", "分数"),
    ("所在省份", "省份"),
    ("科类", "科类"),
    ("家庭条件", "家庭条件"),
    ("目标城市", "目标城市"),
    ("风险偏好", "风险偏好"),
    ("职业方向", "职业方向"),
    ("省份批次", "省份批次"),
    ("选科限制", "选科限制"),
    ("位次", "位次"),
    ("家庭预算", "家庭预算"),
    ("地域偏好", "地域偏好"),
    ("城市层级", "城市层级"),
    ("职业偏好权重", "职业偏好权重"),
]


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


def _recommendation_name(item: dict[str, Any]) -> str:
    return str(
        item.get("school_name")
        or item.get("school")
        or item.get("major_name")
        or item.get("major")
        or item.get("name")
        or "未命名推荐"
    )


def _recommendation_key(item: dict[str, Any]) -> str:
    if item.get("school_name") or item.get("school"):
        return f"school:{_recommendation_name(item)}"
    if item.get("major_name") or item.get("major"):
        return f"major:{_recommendation_name(item)}"
    return f"recommendation:{_recommendation_name(item)}"


def _favorite_label(item: dict[str, Any], favorite_keys: set[str]) -> str:
    return " · 已收藏" if _recommendation_key(item) in favorite_keys else ""


def _gradient_label(item: dict[str, Any]) -> str:
    explicit = item.get("strategy") or item.get("gradient")
    if explicit:
        return str(explicit)

    probability = item.get("admission_probability")
    if isinstance(probability, int | float):
        if probability >= 0.8:
            return "保"
        if probability >= 0.55:
            return "稳"
        return "冲"
    return "待判断"


def _gradient_summary_rows(session_data: dict[str, Any]) -> list[tuple[str, str]]:
    summary = session_data.get("gradient_summary") or {}
    if not isinstance(summary, dict):
        return []

    rows: list[tuple[str, str]] = []
    for strategy in ("冲", "稳", "保"):
        raw_names = summary.get(strategy)
        if isinstance(raw_names, list):
            names = [str(name) for name in raw_names if name]
        elif raw_names:
            names = [str(raw_names)]
        else:
            names = []
        if names:
            rows.append((strategy, "、".join(names)))
    return rows


def _recommendation_detail(item: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = item.get(key)
        if isinstance(value, list):
            return "；".join(str(part) for part in value if part)
        if value:
            return str(value)
    return "未提供"


def _latest_assistant_content(history: list[dict[str, Any]]) -> str:
    for msg in reversed(history):
        if msg.get("role") == "assistant":
            content = str(msg.get("content", "")).strip()
            if content:
                return content
    return ""


def _build_recommendation_markdown(session_data: dict[str, Any]) -> list[str]:
    recommendations = session_data.get("recommendations") or []
    favorite_keys = {
        str(item) for item in session_data.get("favorite_keys", []) if isinstance(item, str)
    }
    history = session_data.get("history", []) or []
    latest_assistant = _latest_assistant_content(history)
    gradient_rows = _gradient_summary_rows(session_data)

    lines = ["## 推荐梯度", ""]
    if gradient_rows:
        lines.extend(["### 梯度概览", ""])
        for strategy, names in gradient_rows:
            lines.append(f"- **{strategy}**：{names}")
        lines.append("")

    if recommendations:
        for idx, item in enumerate(recommendations, start=1):
            if not isinstance(item, dict):
                continue
            favorite_status = "已收藏" if _recommendation_key(item) in favorite_keys else "未收藏"
            lines.extend(
                [
                    f"### {idx}. [{_gradient_label(item)}] {_recommendation_name(item)}",
                    "",
                    f"- 状态：{favorite_status}",
                    f"- 为什么适合：{_recommendation_detail(item, 'reason', 'why_fit')}",
                    f"- 风险点：{_recommendation_detail(item, 'risk', 'risks', 'risk_points')}",
                    f"- 替代方案：{_recommendation_detail(item, 'alternative', 'alternatives')}",
                    "",
                ]
            )
    else:
        lines.extend(
            [
                "- 本次会话未保存结构化推荐列表，请参考下方“理由与风险提示”和“对话记录”。",
                "",
            ]
        )

    lines.extend(["## 理由与风险提示", ""])
    summary = str(session_data.get("summary") or "").strip()
    if summary:
        lines.append(summary)
    elif latest_assistant:
        lines.append(latest_assistant)
    else:
        lines.append("暂无推荐解释内容。")
    lines.append("")
    return lines


def generate_chat_markdown(session_data: dict[str, Any]) -> str:
    """Generate a Markdown volunteer-advice report from session data."""
    session_id = str(session_data.get("session_id", "unknown"))
    created_at = str(session_data.get("created_at", ""))
    ctx = session_data.get("user_context", {}) or {}
    history = session_data.get("history", []) or []

    lines = [
        "# 张雪峰 AI 志愿建议报告",
        "",
        f"**会话 ID**: `{session_id}`",
        f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**会话创建时间**: {created_at}",
        "",
        "## 用户画像",
        "",
    ]

    for label, key in _PROFILE_FIELDS:
        lines.append(f"- **{label}**: {ctx.get(key, '未填写')}")

    lines.extend(["", *_build_recommendation_markdown(session_data), "## 对话记录", ""])

    role_map = {"user": "用户", "assistant": "张雪峰 AI"}
    for msg in history:
        role = role_map.get(str(msg.get("role", "")), str(msg.get("role", "")))
        content = str(msg.get("content", "")).strip()
        if content:
            lines.append(f"### {role}")
            lines.append("")
            lines.append(content)
            lines.append("")

    lines.extend(
        [
            "---",
            "",
            "仅供参考，不构成任何招生或职业决策承诺；请以各省教育考试院和高校官方信息为准。",
            "",
        ]
    )
    return "\n".join(lines)


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
            result.append(
                Paragraph(
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
                )
            )
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

    for label, key in _PROFILE_FIELDS:
        value = ctx.get(key, "未填写")
        fields.append(
            [
                Paragraph(f"<b>{label}</b>", styles["info_label"]),
                Paragraph(str(value), styles["info_value"]),
            ]
        )

    if not fields:
        fields.append(
            [
                Paragraph("<b>用户画像</b>", styles["info_label"]),
                Paragraph("暂无画像信息", styles["info_value"]),
            ]
        )

    table = Table(fields, colWidths=[35 * mm, 130 * mm])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LINEBELOW", (0, 0), (-1, -2), 0.5, _COLOR_BORDER),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#fafafa")),
                ("LEFTPADDING", (0, 0), (0, -1), 6),
            ]
        )
    )
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
        elements.append(
            Paragraph(
                f'{prefix}<b>{label_text}</b> <font size="8" color="#95a5a6">#{idx + 1}</font>',
                label_style,
            )
        )

        # 消息内容 — 支持简单 Markdown
        msg_flowables = _format_markdown_to_flowables(content, styles["msg_content"])
        elements.extend(msg_flowables)

        # 分隔线
        elements.append(
            HRFlowable(
                width="85%",
                thickness=0.3,
                color=_COLOR_BORDER,
                spaceBefore=2 * mm,
                spaceAfter=2 * mm,
            )
        )

    return elements


def _build_recommendation_flowables(session_data: dict[str, Any], styles: dict) -> list:
    """Build volunteer recommendation summary flowables for the PDF report."""
    elements = []
    recommendations = session_data.get("recommendations") or []
    favorite_keys = {
        str(item) for item in session_data.get("favorite_keys", []) if isinstance(item, str)
    }
    history = session_data.get("history", []) or []
    latest_assistant = _latest_assistant_content(history)
    gradient_rows = _gradient_summary_rows(session_data)

    elements.append(Paragraph("推荐梯度与风险提示", styles["section_title"]))
    if gradient_rows:
        overview = "<br/>".join(
            f"<b>{_escape(strategy)}</b>：{_escape(names)}" for strategy, names in gradient_rows
        )
        elements.append(Paragraph(f"梯度概览<br/>{overview}", styles["body"]))

    if recommendations:
        for item in recommendations:
            if not isinstance(item, dict):
                continue
            title = (
                f"[{_gradient_label(item)}] {_escape(_recommendation_name(item))}"
                f"{_favorite_label(item, favorite_keys)}"
            )
            elements.append(Paragraph(f"<b>{title}</b>", styles["body"]))
            detail = (
                f"状态：{'已收藏' if _recommendation_key(item) in favorite_keys else '未收藏'}<br/>"
                f"为什么适合：{_recommendation_detail(item, 'reason', 'why_fit')}<br/>"
                f"风险点：{_recommendation_detail(item, 'risk', 'risks', 'risk_points')}<br/>"
                f"替代方案：{_recommendation_detail(item, 'alternative', 'alternatives')}"
            )
            elements.append(
                Paragraph(
                    _escape(detail).replace("&lt;br/&gt;", "<br/>"),
                    styles["body"],
                )
            )
    elif latest_assistant:
        elements.extend(_format_markdown_to_flowables(latest_assistant, styles["body"]))
    else:
        elements.append(Paragraph("暂无推荐解释内容。", styles["body"]))

    elements.append(Spacer(1, 4 * mm))
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
    story.append(
        Paragraph(
            "高考 / 考研 / 职业规划 — 智能咨询报告",
            styles["subtitle"],
        )
    )

    # 顶部装饰线
    story.append(
        HRFlowable(
            width="100%",
            thickness=2,
            color=_COLOR_PRIMARY,
            spaceBefore=0,
            spaceAfter=4 * mm,
        )
    )
    story.append(
        HRFlowable(
            width="100%",
            thickness=0.5,
            color=_COLOR_ACCENT,
            spaceBefore=0,
            spaceAfter=6 * mm,
        )
    )

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
    info_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LINEBELOW", (0, 0), (-1, -2), 0.5, _COLOR_BORDER),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#fafafa")),
                ("LEFTPADDING", (0, 0), (0, -1), 6),
            ]
        )
    )
    story.append(info_table)
    story.append(Spacer(1, 4 * mm))

    # ── 用户画像 ──
    story.append(Paragraph("用户画像", styles["section_title"]))
    story.append(_build_info_table(session_data, styles))
    story.append(Spacer(1, 4 * mm))

    # ── 推荐摘要 ──
    story.extend(_build_recommendation_flowables(session_data, styles))

    # ── 对话记录 ──
    history = session_data.get("history", [])
    if history:
        story.append(Paragraph("对话记录", styles["section_title"]))
        story.append(
            HRFlowable(
                width="100%",
                thickness=1,
                color=_COLOR_ACCENT,
                spaceBefore=0,
                spaceAfter=4 * mm,
            )
        )
        story.extend(_build_chat_messages(history, styles))
    else:
        story.append(
            Paragraph(
                '<font color="#95a5a6">暂无对话记录</font>',
                styles["body"],
            )
        )

    # ── 页脚 ──
    story.append(Spacer(1, 10 * mm))
    story.append(
        HRFlowable(
            width="100%",
            thickness=1,
            color=_COLOR_PRIMARY,
            spaceBefore=0,
            spaceAfter=3 * mm,
        )
    )
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    story.append(
        Paragraph(
            f"本报告由张雪峰 AI 咨询 Agent 自动生成 | {now_str}",
            styles["footer"],
        )
    )
    story.append(
        Paragraph(
            "仅供参考，不构成任何招生或职业决策建议",
            styles["footer"],
        )
    )

    # 构建 PDF
    doc.build(story)
    return buffer.getvalue()
