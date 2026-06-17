"""Unified seed-data import CLI.

Examples:
    python -m backend.seeds.import_cli --dataset basic --dry-run
    python -m backend.seeds.import_cli --dataset full --duplicate-policy update
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Sequence
from contextlib import closing
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal, cast

from sqlalchemy.orm import Session

from backend.database import Base, SessionLocal, engine
from backend.models import AdmissionScore, EnrollmentPlan, Major, School, SubjectRanking

DuplicatePolicy = Literal["skip", "update", "error"]
DatasetName = Literal["basic", "full", "extended"]

DATA_DIR = Path(__file__).parent

DATASETS: dict[DatasetName, dict[str, list[str]]] = {
    "basic": {
        "schools": ["seed_schools.json"],
        "majors": ["seed_majors.json"],
        "scores": ["seed_scores_all.json"],
        "plans": ["seed_plans.json"],
        "rankings": ["seed_subject_rankings.json"],
    },
    "full": {
        "schools": ["seed_schools_full.json"],
        "majors": ["seed_majors_full.json"],
        "scores": ["seed_scores_full.json"],
        "plans": [],
        "rankings": [],
    },
    "extended": {
        "schools": [
            "seed_schools.json",
            "seed_schools_extended.json",
            "seed_schools_west.json",
            "seed_schools_central.json",
            "seed_schools_east.json",
            "seed_schools_v2.json",
        ],
        "majors": [
            "seed_majors.json",
            "seed_majors_extended.json",
            "seed_majors_expanded.json",
        ],
        "scores": [
            "seed_scores_all.json",
            "seed_scores_extended.json",
            "seed_scores_v2.json",
            "seed_scores_province.json",
        ],
        "plans": ["seed_plans.json", "seed_plans_extended.json", "seed_plans_v2.json"],
        "rankings": ["seed_subject_rankings.json"],
    },
}


@dataclass
class SectionReport:
    loaded: int = 0
    valid: int = 0
    invalid: int = 0
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class ImportReport:
    dataset: str
    dry_run: bool
    duplicate_policy: DuplicatePolicy
    files: dict[str, list[str]]
    schools: SectionReport = field(default_factory=SectionReport)
    majors: SectionReport = field(default_factory=SectionReport)
    scores: SectionReport = field(default_factory=SectionReport)
    plans: SectionReport = field(default_factory=SectionReport)
    rankings: SectionReport = field(default_factory=SectionReport)

    def sections(self) -> tuple[SectionReport, ...]:
        return (self.schools, self.majors, self.scores, self.plans, self.rankings)

    def summary(self) -> dict[str, int | bool]:
        totals = {
            field_name: sum(getattr(section, field_name) for section in self.sections())
            for field_name in (
                "loaded",
                "valid",
                "invalid",
                "inserted",
                "updated",
                "skipped",
            )
        }
        totals["error_count"] = sum(len(section.errors) for section in self.sections())
        totals["has_errors"] = self.has_errors()
        return totals

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["summary"] = self.summary()
        return data

    def has_errors(self) -> bool:
        return any(section.invalid > 0 or bool(section.errors) for section in self.sections())


def load_json_file(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"{path.name} must contain a JSON array")
    return [cast(dict[str, Any], item) for item in data if isinstance(item, dict)]


def load_records(
    files: Sequence[str], data_dir: Path = DATA_DIR
) -> tuple[list[dict[str, Any]], list[str]]:
    records: list[dict[str, Any]] = []
    loaded_files: list[str] = []
    for filename in files:
        path = data_dir / filename
        if not path.exists():
            continue
        records.extend(load_json_file(path))
        loaded_files.append(filename)
    return records, loaded_files


def validate_required(
    records: Sequence[dict[str, Any]],
    required: Sequence[str],
    section: SectionReport,
    label_key: str = "name",
    validators: Sequence[Callable[[dict[str, Any]], list[str]]] = (),
) -> list[dict[str, Any]]:
    valid: list[dict[str, Any]] = []
    section.loaded += len(records)
    for idx, item in enumerate(records, start=1):
        label = item.get(label_key, f"row-{idx}")
        missing = [key for key in required if item.get(key) in (None, "")]
        if missing:
            section.invalid += 1
            section.errors.append(f"{label}: missing {', '.join(missing)}")
            continue
        errors = [error for validator in validators for error in validator(item)]
        if errors:
            section.invalid += 1
            section.errors.extend(f"{label}: {error}" for error in errors)
            continue
        section.valid += 1
        valid.append(item)
    return valid


def _number_between(
    item: dict[str, Any],
    field_name: str,
    minimum: float,
    maximum: float,
) -> str | None:
    value = item.get(field_name)
    if value is None:
        return None
    if not isinstance(value, int | float) or value < minimum or value > maximum:
        return f"{field_name} out of range [{minimum:g}, {maximum:g}]"
    return None


def validate_score_quality(item: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field_name in ("min_score", "avg_score", "max_score"):
        error = _number_between(item, field_name, 0, 750)
        if error:
            errors.append(error)
    year_error = _number_between(item, "year", 2000, 2100)
    if year_error:
        errors.append(year_error)
    return errors


def validate_plan_quality(item: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field_name, minimum, maximum in (
        ("plan_count", 0, 1000),
        ("duration", 2, 8),
        ("tuition", 0, 200000),
    ):
        error = _number_between(item, field_name, minimum, maximum)
        if error:
            errors.append(error)
    year_error = _number_between(item, "year", 2000, 2100)
    if year_error:
        errors.append(year_error)
    return errors


def _school_defaults(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "province": item["province"],
        "city": item.get("city", ""),
        "level": item["level"],
        "school_type": item.get("school_type", ""),
        "ranking": item.get("ranking"),
        "is_985": item.get("is_985", 0),
        "is_211": item.get("is_211", 0),
        "is_double_first_class": item.get("is_double_first_class", 0),
        "website": item.get("website"),
        "description": item.get("description"),
    }


def _major_defaults(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "category": item["category"],
        "sub_category": item.get("sub_category"),
        "employment_rate": item.get("employment_rate"),
        "avg_salary": item.get("avg_salary"),
        "median_salary": item.get("median_salary"),
        "salary_range": item.get("salary_range"),
        "top_industries": item.get("top_industries"),
        "employment_locations": item.get("employment_locations"),
        "postgraduate_rate": item.get("postgraduate_rate"),
        "overseas_rate": item.get("overseas_rate"),
        "description": item.get("description"),
        "job_directions": item.get("job_directions"),
        "is_hot": item.get("is_hot", 0),
    }


def _apply_attrs(instance: Any, attrs: dict[str, Any]) -> None:
    for key, value in attrs.items():
        setattr(instance, key, value)


def import_schools(
    db: Session,
    records: Sequence[dict[str, Any]],
    report: SectionReport,
    duplicate_policy: DuplicatePolicy,
    dry_run: bool,
) -> dict[str, int]:
    schools = validate_required(records, ["name", "province", "level"], report)
    name_to_id: dict[str, int] = {
        cast(str, school.name): cast(int, school.id) for school in db.query(School).all()
    }

    for item in schools:
        name = str(item["name"])
        attrs = _school_defaults(item)
        existing = db.query(School).filter(School.name == name).first()
        if existing:
            if duplicate_policy == "error":
                report.invalid += 1
                report.errors.append(f"{name}: duplicate school")
                continue
            if duplicate_policy == "update":
                report.updated += 1
                if not dry_run:
                    _apply_attrs(existing, attrs)
            else:
                report.skipped += 1
            name_to_id[name] = cast(int, existing.id)
            continue

        report.inserted += 1
        if dry_run:
            name_to_id[name] = -report.inserted
            continue

        school = cast(Any, School(name=name, **attrs))
        db.add(school)
        db.flush()
        name_to_id[name] = cast(int, school.id)

    return name_to_id


def import_majors(
    db: Session,
    records: Sequence[dict[str, Any]],
    report: SectionReport,
    duplicate_policy: DuplicatePolicy,
    dry_run: bool,
) -> dict[str, int]:
    majors = validate_required(records, ["name", "category"], report)
    name_to_id: dict[str, int] = {
        cast(str, major.name): cast(int, major.id) for major in db.query(Major).all()
    }

    for item in majors:
        name = str(item["name"])
        attrs = _major_defaults(item)
        existing = db.query(Major).filter(Major.name == name).first()
        if existing:
            if duplicate_policy == "error":
                report.invalid += 1
                report.errors.append(f"{name}: duplicate major")
                continue
            if duplicate_policy == "update":
                report.updated += 1
                if not dry_run:
                    _apply_attrs(existing, attrs)
            else:
                report.skipped += 1
            name_to_id[name] = cast(int, existing.id)
            continue

        report.inserted += 1
        if dry_run:
            name_to_id[name] = -report.inserted
            continue

        major = cast(Any, Major(name=name, **attrs))
        db.add(major)
        db.flush()
        name_to_id[name] = cast(int, major.id)

    return name_to_id


def _score_key(item: dict[str, Any], school_id: int) -> tuple[int, str, int, str, str]:
    return (
        school_id,
        str(item["province"]),
        int(item["year"]),
        str(item.get("batch", "")),
        str(item.get("subject_type", "")),
    )


def _score_attrs(item: dict[str, Any], school_id: int) -> dict[str, Any]:
    return {
        "school_id": school_id,
        "major_id": None,
        "province": item["province"],
        "year": item["year"],
        "batch": item.get("batch", ""),
        "subject_type": item.get("subject_type", ""),
        "min_score": item.get("min_score"),
        "avg_score": item.get("avg_score"),
        "max_score": item.get("max_score"),
        "min_rank": item.get("min_rank"),
    }


def _plan_key(
    item: dict[str, Any],
    school_id: int,
    major_id: int,
) -> tuple[int, int, str, int]:
    return (
        school_id,
        major_id,
        str(item["province"]),
        int(item["year"]),
    )


def _plan_attrs(item: dict[str, Any], school_id: int, major_id: int) -> dict[str, Any]:
    return {
        "school_id": school_id,
        "major_id": major_id,
        "province": item["province"],
        "year": item["year"],
        "plan_count": item.get("plan_count"),
        "subject_requirement": item.get("subject_requirement"),
        "batch": item.get("batch"),
        "duration": item.get("duration"),
        "tuition": item.get("tuition"),
    }


def _ranking_key(item: dict[str, Any], school_id: int) -> tuple[int, str, str, int]:
    return (
        school_id,
        str(item["major_category"]),
        str(item["ranking_source"]),
        int(item["ranking_year"]),
    )


def _ranking_attrs(item: dict[str, Any], school_id: int) -> dict[str, Any]:
    return {
        "school_id": school_id,
        "major_category": item["major_category"],
        "ranking_source": item["ranking_source"],
        "ranking_year": item["ranking_year"],
        "ranking_position": item.get("ranking_position"),
        "grade": item.get("grade"),
    }


def import_scores(
    db: Session,
    records: Sequence[dict[str, Any]],
    school_map: dict[str, int],
    report: SectionReport,
    duplicate_policy: DuplicatePolicy,
    dry_run: bool,
) -> None:
    scores = validate_required(
        records,
        ["school_name", "province", "year", "batch", "subject_type"],
        report,
        label_key="school_name",
        validators=(validate_score_quality,),
    )
    seen_keys: set[tuple[int, str, int, str, str]] = set()

    for item in scores:
        school_name = str(item["school_name"])
        school_id = school_map.get(school_name)
        if not school_id:
            report.skipped += 1
            report.errors.append(f"{school_name}: school not found")
            continue

        key = _score_key(item, school_id)
        if key in seen_keys:
            report.skipped += 1
            report.errors.append(f"{school_name}: duplicate score in input")
            continue
        seen_keys.add(key)

        existing = (
            db.query(AdmissionScore)
            .filter(
                AdmissionScore.school_id == school_id,
                AdmissionScore.major_id.is_(None),
                AdmissionScore.province == item["province"],
                AdmissionScore.year == item["year"],
                AdmissionScore.batch == item.get("batch", ""),
                AdmissionScore.subject_type == item.get("subject_type", ""),
            )
            .first()
        )
        attrs = _score_attrs(item, school_id)
        if existing:
            if duplicate_policy == "error":
                report.invalid += 1
                report.errors.append(f"{school_name}: duplicate score")
                continue
            if duplicate_policy == "update":
                report.updated += 1
                if not dry_run:
                    _apply_attrs(existing, attrs)
            else:
                report.skipped += 1
            continue

        report.inserted += 1
        if not dry_run:
            db.add(AdmissionScore(**attrs))


def import_plans(
    db: Session,
    records: Sequence[dict[str, Any]],
    school_map: dict[str, int],
    major_map: dict[str, int],
    report: SectionReport,
    duplicate_policy: DuplicatePolicy,
    dry_run: bool,
) -> None:
    plans = validate_required(
        records,
        ["school_name", "major_name", "province", "year"],
        report,
        label_key="school_name",
        validators=(validate_plan_quality,),
    )
    seen_keys: set[tuple[int, int, str, int]] = set()

    for item in plans:
        school_name = str(item["school_name"])
        major_name = str(item["major_name"])
        school_id = school_map.get(school_name)
        major_id = major_map.get(major_name)
        if not school_id or not major_id:
            report.skipped += 1
            report.errors.append(f"{school_name}/{major_name}: school or major not found")
            continue

        key = _plan_key(item, school_id, major_id)
        if key in seen_keys:
            report.skipped += 1
            report.errors.append(f"{school_name}/{major_name}: duplicate plan in input")
            continue
        seen_keys.add(key)

        existing = (
            db.query(EnrollmentPlan)
            .filter(
                EnrollmentPlan.school_id == school_id,
                EnrollmentPlan.major_id == major_id,
                EnrollmentPlan.province == item["province"],
                EnrollmentPlan.year == item["year"],
            )
            .first()
        )
        attrs = _plan_attrs(item, school_id, major_id)
        if existing:
            if duplicate_policy == "error":
                report.invalid += 1
                report.errors.append(f"{school_name}/{major_name}: duplicate plan")
                continue
            if duplicate_policy == "update":
                report.updated += 1
                if not dry_run:
                    _apply_attrs(existing, attrs)
            else:
                report.skipped += 1
            continue

        report.inserted += 1
        if not dry_run:
            db.add(EnrollmentPlan(**attrs))


def import_rankings(
    db: Session,
    records: Sequence[dict[str, Any]],
    school_map: dict[str, int],
    report: SectionReport,
    duplicate_policy: DuplicatePolicy,
    dry_run: bool,
) -> None:
    rankings = validate_required(
        records,
        ["school_name", "major_category", "ranking_source", "ranking_year"],
        report,
        label_key="school_name",
    )
    seen_keys: set[tuple[int, str, str, int]] = set()

    for item in rankings:
        school_name = str(item["school_name"])
        school_id = school_map.get(school_name)
        if not school_id:
            report.skipped += 1
            report.errors.append(f"{school_name}: school not found")
            continue

        key = _ranking_key(item, school_id)
        if key in seen_keys:
            report.skipped += 1
            report.errors.append(f"{school_name}: duplicate ranking in input")
            continue
        seen_keys.add(key)

        existing = (
            db.query(SubjectRanking)
            .filter(
                SubjectRanking.school_id == school_id,
                SubjectRanking.major_category == item["major_category"],
                SubjectRanking.ranking_source == item["ranking_source"],
                SubjectRanking.ranking_year == item["ranking_year"],
            )
            .first()
        )
        attrs = _ranking_attrs(item, school_id)
        if existing:
            if duplicate_policy == "error":
                report.invalid += 1
                report.errors.append(f"{school_name}: duplicate ranking")
                continue
            if duplicate_policy == "update":
                report.updated += 1
                if not dry_run:
                    _apply_attrs(existing, attrs)
            else:
                report.skipped += 1
            continue

        report.inserted += 1
        if not dry_run:
            db.add(SubjectRanking(**attrs))


def run_import(
    dataset: DatasetName,
    duplicate_policy: DuplicatePolicy = "skip",
    dry_run: bool = False,
    data_dir: Path = DATA_DIR,
) -> ImportReport:
    files = DATASETS[dataset]
    report = ImportReport(
        dataset=dataset,
        dry_run=dry_run,
        duplicate_policy=duplicate_policy,
        files={},
    )

    Base.metadata.create_all(bind=engine)
    with closing(SessionLocal()) as db:
        schools, school_files = load_records(files["schools"], data_dir)
        majors, major_files = load_records(files["majors"], data_dir)
        scores, score_files = load_records(files["scores"], data_dir)
        plans, plan_files = load_records(files["plans"], data_dir)
        rankings, ranking_files = load_records(files["rankings"], data_dir)
        report.files = {
            "schools": school_files,
            "majors": major_files,
            "scores": score_files,
            "plans": plan_files,
            "rankings": ranking_files,
        }

        school_map = import_schools(db, schools, report.schools, duplicate_policy, dry_run)
        major_map = import_majors(db, majors, report.majors, duplicate_policy, dry_run)
        import_scores(db, scores, school_map, report.scores, duplicate_policy, dry_run)
        import_plans(
            db,
            plans,
            school_map,
            major_map,
            report.plans,
            duplicate_policy,
            dry_run,
        )
        import_rankings(
            db,
            rankings,
            school_map,
            report.rankings,
            duplicate_policy,
            dry_run,
        )

        if dry_run:
            db.rollback()
        else:
            db.commit()

    return report


def write_report(report: ImportReport, report_path: Path | None) -> None:
    text = json.dumps(report.to_dict(), ensure_ascii=False, indent=2)
    if report_path:
        report_path.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import seed JSON data into the local database.")
    parser.add_argument("--dataset", choices=sorted(DATASETS), default="basic")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--duplicate-policy", choices=["skip", "update", "error"], default="skip")
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    parser.add_argument("--report-path", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run_import(
        dataset=cast(DatasetName, args.dataset),
        duplicate_policy=cast(DuplicatePolicy, args.duplicate_policy),
        dry_run=bool(args.dry_run),
        data_dir=args.data_dir,
    )
    write_report(report, args.report_path)
    return 1 if report.has_errors() else 0


if __name__ == "__main__":
    raise SystemExit(main())
