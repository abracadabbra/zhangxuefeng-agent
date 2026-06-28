"""
导入浙江省 2025 年高考投档分数线数据

数据来源：
- 浙江省教育考试院发布的普通类第一段/第二段平行投档分数线
- 文件位于 backend/seeds/zhejiang_2025/ 目录

使用方法：
    source .venv/bin/activate
    python -m backend.seeds.import_zhejiang --dry-run    # 仅验证，不写入
    python -m backend.seeds.import_zhejiang              # 实际导入
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from backend.database import Base, SessionLocal, engine
from backend.models import AdmissionScore, School

DATA_DIR = Path(__file__).parent / "zhejiang_2025"

EXCEL_FILES = {
    "一段": "浙江省2025年普通高校招生普通类第一段平行投档分数线表.xls",
    "二段": "浙江省2025年普通高校招生普通类第二段平行投档分数线.xls",
}

PROVINCE = "浙江"
YEAR = 2025
SUBJECT_TYPE = None  # 新高考 3+3 不分文理


def _to_int(value, default=None):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_excel(path: Path, batch: str) -> pd.DataFrame:
    """读取并规范化浙江 Excel 数据"""
    df = pd.read_excel(path)
    df.columns = [
        "school_code",
        "school_name",
        "major_code",
        "major_label",
        "plan_count",
        "min_score",
        "min_rank",
    ]
    df["batch"] = batch
    df["province"] = PROVINCE
    df["year"] = YEAR
    df["subject_type"] = SUBJECT_TYPE
    return df


def upsert_school(db: Session, name: str, cache: dict) -> int:
    """获取或自动创建学校"""
    if name in cache:
        return cache[name]
    existing = db.query(School).filter(School.name == name).first()
    if existing:
        cache[name] = existing.id
        return existing.id
    school = School(
        name=name,
        province="未知",
        city="",
        level="普通",
        school_type="",
    )
    db.add(school)
    db.flush()
    cache[name] = school.id
    return school.id


def import_dataframe(
    db: Session,
    df: pd.DataFrame,
    school_cache: dict,
    *,
    dry_run: bool = False,
) -> tuple[int, int, int]:
    """导入一个 Excel 数据框，返回 (inserted, skipped, errors)"""
    inserted = 0
    skipped = 0
    errors = 0
    for _, row in df.iterrows():
        try:
            school_name = str(row["school_name"]).strip()
            major_label = str(row["major_label"]).strip()
            if not school_name or not major_label:
                skipped += 1
                continue
            school_id = upsert_school(db, school_name, school_cache)

            existing = (
                db.query(AdmissionScore)
                .filter(
                    AdmissionScore.school_id == school_id,
                    AdmissionScore.major_id.is_(None),
                    AdmissionScore.major_label == major_label,
                    AdmissionScore.province == PROVINCE,
                    AdmissionScore.year == YEAR,
                    AdmissionScore.batch == row["batch"],
                )
                .first()
            )
            if existing:
                skipped += 1
                continue

            record = AdmissionScore(
                school_id=school_id,
                major_id=None,
                major_label=major_label,
                province=PROVINCE,
                year=YEAR,
                batch=row["batch"],
                subject_type=SUBJECT_TYPE,
                min_score=_to_int(row["min_score"]),
                min_rank=_to_int(row["min_rank"]),
                plan_count=_to_int(row["plan_count"]),
            )
            if dry_run:
                db.rollback()  # 不持久化
            else:
                db.add(record)
            inserted += 1
        except Exception as exc:
            errors += 1
            print(f"  ❌ row error: {row.get('school_name')}/{row.get('major_label')}: {exc}")
    return inserted, skipped, errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="导入浙江 2025 高考投档分数线")
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    parser.add_argument("--dry-run", action="store_true", help="仅验证不写入")
    args = parser.parse_args(argv)

    Base.metadata.create_all(bind=engine)

    school_cache: dict[str, int] = {
        s.name: s.id for s in SessionLocal().query(School).all()
    }
    print(f"📚 已有学校 {len(school_cache)} 所")

    total_inserted = 0
    total_skipped = 0
    total_errors = 0

    with SessionLocal() as db:
        for batch, filename in EXCEL_FILES.items():
            path = args.data_dir / filename
            if not path.exists():
                print(f"⚠️  缺少文件: {path}")
                continue
            print(f"\n📥 读取 {filename}...")
            df = parse_excel(path, batch)
            print(f"   行数: {len(df)}")
            inserted, skipped, errors = import_dataframe(
                db, df, school_cache, dry_run=args.dry_run
            )
            print(f"   ✅ 插入 {inserted}, 跳过 {skipped}, 错误 {errors}")
            total_inserted += inserted
            total_skipped += skipped
            total_errors += errors
        if args.dry_run:
            db.rollback()
        else:
            db.commit()

    print(f"\n📊 汇总: 插入 {total_inserted}, 跳过 {total_skipped}, 错误 {total_errors}")
    if args.dry_run:
        print("🔍 Dry-run 模式，未写入数据库")
    return 0 if total_errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
