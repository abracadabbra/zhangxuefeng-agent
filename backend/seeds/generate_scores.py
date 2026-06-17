"""
生成全国 31 省份、5 年跨度（2021-2025）的分数线种子数据

包括：
- 普通类（理工/文史/物理类/历史类/综合）
- 艺术类
- 体育类

使用方法:
    cd backend && python -m seeds.generate_scores
"""

import json
import random
from pathlib import Path
from typing import cast

# 全国 31 个省份
ALL_PROVINCES = [
    "北京",
    "天津",
    "上海",
    "重庆",
    "河北",
    "山西",
    "辽宁",
    "吉林",
    "黑龙江",
    "江苏",
    "浙江",
    "安徽",
    "福建",
    "江西",
    "山东",
    "河南",
    "湖北",
    "湖南",
    "广东",
    "海南",
    "四川",
    "贵州",
    "云南",
    "陕西",
    "甘肃",
    "青海",
    "内蒙古",
    "广西",
    "西藏",
    "宁夏",
    "新疆",
]

# 新高考改革省份（2021年起不分文理，按物理/历史分科）
# 第一批（2017）：浙江、上海（综合）
# 第二批（2020）：北京、天津、山东、海南（综合）
# 第三批（2021）：河北、辽宁、江苏、福建、湖北、湖南、广东、重庆（物理类/历史类）
# 第四批（2024）：甘肃、黑龙江、吉林、安徽、江西、贵州、广西（物理类/历史类）
NEW_GAOKAO_V1 = ["浙江", "上海"]  # 综合
NEW_GAOKAO_V2 = ["北京", "天津", "山东", "海南"]  # 综合
NEW_GAOKAO_V3 = ["河北", "辽宁", "江苏", "福建", "湖北", "湖南", "广东", "重庆"]  # 物理/历史
NEW_GAOKAO_V4 = ["甘肃", "黑龙江", "吉林", "安徽", "江西", "贵州", "广西"]  # 物理/历史 (2024起)
# 传统文理分科省份（2025年仍适用）
TRADITIONAL = [
    p
    for p in ALL_PROVINCES
    if p not in NEW_GAOKAO_V1 + NEW_GAOKAO_V2 + NEW_GAOKAO_V3 + NEW_GAOKAO_V4
]


def get_subject_types(province: str, year: int) -> list[str]:
    """根据省份和年份返回适用的科类"""
    if province in NEW_GAOKAO_V1:
        return ["综合"]
    if province in NEW_GAOKAO_V2:
        return ["综合"]
    if province in NEW_GAOKAO_V3:
        if year >= 2021:
            return ["物理类", "历史类"]
        return ["理工", "文史"]
    if province in NEW_GAOKAO_V4:
        if year >= 2024:
            return ["物理类", "历史类"]
        return ["理工", "文史"]
    # 传统省份
    return ["理工", "文史"]


