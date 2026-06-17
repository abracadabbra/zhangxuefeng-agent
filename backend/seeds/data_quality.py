"""
数据质量检查工具

检查种子数据的完整性、一致性和有效性
"""

import json
from pathlib import Path


def load_json(filename: str) -> list[dict]:
    """加载 JSON 文件"""
    data_dir = Path(__file__).parent
    filepath = data_dir / filename
    with open(filepath, encoding="utf-8") as f:
        return json.load(f)


def check_schools(schools: list[dict]) -> list[str]:
    """检查院校数据质量"""
    issues = []
    names = set()
    provinces = set()

    for i, school in enumerate(schools):
        # 必填字段检查
        required = ["name", "province", "city", "level", "school_type"]
        for field in required:
            if field not in school or not school[field]:
                issues.append(f"院校[{i}] 缺少必填字段: {field}")

        # 名称唯一性
        name = school.get("name", "")
        if name in names:
            issues.append(f"院校[{i}] 名称重复: {name}")
        names.add(name)

        # 层次有效性
        level = school.get("level", "")
        valid_levels = ["985", "211", "双一流", "普通"]
        if level not in valid_levels:
            issues.append(f"院校[{i}] 层次无效: {level}")

        # 类型有效性
        school_type = school.get("school_type", "")
        valid_types = [
            "综合",
            "理工",
            "医药",
            "师范",
            "财经",
            "政法",
            "农林",
            "语言",
            "艺术",
            "体育",
            "民族",
        ]
        if school_type not in valid_types:
            issues.append(f"院校[{i}] 类型无效: {school_type}")

        # 985/211 标记一致性
        is_985 = school.get("is_985", 0)
        is_211 = school.get("is_211", 0)
        if is_985 == 1 and level != "985":
            issues.append(f"院校[{i}] is_985=1 但 level={level}")
        if is_211 == 1 and level not in ["985", "211"]:
            issues.append(f"院校[{i}] is_211=1 但 level={level}")

        # 排名范围
        ranking = school.get("ranking")
        if ranking is not None and (ranking < 1 or ranking > 300):
            issues.append(f"院校[{i}] 排名异常: {ranking}")

        provinces.add(school.get("province", ""))

    return issues


def check_majors(majors: list[dict]) -> list[str]:
    """检查专业数据质量"""
    issues = []
    names = set()

    for i, major in enumerate(majors):
        # 必填字段检查
        required = ["name", "category"]
        for field in required:
            if field not in major or not major[field]:
                issues.append(f"专业[{i}] 缺少必填字段: {field}")

        # 名称唯一性
        name = major.get("name", "")
        if name in names:
            issues.append(f"专业[{i}] 名称重复: {name}")
        names.add(name)

        # 就业率范围
        emp_rate = major.get("employment_rate")
        if emp_rate is not None and (emp_rate < 0 or emp_rate > 1):
            issues.append(f"专业[{i}] 就业率超出范围: {emp_rate}")

        # 薪资范围
        salary = major.get("avg_salary")
        if salary is not None and (salary < 0 or salary > 100000):
            issues.append(f"专业[{i}] 平均薪资异常: {salary}")

    return issues


def check_scores(scores: list[dict]) -> list[str]:
    """检查分数线数据质量"""
    issues = []

    for i, score in enumerate(scores):
        # 必填字段检查
        required = ["school_name", "province", "year", "batch", "subject_type"]
        for field in required:
            if field not in score or not score[field]:
                issues.append(f"分数线[{i}] 缺少必填字段: {field}")

        # 年份范围
        year = score.get("year")
        if year is not None and (year < 2020 or year > 2026):
            issues.append(f"分数线[{i}] 年份异常: {year}")

        # 分数范围
        min_score = score.get("min_score")
        if min_score is not None and (min_score < 0 or min_score > 750):
            issues.append(f"分数线[{i}] 最低分异常: {min_score}")

        # 批次有效性
        batch = score.get("batch", "")
        valid_batches = ["本科一批", "本科二批", "提前批", "专科", "本科批"]
        if batch and batch not in valid_batches:
            issues.append(f"分数线[{i}] 批次无效: {batch}")

        # 科类有效性
        subject_type = score.get("subject_type", "")
        valid_subjects = ["理工", "文史", "综合", "物理类", "历史类", "理科", "文科"]
        if subject_type and subject_type not in valid_subjects:
            issues.append(f"分数线[{i}] 科类无效: {subject_type}")

    return issues


