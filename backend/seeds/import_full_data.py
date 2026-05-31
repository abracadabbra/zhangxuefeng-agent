"""
导入完整种子数据到数据库

使用方法:
    cd backend && python -m seeds.import_full_data
"""
import json
from pathlib import Path
from contextlib import closing

from backend.database import Base, SessionLocal, engine
from backend.models import AdmissionScore, School


def load_json(filename: str) -> list[dict]:
    data_dir = Path(__file__).parent
    filepath = data_dir / filename
    with open(filepath, encoding="utf-8") as f:
        return json.load(f)


def import_schools(db, schools_data: list[dict]) -> dict[str, int]:
    """导入院校数据，返回 {院校名: id} 映射（跳过重名）"""
    name_to_id = {}
    seen = set()
    skipped = 0
    for item in schools_data:
        name = item["name"]
        if name in seen:
            skipped += 1
            continue
        seen.add(name)
        school = School(
            name=name,
            province=item["province"],
            city=item.get("city", ""),
            level=item["level"],
            school_type=item.get("school_type", ""),
            ranking=item.get("ranking"),
            is_985=item.get("is_985", False),
            is_211=item.get("is_211", False),
            is_double_first_class=item.get("is_double_first_class", False),
            website=item.get("website", ""),
            description=item.get("description", ""),
        )
        db.add(school)
        db.flush()
        name_to_id[school.name] = school.id
    db.commit()
    if skipped:
        print(f"  跳过重名: {skipped} 所")
    return name_to_id


def import_scores(db, scores_data: list[dict], school_map: dict[str, int]):
    """导入分数线数据"""
    count = 0
    skipped = 0
    for item in scores_data:
        school_id = school_map.get(item["school_name"])
        if not school_id:
            skipped += 1
            continue
        score = AdmissionScore(
            school_id=school_id,
            province=item["province"],
            year=item["year"],
            subject_type=item.get("subject_type", ""),
            batch=item.get("batch", ""),
            min_score=item.get("min_score"),
            max_score=item.get("max_score"),
            avg_score=item.get("avg_score"),
            min_rank=item.get("min_rank"),
        )
        db.add(score)
        count += 1
        if count % 5000 == 0:
            db.commit()
    db.commit()
    return count, skipped


def run_import():
    """执行导入"""
    print("正在创建表结构...")
    Base.metadata.create_all(bind=engine)

    with closing(SessionLocal()) as db:
        # 清空现有数据（按外键依赖顺序）
        print("清空现有数据...")
        db.query(AdmissionScore).delete()
        db.query(School).delete()
        db.commit()

        # 导入学校
        schools_data = load_json("seed_schools_full.json")
        print(f"导入学校数据: {len(schools_data)} 所...")
        school_map = import_schools(db, schools_data)
        print(f"  完成: {len(school_map)} 所学校已入库")

        # 导入分数线
        scores_data = load_json("seed_scores_full.json")
        print(f"导入分数线数据: {len(scores_data)} 条...")
        count, skipped = import_scores(db, scores_data, school_map)
        print(f"  完成: {count} 条已入库, {skipped} 条跳过")

    print("\n导入完成！")


if __name__ == "__main__":
    run_import()