# 50 所代表性院校及其基准分（2025 理工/物理类，河南省）
SCHOOLS = [
    # 985 第一梯队
    {"name": "清华大学", "tier": 1, "base_score": 690, "base_rank": 40},
    {"name": "北京大学", "tier": 1, "base_score": 688, "base_rank": 50},
    {"name": "浙江大学", "tier": 1, "base_score": 670, "base_rank": 350},
    {"name": "上海交通大学", "tier": 1, "base_score": 675, "base_rank": 250},
    {"name": "复旦大学", "tier": 1, "base_score": 668, "base_rank": 380},
    {"name": "中国科学技术大学", "tier": 1, "base_score": 672, "base_rank": 300},
    {"name": "南京大学", "tier": 1, "base_score": 660, "base_rank": 550},
    {"name": "武汉大学", "tier": 2, "base_score": 640, "base_rank": 1500},
    {"name": "华中科技大学", "tier": 2, "base_score": 638, "base_rank": 1600},
    {"name": "中山大学", "tier": 2, "base_score": 630, "base_rank": 2000},
    # 985 第二梯队
    {"name": "哈尔滨工业大学", "tier": 2, "base_score": 635, "base_rank": 1700},
    {"name": "西安交通大学", "tier": 2, "base_score": 632, "base_rank": 1800},
    {"name": "北京航空航天大学", "tier": 2, "base_score": 650, "base_rank": 900},
    {"name": "同济大学", "tier": 2, "base_score": 648, "base_rank": 950},
    {"name": "东南大学", "tier": 2, "base_score": 635, "base_rank": 1500},
    {"name": "电子科技大学", "tier": 2, "base_score": 632, "base_rank": 1700},
    {"name": "四川大学", "tier": 2, "base_score": 618, "base_rank": 2800},
    {"name": "山东大学", "tier": 2, "base_score": 610, "base_rank": 3200},
    {"name": "中南大学", "tier": 2, "base_score": 612, "base_rank": 3000},
    {"name": "吉林大学", "tier": 2, "base_score": 600, "base_rank": 4000},
    {"name": "大连理工大学", "tier": 2, "base_score": 608, "base_rank": 3200},
    {"name": "华南理工大学", "tier": 2, "base_score": 615, "base_rank": 2800},
    {"name": "重庆大学", "tier": 2, "base_score": 600, "base_rank": 4000},
    {"name": "西北工业大学", "tier": 2, "base_score": 610, "base_rank": 3000},
    {"name": "兰州大学", "tier": 2, "base_score": 585, "base_rank": 6000},
    # 211 / 双一流
    {"name": "北京邮电大学", "tier": 3, "base_score": 638, "base_rank": 1400},
    {"name": "上海财经大学", "tier": 3, "base_score": 622, "base_rank": 2300},
    {"name": "中央财经大学", "tier": 3, "base_score": 618, "base_rank": 2600},
    {"name": "西安电子科技大学", "tier": 3, "base_score": 608, "base_rank": 3200},
    {"name": "北京交通大学", "tier": 3, "base_score": 605, "base_rank": 3500},
    {"name": "南京航空航天大学", "tier": 3, "base_score": 602, "base_rank": 3800},
    {"name": "南京理工大学", "tier": 3, "base_score": 600, "base_rank": 4000},
    {"name": "武汉理工大学", "tier": 3, "base_score": 590, "base_rank": 5000},
    {"name": "华中师范大学", "tier": 3, "base_score": 595, "base_rank": 4500},
    {"name": "西南大学", "tier": 3, "base_score": 580, "base_rank": 6500},
    {"name": "郑州大学", "tier": 3, "base_score": 578, "base_rank": 11000},
    {"name": "苏州大学", "tier": 3, "base_score": 592, "base_rank": 4800},
    {"name": "暨南大学", "tier": 3, "base_score": 588, "base_rank": 5200},
    {"name": "深圳大学", "tier": 3, "base_score": 595, "base_rank": 4500},
    {"name": "南方科技大学", "tier": 3, "base_score": 610, "base_rank": 3200},
    # 普通本科
    {"name": "燕山大学", "tier": 4, "base_score": 560, "base_rank": 18000},
    {"name": "浙江工业大学", "tier": 4, "base_score": 565, "base_rank": 16000},
    {"name": "南京工业大学", "tier": 4, "base_score": 558, "base_rank": 19000},
    {"name": "广东工业大学", "tier": 4, "base_score": 555, "base_rank": 20000},
    {"name": "昆明理工大学", "tier": 4, "base_score": 540, "base_rank": 28000},
    {"name": "西安建筑科技大学", "tier": 4, "base_score": 545, "base_rank": 25000},
    {"name": "长沙理工大学", "tier": 4, "base_score": 548, "base_rank": 23000},
    {"name": "河南大学", "tier": 4, "base_score": 565, "base_rank": 16000},
    {"name": "山西大学", "tier": 4, "base_score": 545, "base_rank": 25000},
    {"name": "黑龙江大学", "tier": 4, "base_score": 535, "base_rank": 30000},
]

# 省份分数调整系数（相对于河南的难度差异）
# 正值表示该省分数线更高（竞争更激烈），负值表示更低
PROVINCE_OFFSET = {
    "河南": 0,
    "山东": 2,
    "河北": 3,
    "广东": 5,
    "江苏": 8,
    "浙江": 10,
    "湖北": 3,
    "湖南": 2,
    "四川": -2,
    "安徽": 3,
    "福建": -3,
    "江西": 0,
    "辽宁": -5,
    "吉林": -8,
    "黑龙江": -10,
    "陕西": -5,
    "山西": -3,
    "重庆": -2,
    "甘肃": -12,
    "贵州": -15,
    "云南": -15,
    "广西": -12,
    "内蒙古": -18,
    "宁夏": -20,
    "新疆": -18,
    "青海": -25,
    "西藏": -40,
    "海南": -8,
    "天津": 12,
    "北京": 15,
    "上海": 12,
}

# 年份调整（分数线年度波动）
YEAR_OFFSET = {
    2021: -8,
    2022: -5,
    2023: -3,
    2024: 0,
    2025: 3,
}