def check_plans(plans: list[dict]) -> list[str]:
    """检查招生计划数据质量"""
    issues = []

    for i, plan in enumerate(plans):
        # 必填字段检查
        required = ["school_name", "major_name", "province", "year"]
        for field in required:
            if field not in plan or not plan[field]:
                issues.append(f"招生计划[{i}] 缺少必填字段: {field}")

        # 招生人数
        plan_count = plan.get("plan_count")
        if plan_count is not None and (plan_count < 0 or plan_count > 1000):
            issues.append(f"招生计划[{i}] 人数异常: {plan_count}")

        # 学制
        duration = plan.get("duration")
        if duration is not None and (duration < 2 or duration > 8):
            issues.append(f"招生计划[{i}] 学制异常: {duration}")

        # 学费
        tuition = plan.get("tuition")
        if tuition is not None and (tuition < 0 or tuition > 200000):
            issues.append(f"招生计划[{i}] 学费异常: {tuition}")

    return issues


def run_quality_check():
    """执行全量数据质量检查"""
    print("=" * 60)
    print("数据质量检查报告")
    print("=" * 60)

    all_issues = []

    # 检查院校
    schools = load_json("seed_schools.json")
    extended = load_json("seed_schools_extended.json")
    west = load_json("seed_schools_west.json")
    central = load_json("seed_schools_central.json")
    east = load_json("seed_schools_east.json")
    v2_schools = load_json("seed_schools_v2.json")
    all_schools = schools + extended + west + central + east + v2_schools
    school_files = [
        f"seed_schools.json({len(schools)})",
        f"seed_schools_extended.json({len(extended)})",
        f"seed_schools_west.json({len(west)})",
        f"seed_schools_central.json({len(central)})",
        f"seed_schools_east.json({len(east)})",
        f"seed_schools_v2.json({len(v2_schools)})",
    ]
    print(f"  文件: {', '.join(school_files)}")

    print(f"\n[院校] 总数: {len(all_schools)}")
    school_issues = check_schools(all_schools)
    if school_issues:
        for issue in school_issues:
            print(f"  ⚠ {issue}")
        all_issues.extend(school_issues)
    else:
        print("  ✓ 数据质量良好")

    # 检查专业
    majors = load_json("seed_majors.json")
    try:
        ext_majors = load_json("seed_majors_extended.json")
        expanded_majors = load_json("seed_majors_expanded.json")
        majors = majors + ext_majors + expanded_majors
        major_files = [
            f"seed_majors.json({len(majors) - len(ext_majors) - len(expanded_majors)})",
            f"seed_majors_extended.json({len(ext_majors)})",
            f"seed_majors_expanded.json({len(expanded_majors)})",
        ]
        print(f"  文件: {', '.join(major_files)}")
    except FileNotFoundError:
        pass
    print(f"\n[专业] 总数: {len(majors)}")
    major_issues = check_majors(majors)
    if major_issues:
        for issue in major_issues:
            print(f"  ⚠ {issue}")
        all_issues.extend(major_issues)
    else:
        print("  ✓ 数据质量良好")

    # 检查分数线
    scores = load_json("seed_scores.json")
    try:
        ext_scores = load_json("seed_scores_extended.json")
        province_scores = load_json("seed_scores_province.json")
        v2_scores = load_json("seed_scores_v2.json")
        scores = scores + ext_scores + province_scores + v2_scores
        score_files = [
            "seed_scores.json",
            "seed_scores_extended.json",
            "seed_scores_province.json",
            "seed_scores_v2.json",
        ]
        print(f"  文件: {', '.join(score_files)}")
    except FileNotFoundError:
        pass
    print(f"\n[分数线] 总数: {len(scores)}")
    score_issues = check_scores(scores)
    if score_issues:
        for issue in score_issues:
            print(f"  ⚠ {issue}")
        all_issues.extend(score_issues)
    else:
        print("  ✓ 数据质量良好")

    # 检查招生计划
    plans = load_json("seed_plans.json")
    try:
        ext_plans = load_json("seed_plans_extended.json")
        v2_plans = load_json("seed_plans_v2.json")
        plans = plans + ext_plans + v2_plans
        print("  文件: seed_plans.json, seed_plans_extended.json, seed_plans_v2.json")
    except FileNotFoundError:
        pass
    print(f"\n[招生计划] 总数: {len(plans)}")
    plan_issues = check_plans(plans)
    if plan_issues:
        for issue in plan_issues:
            print(f"  ⚠ {issue}")
        all_issues.extend(plan_issues)
    else:
        print("  ✓ 数据质量良好")

    # 总结
    print("\n" + "=" * 60)
    if all_issues:
        print(f"发现 {len(all_issues)} 个数据质量问题")
    else:
        print("所有数据质量检查通过!")
    print("=" * 60)

    return len(all_issues) == 0


if __name__ == "__main__":
    run_quality_check()
