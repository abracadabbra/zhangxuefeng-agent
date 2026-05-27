"""
可信度评分机制

按来源分类 + 时效性衰减，实现可信度评分和新鲜度标记
"""
from datetime import datetime, timedelta
from urllib.parse import urlparse

from .models import SearchResult, SourceType, FreshnessLevel


# 来源类型权重映射
SOURCE_TYPE_WEIGHTS: dict[SourceType, float] = {
    SourceType.GOVERNMENT: 1.0,      # 官方/政府网站：最高可信度
    SourceType.UNIVERSITY: 0.95,     # 高校官网：高可信度
    SourceType.EDUCATION: 0.85,      # 教育类网站：较高可信度
    SourceType.MEDIA: 0.8,          # 主流媒体：中高可信度
    SourceType.FORUM: 0.4,          # 论坛/社区：低可信度
    SourceType.OTHER: 0.5,          # 其他：默认可信度
}

# 域名 → 来源类型映射
DOMAIN_SOURCE_MAP: dict[str, SourceType] = {
    # 政府网站
    "moe.gov.cn": SourceType.GOVERNMENT,      # 教育部
    "zs.moe.gov.cn": SourceType.GOVERNMENT,    # 教育部阳光高考
    "chsi.com.cn": SourceType.GOVERNMENT,      # 学信网
    "gaokao.chsi.com.cn": SourceType.GOVERNMENT,

    # 高校官网
    "pku.edu.cn": SourceType.UNIVERSITY,       # 北京大学
    "tsinghua.edu.cn": SourceType.UNIVERSITY,   # 清华大学
    "fudan.edu.cn": SourceType.UNIVERSITY,      # 复旦大学
    "zju.edu.cn": SourceType.UNIVERSITY,        # 浙江大学
    "sjtu.edu.cn": SourceType.UNIVERSITY,       # 上海交大
    "nju.edu.cn": SourceType.UNIVERSITY,        # 南京大学
    "ustc.edu.cn": SourceType.UNIVERSITY,       # 中国科大

    # 教育类网站
    "eol.cn": SourceType.EDUCATION,            # 中国教育在线
    "gaokao.com": SourceType.EDUCATION,        # 高考网
    "51meishu.com": SourceType.EDUCATION,      # 美术高考网

    # 主流媒体
    "people.com.cn": SourceType.MEDIA,         # 人民网
    "xinhuanet.com": SourceType.MEDIA,         # 新华网
    "cctv.com": SourceType.MEDIA,              # 央视网
    "china.com.cn": SourceType.MEDIA,          # 中国网

    # 论坛/社区
    "zhihu.com": SourceType.FORUM,             # 知乎
    "tieba.baidu.com": SourceType.FORUM,       # 百度贴吧
    "weibo.com": SourceType.FORUM,             # 微博
}


def classify_source(url: str) -> SourceType:
    """根据 URL 域名分类来源类型"""
    parsed = urlparse(url)
    domain = parsed.netloc.lower()

    # 移除 www. 前缀
    if domain.startswith("www."):
        domain = domain[4:]

    # 精确匹配
    if domain in DOMAIN_SOURCE_MAP:
        return DOMAIN_SOURCE_MAP[domain]

    # 子域名匹配
    for known_domain, source_type in DOMAIN_SOURCE_MAP.items():
        if domain.endswith("." + known_domain) or domain == known_domain:
            return source_type

    # 启发式判断
    if domain.endswith(".gov.cn") or domain.endswith(".gov"):
        return SourceType.GOVERNMENT
    if domain.endswith(".edu.cn") or domain.endswith(".edu"):
        return SourceType.UNIVERSITY

    return SourceType.OTHER


def calculate_freshness(published_date: datetime | None) -> tuple[FreshnessLevel, str]:
    """
    计算新鲜度等级

    返回：(新鲜度等级, 判定原因)
    """
    if published_date is None:
        return FreshnessLevel.ATTENTION, "发布日期未知，建议核实时效性"

    now = datetime.now()
    age = now - published_date

    if age <= timedelta(days=365):
        return FreshnessLevel.NORMAL, f"数据时效性良好（{age.days}天内）"
    elif age <= timedelta(days=365 * 3):
        years = age.days / 365
        return FreshnessLevel.ATTENTION, f"数据较旧（约{years:.1f}年前），请注意时效性"
    else:
        years = age.days / 365
        return FreshnessLevel.WARNING, f"数据较旧（约{years:.1f}年前），建议寻找更新数据源"


def calculate_credibility_score(
    source_type: SourceType,
    published_date: datetime | None,
) -> float:
    """
    计算可信度评分

    公式：基础权重 × 时效性衰减系数
    """
    # 基础权重
    base_weight = SOURCE_TYPE_WEIGHTS.get(source_type, 0.5)

    # 时效性衰减系数
    if published_date is None:
        decay_factor = 0.8  # 未知日期，轻微衰减
    else:
        now = datetime.now()
        age_days = (now - published_date).days

        if age_days <= 365:
            decay_factor = 1.0  # 1年内：无衰减
        elif age_days <= 365 * 3:
            decay_factor = 0.9  # 1-3年：轻微衰减
        elif age_days <= 365 * 5:
            decay_factor = 0.7  # 3-5年：中度衰减
        else:
            decay_factor = 0.5  # 5年以上：严重衰减

    return round(base_weight * decay_factor, 2)


class CredibilityScorer:
    """可信度评分器"""

    def score_result(self, result: SearchResult) -> SearchResult:
        """对单条搜索结果评分"""
        # 分类来源
        source_type = classify_source(result.url)

        # 计算新鲜度
        freshness_level, freshness_reason = calculate_freshness(result.published_date)

        # 计算可信度评分
        credibility_score = calculate_credibility_score(source_type, result.published_date)

        return result.model_copy(update={
            "source_type": source_type,
            "freshness_level": freshness_level,
            "freshness_reason": freshness_reason,
            "credibility_score": credibility_score,
        })

    def score_results(self, results: list[SearchResult]) -> list[SearchResult]:
        """对多条搜索结果评分并按可信度排序"""
        scored = [self.score_result(r) for r in results]
        # 按可信度降序排序
        return sorted(scored, key=lambda r: r.credibility_score, reverse=True)