# 文科比理工科分数线通常低 10-30 分
LITERATURE_OFFSET = {
    1: -5,  # 顶尖学校差距小
    2: -15,
    3: -20,
    4: -25,
}

# 艺术类分数线（通常比普通类低很多）
ART_OFFSET = {
    1: -180,
    2: -160,
    3: -140,
    4: -120,
}

# 体育类分数线
SPORT_OFFSET = {
    1: -150,
    2: -130,
    3: -110,
    4: -90,
}


def generate_scores() -> list[dict]:
    """生成完整分数线数据"""
    records = []
    random.seed(42)  # 可复现

    for school in SCHOOLS:
        for province in ALL_PROVINCES:
            for year in range(2021, 2026):
                subject_types = get_subject_types(province, year)

                for subject_type in subject_types:
                    # 普通类
                    tier = cast(int, school["tier"])
                    base = cast(int, school["base_score"])
                    base_rank = cast(int, school["base_rank"])
                    offset = PROVINCE_OFFSET.get(province, 0)
                    year_adj = YEAR_OFFSET.get(year, 0)

                    is_literature = subject_type in ("文史", "历史类")
                    lit_adj = LITERATURE_OFFSET[tier] if is_literature else 0

                    # 添加随机波动
                    noise = random.randint(-3, 3)

                    min_score = max(200, base + offset + year_adj + lit_adj + noise)
                    avg_score = min_score + random.randint(5, 15)
                    max_score = avg_score + random.randint(5, 15)
                    min_rank = max(
                        1,
                        int(
                            base_rank * (1 + (PROVINCE_OFFSET.get(province, 0) + year_adj) / 100)
                            + random.randint(-100, 100)
                        ),
                    )

                    # 综合改革省份满分 750，但上海 660，海南有标准分
                    if province == "上海":
                        min_score = int(min_score * 660 / 750)
                        avg_score = int(avg_score * 660 / 750)
                        max_score = int(max_score * 660 / 750)
                    elif province == "海南":
                        # 海南标准分 900 满分
                        min_score = int(min_score * 900 / 750)
                        avg_score = int(avg_score * 900 / 750)
                        max_score = int(max_score * 900 / 750)

                    batch = "本科一批" if tier <= 3 else "本科二批"
                    if tier == 1 and province in ("北京", "上海"):
                        batch = "提前批"

                    records.append(
                        {
                            "school_name": school["name"],
                            "province": province,
                            "year": year,
                            "batch": batch,
                            "subject_type": subject_type,
                            "min_score": min_score,
                            "avg_score": round(avg_score, 1),
                            "max_score": max_score,
                            "min_rank": min_rank,
                        }
                    )

                    # 艺术类（仅部分年份有数据）
                    if year >= 2022:
                        art_offset = ART_OFFSET[tier]
                        art_noise = random.randint(-10, 10)
                        art_base = max(200, min_score + art_offset + art_noise)

                        records.append(
                            {
                                "school_name": school["name"],
                                "province": province,
                                "year": year,
                                "batch": "提前批",
                                "subject_type": f"艺术类（{subject_type}）",
                                "min_score": art_base,
                                "avg_score": art_base + random.randint(10, 30),
                                "max_score": art_base + random.randint(30, 60),
                                "min_rank": None,
                            }
                        )

                    # 体育类（仅部分年份有数据）
                    if year >= 2022:
                        sport_offset = SPORT_OFFSET[tier]
                        sport_noise = random.randint(-8, 8)
                        sport_base = max(200, min_score + sport_offset + sport_noise)

                        records.append(
                            {
                                "school_name": school["name"],
                                "province": province,
                                "year": year,
                                "batch": "提前批",
                                "subject_type": f"体育类（{subject_type}）",
                                "min_score": sport_base,
                                "avg_score": sport_base + random.randint(8, 20),
                                "max_score": sport_base + random.randint(20, 50),
                                "min_rank": None,
                            }
                        )

    return records


def main():
    print("生成全国分数线数据...")
    records = generate_scores()

    # 统计
    provinces = set(r["province"] for r in records)
    years = set(r["year"] for r in records)
    schools = set(r["school_name"] for r in records)
    subject_types = set(r["subject_type"] for r in records)

    print(f"  省份: {len(provinces)} 个")
    print(f"  年份: {sorted(years)}")
    print(f"  院校: {len(schools)} 所")
    print(f"  科类: {sorted(subject_types)}")
    print(f"  总记录: {len(records)} 条")

    # 写入文件
    output = Path(__file__).parent / "seed_scores_all.json"
    with open(output, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    print(f"\n已保存至: {output}")


if __name__ == "__main__":
    main()
