"""
种子数据导入脚本

使用方法:
    cd backend && python -m seeds.import_data
"""
import json
import os
from pathlib import Path

from backend.database import SessionLocal, engine, Base
from backend.models import School, Major, AdmissionScore, EnrollmentPlan


def load_json(filename: str) -> list[dict]:
    """加载 JSON 种子数据文件"""
    data_dir = Path(__file__).parent
    filepath = data_dir / filename
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def import_schools(db, schools_data: list[dict]) -> dict[str, int]:
    """导入院校数据，返回 {院校名: id} 映射"""
    name_to_id = {}
    for item in schools_data:
        school = School(
            name=item["name"],
            province=item["province"],
            city=item["city"],
            level=item["level"],
            school_type=item["school_type"],
            ranking=item.get("ranking"),
            is_985=item.get("is_985", 0),
            is_211=item.get("is_211", 0),
            is_double_first_class=item.get("is_double_first_class", 0),
        )
        db.add(school)
        db.flush()
        name_to_id[school.name] = school.id
    db.commit()
    return name_to_id


def import_majors(db, majors_data: list[dict]) -> dict[str, int]:
    """导入专业数据，返回 {专业名: id} 映射"""
    name_to_id = {}
    for item in majors_data:
        major = Major(
            name=item["name"],
            category=item["category"],
            sub_category=item.get("sub_category"),
            employment_rate=item.get("employment_rate"),
            avg_salary=item.get("avg_salary"),
            description=item.get("description"),
            job_directions=item.get("job_directions"),
            is_hot=item.get("is_hot", 0),
        )
        db.add(major)
        db.flush()
        name_to_id[major.name] = major.id
    db.commit()
    return name_to_id


def import_scores(db, scores_data: list[dict], school_map: dict[str, int]):
    """导入分数线数据"""
    for item in scores_data:
        school_id = school_map.get(item["school_name"])
        if not school_id:
            print(f"  [跳过] 院校不存在: {item['school_name']}")
            continue

        score = AdmissionScore(
            school_id=school_id,
            major_id=None,  # 院校级分数线，不关联专业
            province=item["province"],
            year=item["year"],
            batch=item["batch"],
            subject_type=item["subject_type"],
            min_score=item.get("min_score"),
            avg_score=item.get("avg_score"),
            max_score=item.get("max_score"),
            min_rank=item.get("min_rank"),
        )
        db.add(score)
    db.commit()


def import_plans(db, plans_data: list[dict], school_map: dict[str, int], major_map: dict[str, int]):
    """导入招生计划数据"""
    for item in plans_data:
        school_id = school_map.get(item["school_name"])
        major_id = major_map.get(item["major_name"])

        if not school_id:
            print(f"  [跳过] 院校不存在: {item['school_name']}")
            continue
        if not major_id:
            print(f"  [跳过] 专业不存在: {item['major_name']}")
            continue

        plan = EnrollmentPlan(
            school_id=school_id,
            major_id=major_id,
            province=item["province"],
            year=item["year"],
            plan_count=item.get("plan_count"),
            subject_requirement=item.get("subject_requirement"),
            batch=item.get("batch"),
            duration=item.get("duration"),
            tuition=item.get("tuition"),
        )
        db.add(plan)
    db.commit()


def run_import():
    """执行全量数据导入"""
    print("=" * 50)
    print("张雪峰 AI Agent — 种子数据导入")
    print("=" * 50)

    # 创建表（如果不存在）
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # 1. 导入院校
        schools_data = load_json("seed_schools.json")
        print(f"\n[1/4] 导入院校 ({len(schools_data)} 条)...")
        school_map = import_schools(db, schools_data)
        print(f"  ✓ 成功导入 {len(school_map)} 所院校")

        # 2. 导入专业
        majors_data = load_json("seed_majors.json")
        print(f"\n[2/4] 导入专业 ({len(majors_data)} 条)...")
        major_map = import_majors(db, majors_data)
        print(f"  ✓ 成功导入 {len(major_map)} 个专业")

        # 3. 导入分数线
        scores_data = load_json("seed_scores.json")
        print(f"\n[3/4] 导入分数线 ({len(scores_data)} 条)...")
        import_scores(db, scores_data, school_map)
        print(f"  ✓ 成功导入 {len(scores_data)} 条分数线")

        # 4. 导入招生计划
        plans_data = load_json("seed_plans.json")
        print(f"\n[4/4] 导入招生计划 ({len(plans_data)} 条)...")
        import_plans(db, plans_data, school_map, major_map)
        print(f"  ✓ 成功导入 {len(plans_data)} 条招生计划")

        print("\n" + "=" * 50)
        print("数据导入完成！")
        print("=" * 50)

    except Exception as e:
        db.rollback()
        print(f"\n导入失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_import()
