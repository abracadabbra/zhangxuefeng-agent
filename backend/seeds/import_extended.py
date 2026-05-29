"""
扩展数据导入脚本

支持多文件导入，数据质量检查，增量更新

使用方法:
    cd backend && python -m seeds.import_extended
"""
import json
import sys
from contextlib import closing
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import create_engine

# 确保项目根目录在 sys.path 中，支持从 backend/ 或项目根目录运行
_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from backend.database import DATABASE_URL, Base
from backend.models import School, Major, AdmissionScore, EnrollmentPlan


def load_json(filename: str) -> list[dict]:
    """加载 JSON 文件"""
    data_dir = Path(__file__).parent
    filepath = data_dir / filename
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def get_or_create_school(db: Session, name: str, defaults: dict) -> School:
    """获取或创建院校"""
    school = db.query(School).filter(School.name == name).first()
    if not school:
        school = School(name=name, **defaults)
        db.add(school)
        db.flush()
    return school


def get_or_create_major(db: Session, name: str, defaults: dict) -> Major:
    """获取或创建专业"""
    major = db.query(Major).filter(Major.name == name).first()
    if not major:
        major = Major(name=name, **defaults)
        db.add(major)
        db.flush()
    return major


def import_schools_batch(db: Session, schools_data: list[dict]) -> dict[str, int]:
    """批量导入院校"""
    name_to_id = {}
    for item in schools_data:
        school = get_or_create_school(db, item["name"], {
            "province": item["province"],
            "city": item["city"],
            "level": item["level"],
            "school_type": item["school_type"],
            "ranking": item.get("ranking"),
            "is_985": item.get("is_985", 0),
            "is_211": item.get("is_211", 0),
            "is_double_first_class": item.get("is_double_first_class", 0),
        })
        name_to_id[school.name] = school.id
    db.commit()
    return name_to_id


def import_scores_batch(db: Session, scores_data: list[dict], school_map: dict[str, int], major_map: dict[str, int]):
    """批量导入分数线"""
    imported = 0
    skipped = 0
    for item in scores_data:
        school_name = item.get("school_name") or item.get("name")
        school_id = school_map.get(school_name)
        if not school_id:
            skipped += 1
            continue

        # 检查是否已存在
        existing = db.query(AdmissionScore).filter(
            AdmissionScore.school_id == school_id,
            AdmissionScore.province == item["province"],
            AdmissionScore.year == item["year"],
            AdmissionScore.batch == item["batch"],
            AdmissionScore.subject_type == item["subject_type"],
        ).first()

        if existing:
            skipped += 1
            continue

        score = AdmissionScore(
            school_id=school_id,
            major_id=None,
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
        imported += 1

    db.commit()
    return imported, skipped


def import_plans_batch(db: Session, plans_data: list[dict], school_map: dict[str, int], major_map: dict[str, int]):
    """批量导入招生计划"""
    imported = 0
    skipped = 0
    for item in plans_data:
        school_id = school_map.get(item["school_name"])
        major_id = major_map.get(item["major_name"])

        if not school_id or not major_id:
            skipped += 1
            continue

        # 检查是否已存在
        existing = db.query(EnrollmentPlan).filter(
            EnrollmentPlan.school_id == school_id,
            EnrollmentPlan.major_id == major_id,
            EnrollmentPlan.province == item["province"],
            EnrollmentPlan.year == item["year"],
        ).first()

        if existing:
            skipped += 1
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
        imported += 1

    db.commit()
    return imported, skipped


def run_extended_import():
    """执行扩展数据导入"""
    print("=" * 60)
    print("张雪峰 AI Agent — 扩展数据导入")
    print("=" * 60)

    # 创建引擎和表
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)

    Session = sessionmaker(bind=engine)

    with closing(Session()) as db:
        # 1. 导入扩展院校
        print("\n[1/3] 导入扩展院校...")
        school_files = [
            "seed_schools.json",
            "seed_schools_extended.json",
            "seed_schools_west.json",
            "seed_schools_central.json",
            "seed_schools_east.json",
            "seed_schools_v2.json",
        ]

        all_schools = []
        for filename in school_files:
            try:
                data = load_json(filename)
                all_schools.extend(data)
                print(f"  加载 {filename}: {len(data)} 条")
            except FileNotFoundError:
                print(f"  跳过 {filename}: 文件不存在")

        school_map = import_schools_batch(db, all_schools)
        print(f"  ✓ 院校总数: {len(school_map)}")

        # 2. 导入专业
        print("\n[2/4] 导入专业...")
        major_files = ["seed_majors.json", "seed_majors_extended.json", "seed_majors_expanded.json"]
        all_majors = []
        for filename in major_files:
            try:
                data = load_json(filename)
                all_majors.extend(data)
                print(f"  加载 {filename}: {len(data)} 条")
            except FileNotFoundError:
                print(f"  跳过 {filename}: 文件不存在")

        major_map = {}
        for item in all_majors:
            major = get_or_create_major(db, item["name"], {
                "category": item["category"],
                "sub_category": item.get("sub_category"),
                "employment_rate": item.get("employment_rate"),
                "avg_salary": item.get("avg_salary"),
                "description": item.get("description"),
                "job_directions": item.get("job_directions"),
                "is_hot": item.get("is_hot", 0),
            })
            major_map[major.name] = major.id
        db.commit()
        print(f"  ✓ 专业总数: {len(major_map)}")

        # 3. 导入扩展分数线（优先使用全量数据）
        print("\n[3/4] 导入扩展分数线...")
        score_files = ["seed_scores_all.json", "seed_scores.json", "seed_scores_extended.json", "seed_scores_province.json", "seed_scores_v2.json"]

        all_scores = []
        for filename in score_files:
            try:
                data = load_json(filename)
                all_scores.extend(data)
                print(f"  加载 {filename}: {len(data)} 条")
            except FileNotFoundError:
                print(f"  跳过 {filename}: 文件不存在")

        imported, skipped = import_scores_batch(db, all_scores, school_map, major_map)
        print(f"  ✓ 导入 {imported} 条，跳过 {skipped} 条")

        # 4. 导入招生计划
        print("\n[4/4] 导入招生计划...")
        plan_files = ["seed_plans.json", "seed_plans_extended.json", "seed_plans_v2.json"]

        all_plans = []
        for filename in plan_files:
            try:
                data = load_json(filename)
                all_plans.extend(data)
                print(f"  加载 {filename}: {len(data)} 条")
            except FileNotFoundError:
                print(f"  跳过 {filename}: 文件不存在")

        imported, skipped = import_plans_batch(db, all_plans, school_map, major_map)
        print(f"  ✓ 导入 {imported} 条，跳过 {skipped} 条")

        # 统计
        print("\n" + "=" * 60)
        print("数据导入完成!")
        print(f"  院校: {db.query(School).count()}")
        print(f"  专业: {db.query(Major).count()}")
        print(f"  分数线: {db.query(AdmissionScore).count()}")
        print(f"  招生计划: {db.query(EnrollmentPlan).count()}")
        print("=" * 60)

    except Exception as e:
        print(f"\n导入失败: {e}")
        raise


if __name__ == "__main__":
    # 运行数据质量检查
    from backend.seeds.data_quality import run_quality_check
    print("\n" + "=" * 60)
    print("步骤 1: 数据质量检查")
    print("=" * 60)
    run_quality_check()

    # 运行导入
    print("\n" + "=" * 60)
    print("步骤 2: 数据导入")
    print("=" * 60)
    run_extended_import()
