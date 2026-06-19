"""Static no-write evidence artifact smoke tests."""

import json
from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = PROJECT_ROOT / "examples" / "real_data" / "artifacts"


def load_artifact(name: str) -> dict:
    with (ARTIFACTS_DIR / name).open(encoding="utf-8") as f:
        return json.load(f)


class StaticEvidenceArtifactTest(unittest.TestCase):
    def test_checked_in_artifacts_have_expected_readiness(self) -> None:
        expectations = {
            "sd_source_snapshot_planning_blocked.json": {
                "action": "source_snapshot_planning_review",
                "passed": False,
                "ready_field": "ready_for_snapshot_planning",
                "ready": False,
            },
            "source_snapshot_planning_approved_example.json": {
                "action": "source_snapshot_planning_review",
                "passed": True,
                "ready_field": "ready_for_snapshot_planning",
                "ready": True,
            },
            "priority_source_coverage_report.json": {
                "action": "source_coverage_report",
                "passed": True,
            },
            "priority_source_coverage_action_queue.json": {
                "action": "priority_source_coverage_action_queue",
                "passed": False,
                "ready_field": "ready_for_human_review",
                "ready": True,
            },
            "priority_source_year_review_coverage_report.json": {
                "action": "source_year_review_coverage_report",
                "passed": False,
                "ready_field": "ready_for_priority_source_year_registration",
                "ready": False,
            },
            "ha_source_year_review_blocked.json": {
                "action": "source_year_review",
                "passed": False,
                "ready_field": "ready_for_source_year_registration",
                "ready": False,
            },
            "sd_source_usage_review_blocked.json": {
                "action": "source_usage_review",
                "passed": False,
                "ready_field": "ready_for_source_approval_license_review",
                "ready": False,
            },
            "source_usage_review_reviewed_example.json": {
                "action": "source_usage_review",
                "passed": True,
                "ready_field": "ready_for_source_approval_license_review",
                "ready": True,
            },
            "source_usage_to_approval_chain_smoke_reviewed_example.json": {
                "action": "source_usage_to_approval_chain_smoke",
                "passed": True,
            },
            "sd_source_review_human_checklist_blocked.json": {
                "action": "source_review_human_checklist",
                "passed": False,
                "ready_field": "ready_for_source_review_approval",
                "ready": False,
            },
            "sd_source_review_handoff_blocked.json": {
                "action": "source_review_handoff",
                "passed": False,
                "ready_field": "ready_for_source_review_handoff",
                "ready": False,
            },
            "sd_source_review_chain_smoke_blocked.json": {
                "action": "source_review_chain_smoke",
                "passed": False,
            },
            "sd_source_review_approval_candidate_review.json": {
                "action": "source_review_approval_review",
                "passed": False,
                "ready_field": "ready_for_registry_update",
                "ready": False,
            },
            "source_review_chain_smoke_reviewed_example.json": {
                "action": "source_review_chain_smoke",
                "passed": True,
            },
            "source_review_chain_smoke_reviewed_example_update_plan.json": {
                "action": "source_registry_update_plan",
                "passed": True,
                "ready_field": "ready_for_registry_patch",
                "ready": True,
            },
            "source_registry_patch_approval_reviewed_example_review.json": {
                "action": "source_registry_patch_approval_review",
                "passed": True,
                "ready_field": "ready_for_registry_patch_execution",
                "ready": True,
            },
            "source_registry_patch_preview_reviewed_example.json": {
                "action": "source_registry_patch_preview",
                "passed": True,
                "ready_field": "ready_for_registry_patch_preview",
                "ready": True,
            },
            "source_registry_patch_chain_smoke_reviewed_example.json": {
                "action": "source_registry_patch_chain_smoke",
                "passed": True,
            },
            "source_review_approval_reviewed_example_review.json": {
                "action": "source_review_approval_review",
                "passed": True,
                "ready_field": "ready_for_registry_update",
                "ready": True,
            },
            "source_review_approval_reviewed_example_update_plan_blocked.json": {
                "action": "source_registry_update_plan",
                "passed": False,
                "ready_field": "ready_for_registry_patch",
                "ready": False,
            },
            "sd_source_registry_update_plan_blocked.json": {
                "action": "source_registry_update_plan",
                "passed": False,
                "ready_field": "ready_for_registry_patch",
                "ready": False,
            },
            "sd_source_registry_patch_approval_blocked.json": {
                "action": "source_registry_patch_approval_review",
                "passed": False,
                "ready_field": "ready_for_registry_patch_execution",
                "ready": False,
            },
            "sd_source_registry_patch_preview_blocked.json": {
                "action": "source_registry_patch_preview",
                "passed": False,
                "ready_field": "ready_for_registry_patch_preview",
                "ready": False,
            },
            "sd_source_registry_patch_chain_smoke_blocked.json": {
                "action": "source_registry_patch_chain_smoke",
                "passed": False,
            },
            "source_to_intake_chain_smoke_approved_example.json": {
                "action": "source_to_intake_chain_smoke",
                "passed": True,
            },
            "sd_loader_run_evidence_templates_blocked.json": {
                "action": "loader_run_evidence_review",
                "passed": False,
                "ready_field": "ready_for_activation_evidence",
                "ready": False,
            },
            "source_intake_review_approved_example.json": {
                "action": "official_sample_intake_review",
                "passed": True,
                "ready_field": "ready_for_snapshot",
                "ready": True,
            },
            "source_parser_rows_bundle_smoke_approved_example.json": {
                "action": "parser_rows_bundle_smoke",
                "passed": True,
                "ready_field": "ready_for_parser",
                "ready": True,
            },
            "source_quality_smoke_approved_example.json": {
                "action": "quality_smoke_review",
                "passed": True,
                "ready_field": "ready_for_quality_gate",
                "ready": True,
            },
            "source_to_quality_chain_smoke_approved_example.json": {
                "action": "source_to_quality_chain_smoke",
                "passed": True,
            },
            "sd_parser_rows_bundle_smoke.json": {
                "action": "parser_rows_bundle_smoke",
                "passed": True,
                "ready_field": "ready_for_parser",
                "ready": True,
            },
            "sd_quality_smoke.json": {
                "action": "quality_smoke_review",
                "passed": True,
                "ready_field": "ready_for_quality_gate",
                "ready": True,
            },
            "sd_example_chain_smoke.json": {
                "action": "real_data_example_chain_smoke",
                "passed": True,
            },
            "sd_example_chain_smoke_templates_blocked.json": {
                "action": "real_data_example_chain_smoke",
                "passed": False,
            },
            "sd_mvp_readiness_summary.json": {
                "action": "real_data_mvp_readiness_summary",
                "passed": False,
                "ready_field": "ready_for_real_snapshot",
                "ready": False,
            },
            "sd_mvp_action_queue.json": {
                "action": "real_data_mvp_action_queue",
                "passed": False,
                "ready_field": "ready_for_human_review",
                "ready": True,
            },
        }

        for name, expected in expectations.items():
            with self.subTest(name=name):
                artifact = load_artifact(name)
                self.assertEqual(artifact["action"], expected["action"])
                self.assertIs(artifact["passed"], expected["passed"])
                ready_field = expected.get("ready_field")
                if ready_field:
                    self.assertIs(artifact[ready_field], expected["ready"])

    def test_checked_in_artifacts_keep_no_write_non_goals(self) -> None:
        artifact_names = [
            "sd_source_snapshot_planning_blocked.json",
            "source_snapshot_planning_approved_example.json",
            "priority_source_coverage_report.json",
            "priority_source_coverage_action_queue.json",
            "priority_source_year_review_coverage_report.json",
            "ha_source_year_review_blocked.json",
            "sd_source_usage_review_blocked.json",
            "source_usage_review_reviewed_example.json",
            "source_usage_to_approval_chain_smoke_reviewed_example.json",
            "sd_source_review_human_checklist_blocked.json",
            "sd_source_review_handoff_blocked.json",
            "sd_source_review_chain_smoke_blocked.json",
            "sd_source_review_approval_candidate_review.json",
            "source_review_chain_smoke_reviewed_example.json",
            "source_review_chain_smoke_reviewed_example_update_plan.json",
            "source_registry_patch_approval_reviewed_example_review.json",
            "source_registry_patch_preview_reviewed_example.json",
            "source_registry_patch_chain_smoke_reviewed_example.json",
            "source_review_approval_reviewed_example_review.json",
            "source_review_approval_reviewed_example_update_plan_blocked.json",
            "sd_source_registry_update_plan_blocked.json",
            "sd_source_registry_patch_approval_blocked.json",
            "sd_source_registry_patch_preview_blocked.json",
            "sd_source_registry_patch_chain_smoke_blocked.json",
            "source_to_intake_chain_smoke_approved_example.json",
            "sd_loader_run_evidence_templates_blocked.json",
            "source_intake_review_approved_example.json",
            "source_parser_rows_bundle_smoke_approved_example.json",
            "source_quality_smoke_approved_example.json",
            "source_to_quality_chain_smoke_approved_example.json",
            "sd_parser_rows_bundle_smoke.json",
            "sd_quality_smoke.json",
            "sd_example_chain_smoke.json",
            "sd_example_chain_smoke_templates_blocked.json",
            "sd_mvp_readiness_summary.json",
            "sd_mvp_action_queue.json",
        ]

        for name in artifact_names:
            with self.subTest(name=name):
                non_goals = load_artifact(name).get("non_goals")
                self.assertIsInstance(non_goals, list)
                self.assertTrue(non_goals)
                self.assertTrue(
                    any("Does not" in item for item in non_goals),
                    msg=f"{name} should preserve no-write non_goals",
                )

    def test_aggregate_artifacts_expose_required_reviews(self) -> None:
        passed_chain = load_artifact("sd_example_chain_smoke.json")
        blocked_chain = load_artifact(
            "sd_example_chain_smoke_templates_blocked.json"
        )

        self.assertIn(
            "Provide a separate approved loader run command.",
            passed_chain["required_reviews"],
        )
        self.assertIn(
            "Provide separate Agent visibility approval.",
            passed_chain["required_reviews"],
        )
        self.assertIn(
            "Confirm Agent visibility approval explicitly allows activation.",
            blocked_chain["required_reviews"],
        )

    def test_aggregate_artifacts_expose_loader_evidence_review(self) -> None:
        passed_chain = load_artifact("sd_example_chain_smoke.json")
        blocked_chain = load_artifact(
            "sd_example_chain_smoke_templates_blocked.json"
        )

        self.assertIsNone(passed_chain["reviews"]["loader_run_evidence"])
        self.assertFalse(
            blocked_chain["reviews"]["loader_run_evidence"][
                "ready_for_activation_evidence"
            ]
        )
        self.assertIn(
            "Record loader run ID and completion time.",
            blocked_chain["reviews"]["loader_run_evidence"]["required_reviews"],
        )

    def test_priority_source_coverage_keeps_snapshot_planning_blocked(self) -> None:
        coverage = load_artifact("priority_source_coverage_report.json")

        self.assertTrue(coverage["passed"])
        self.assertFalse(coverage["readiness"]["ready_for_snapshot_planning"])
        self.assertEqual(
            coverage["gap_summary"]["missing_priority_provinces"],
            [],
        )
        self.assertIn(
            "河南",
            coverage["gap_summary"]["priority_provinces_without_years"],
        )
        self.assertIn(
            "山东",
            coverage["gap_summary"]["priority_provinces_without_approved_source"],
        )

    def test_priority_source_coverage_action_queue_exposes_human_actions(self) -> None:
        queue = load_artifact("priority_source_coverage_action_queue.json")

        self.assertFalse(queue["passed"])
        self.assertTrue(queue["ready_for_human_review"])
        self.assertEqual(queue["next_gate"], "review_priority_dataset_years")
        self.assertEqual(len(queue["priority_actions"]), 15)
        action_ids = {item["id"] for item in queue["priority_actions"]}
        self.assertIn("review_dataset_year:河南", action_ids)
        self.assertIn("complete_source_approval:山东", action_ids)
        self.assertIn(
            "Review official dataset pages and candidate years.",
            queue["required_reviews"],
        )
        self.assertIn("Does not modify sources.json.", queue["non_goals"])

    def test_henan_source_year_review_keeps_registry_years_blocked(self) -> None:
        review = load_artifact("ha_source_year_review_blocked.json")

        self.assertFalse(review["ready_for_source_year_registration"])
        self.assertEqual(review["scope"]["source_id"], "ha_exam_authority")
        self.assertEqual(review["scope"]["province"], "河南")
        self.assertEqual(review["scope"]["candidate_years"], [])
        self.assertFalse(
            review["registry_update_hint"]["can_update_registry_years"],
        )
        self.assertIn(
            "Review official dataset candidate years.",
            review["required_reviews"],
        )

    def test_priority_source_year_review_coverage_blocks_missing_reviews(self) -> None:
        report = load_artifact("priority_source_year_review_coverage_report.json")

        self.assertFalse(report["passed"])
        self.assertFalse(report["ready_for_priority_source_year_registration"])
        self.assertEqual(report["next_gate"], "collect_priority_source_year_reviews")
        self.assertEqual(report["current_state"]["required_province_count"], 7)
        self.assertEqual(report["current_state"]["review_artifact_count"], 1)
        self.assertEqual(report["current_state"]["missing_review_count"], 6)
        self.assertIn("河南", report["blocked_reviews"])
        self.assertIn("广东", report["missing_reviews"])
        self.assertIn(
            "Create source year review packets for priority provinces.",
            report["required_reviews"],
        )
        self.assertIn("Does not modify sources.json.", report["non_goals"])

    def test_aggregate_artifacts_expose_parser_smoke_review(self) -> None:
        passed_chain = load_artifact("sd_example_chain_smoke.json")
        blocked_chain = load_artifact(
            "sd_example_chain_smoke_templates_blocked.json"
        )

        self.assertTrue(
            passed_chain["reviews"]["parser_rows_bundle_smoke"][
                "ready_for_parser"
            ]
        )
        self.assertTrue(
            blocked_chain["checks"]["parser_smoke_scope_matches_when_provided"]
        )
        self.assertEqual(
            passed_chain["reviews"]["parser_rows_bundle_smoke"]["scope"][
                "snapshot_id"
            ],
            "sd_pilot_2025_001",
        )
        parser_smoke = load_artifact("sd_parser_rows_bundle_smoke.json")
        candidate_source = parser_smoke["candidate_previews"][0]["source"]
        self.assertEqual(candidate_source["source_id"], "sd_exam_authority")
        self.assertEqual(candidate_source["dataset"], "admission_scores")
        self.assertEqual(candidate_source["year"], 2025)
        self.assertEqual(candidate_source["confidence"], 0.95)

    def test_aggregate_artifacts_expose_quality_smoke_review(self) -> None:
        passed_chain = load_artifact("sd_example_chain_smoke.json")
        blocked_chain = load_artifact(
            "sd_example_chain_smoke_templates_blocked.json"
        )

        self.assertTrue(
            passed_chain["reviews"]["quality_smoke"]["ready_for_quality_gate"]
        )
        self.assertTrue(
            blocked_chain["checks"]["quality_smoke_scope_matches_when_provided"]
        )
        self.assertEqual(
            passed_chain["reviews"]["quality_smoke"]["coverage"]["total"],
            1,
        )
        quality_smoke = load_artifact("sd_quality_smoke.json")
        self.assertEqual(
            quality_smoke["source_metadata"]["source_ids"],
            ["sd_exam_authority"],
        )
        self.assertEqual(
            quality_smoke["source_metadata"]["years"],
            [2025],
        )
        self.assertEqual(quality_smoke["source_metadata"]["confidence_min"], 0.95)

    def test_mvp_readiness_summary_separates_synthetic_and_real_ready(self) -> None:
        summary = load_artifact("sd_mvp_readiness_summary.json")

        self.assertTrue(summary["synthetic_chain_ready"])
        self.assertTrue(summary["source_to_quality_chain_ready"])
        self.assertTrue(summary["evidence_inventory_ready"])
        self.assertFalse(summary["ready_for_real_snapshot"])
        self.assertFalse(summary["ready_for_loader_discussion"])
        self.assertIn(
            "source_snapshot_planning_not_ready",
            summary["blockers"],
        )
        self.assertIn(
            "separate_agent_visibility_approval_required",
            summary["blockers"],
        )

    def test_mvp_action_queue_prioritizes_manual_source_review(self) -> None:
        queue = load_artifact("sd_mvp_action_queue.json")

        self.assertFalse(queue["passed"])
        self.assertTrue(queue["ready_for_human_review"])
        self.assertEqual(queue["next_gate"], "source_usage_and_citation_review")
        action_ids = [item["id"] for item in queue["priority_actions"]]
        self.assertEqual(action_ids[:3], [
            "review_usage_and_citation",
            "record_reviewer",
            "prepare_separate_source_approval",
        ])
        self.assertEqual(
            queue["priority_actions"][3]["id"],
            "resolve_source_snapshot_planning",
        )
        self.assertEqual(queue["priority_actions"][3]["status"], "blocked")
        self.assertEqual(
            queue["priority_actions"][4]["id"],
            "provide_loader_run_command",
        )
        self.assertEqual(queue["priority_actions"][4]["status"], "deferred")
        self.assertIn("Does not modify sources.json.", queue["non_goals"])

    def test_source_review_candidate_artifact_keeps_registry_blocked(self) -> None:
        review = load_artifact("sd_source_review_approval_candidate_review.json")

        self.assertFalse(review["ready_for_registry_update"])
        self.assertEqual(review["issue_counts"]["error"], 5)
        self.assertTrue(review["evidence_summary"]["has_dataset_page_url"])
        self.assertTrue(review["evidence_summary"]["has_attachment_url"])
        self.assertTrue(review["evidence_summary"]["published_year_confirmed"])
        self.assertFalse(review["evidence_summary"]["license_reviewed"])
        self.assertTrue(review["evidence_summary"]["has_usage_review"])
        self.assertFalse(review["evidence_summary"]["usage_review_ready"])
        self.assertIn(
            "Complete source usage review before source approval.",
            review["required_reviews"],
        )

    def test_source_usage_review_artifact_keeps_ingestion_blocked(self) -> None:
        review = load_artifact("sd_source_usage_review_blocked.json")

        self.assertFalse(review["ready_for_source_approval_license_review"])
        self.assertEqual(review["issue_counts"]["error"], 4)
        self.assertTrue(review["evidence_summary"]["has_source_url"])
        self.assertTrue(review["evidence_summary"]["has_attachment_url"])
        self.assertTrue(
            review["evidence_summary"]["redistribution_restriction_detected"],
        )
        self.assertFalse(review["evidence_summary"]["license_reviewed"])
        self.assertFalse(review["evidence_summary"]["allow_real_data_ingestion"])
        self.assertIn(
            "Approve real-data ingestion only after usage review passes.",
            review["required_reviews"],
        )

    def test_synthetic_source_usage_review_example_passes_no_write(self) -> None:
        review = load_artifact("source_usage_review_reviewed_example.json")

        self.assertTrue(review["ready_for_source_approval_license_review"])
        self.assertEqual(review["issue_counts"]["error"], 0)
        self.assertEqual(review["required_reviews"], [])
        self.assertEqual(
            review["scope"]["source_id"],
            "synthetic_reviewed_source_example",
        )
        self.assertTrue(review["evidence_summary"]["license_reviewed"])
        self.assertTrue(review["evidence_summary"]["allow_real_data_ingestion"])
        self.assertFalse(
            review["evidence_summary"]["redistribution_restriction_detected"],
        )
        self.assertIn(
            "Does not approve source registry changes.",
            review["non_goals"],
        )

    def test_source_review_chain_artifact_keeps_update_plan_blocked(self) -> None:
        review = load_artifact("sd_source_review_chain_smoke_blocked.json")

        self.assertFalse(review["passed"])
        self.assertTrue(review["checks"]["source_scope_audit_passed"])
        self.assertFalse(review["checks"]["approval_review_passed"])
        self.assertFalse(review["checks"]["update_plan_ready"])
        self.assertTrue(review["checks"]["registry_not_modified"])
        self.assertIn(
            "Complete source usage review before source approval.",
            review["required_reviews"],
        )

    def test_synthetic_source_review_example_is_not_real_approval(self) -> None:
        review = load_artifact("source_review_approval_reviewed_example_review.json")

        self.assertTrue(review["ready_for_registry_update"])
        self.assertEqual(
            review["scope"]["source_id"],
            "synthetic_reviewed_source_example",
        )
        self.assertEqual(review["required_reviews"], [])
        self.assertEqual(review["issue_counts"]["error"], 0)
        self.assertTrue(review["registry_update_hint"]["can_update_registry"])
        self.assertIn(
            "Does not modify the source registry.",
            review["non_goals"],
        )

    def test_synthetic_source_review_example_update_plan_is_blocked(self) -> None:
        plan = load_artifact(
            "source_review_approval_reviewed_example_update_plan_blocked.json"
        )

        self.assertFalse(plan["ready_for_registry_patch"])
        self.assertEqual(plan["source_id"], "synthetic_reviewed_source_example")
        self.assertEqual(plan["planned_updates"], {})
        self.assertEqual(plan["issue_counts"]["error"], 1)
        self.assertEqual(plan["issues"][0]["code"], "source_not_found")
        self.assertIn("Does not modify sources.json.", plan["non_goals"])

    def test_synthetic_source_review_chain_example_passes_no_write(self) -> None:
        report = load_artifact("source_review_chain_smoke_reviewed_example.json")

        self.assertTrue(report["passed"])
        self.assertTrue(report["checks"]["source_scope_audit_passed"])
        self.assertTrue(report["checks"]["approval_review_passed"])
        self.assertTrue(report["checks"]["update_plan_ready"])
        self.assertTrue(report["checks"]["registry_not_modified"])
        self.assertEqual(report["required_reviews"], [])
        update_plan = report["reviews"]["update_plan"]
        self.assertTrue(update_plan["ready_for_registry_patch"])
        self.assertEqual(update_plan["source_id"], "synthetic_reviewed_source_example")
        self.assertEqual(
            update_plan["planned_updates"]["review_status"],
            {"current": "reviewed", "target": "approved", "will_update": True},
        )
        self.assertIn("Does not modify sources.json.", report["non_goals"])

    def test_synthetic_registry_patch_chain_example_passes_no_write(self) -> None:
        approval = load_artifact(
            "source_registry_patch_approval_reviewed_example_review.json"
        )
        preview = load_artifact("source_registry_patch_preview_reviewed_example.json")
        report = load_artifact(
            "source_registry_patch_chain_smoke_reviewed_example.json"
        )

        self.assertTrue(approval["ready_for_registry_patch_execution"])
        self.assertTrue(preview["ready_for_registry_patch_preview"])
        self.assertEqual(preview["changes_applied"], ["review_status"])
        self.assertEqual(preview["patched_source"]["review_status"], "approved")
        self.assertTrue(report["passed"])
        self.assertTrue(report["checks"]["patch_approval_ready"])
        self.assertTrue(report["checks"]["patch_preview_ready"])
        self.assertTrue(report["checks"]["registry_not_modified"])
        self.assertEqual(report["required_reviews"], [])
        self.assertIn("Does not modify sources.json.", report["non_goals"])

    def test_synthetic_snapshot_planning_example_is_ready_no_write(self) -> None:
        review = load_artifact("source_snapshot_planning_approved_example.json")

        self.assertTrue(review["ready_for_snapshot_planning"])
        self.assertEqual(review["blockers"], [])
        self.assertEqual(review["required_reviews"], [])
        self.assertEqual(
            review["source_summary"]["matching_source_ids"],
            ["synthetic_reviewed_source_example"],
        )
        self.assertEqual(review["source_summary"]["review_statuses"], ["approved"])
        self.assertTrue(review["source_summary"]["has_approved_source"])
        self.assertTrue(review["source_summary"]["has_requested_year"])
        self.assertIn("Does not create raw snapshots.", review["non_goals"])

    def test_synthetic_intake_review_example_is_ready_no_write(self) -> None:
        review = load_artifact("source_intake_review_approved_example.json")

        self.assertTrue(review["ready_for_snapshot"])
        self.assertEqual(review["issue_counts"], {"error": 0, "warning": 0, "info": 0})
        self.assertEqual(review["required_reviews"], [])
        self.assertEqual(
            review["scope"],
            {
                "source_id": "synthetic_reviewed_source_example",
                "dataset": "admission_scores",
                "province": "示例省",
                "published_year": 2025,
            },
        )
        planning = review["snapshot_planning_review"]
        self.assertTrue(planning["ready_for_snapshot_planning"])
        self.assertTrue(planning["source_summary"]["has_approved_source"])
        self.assertIn("Does not create raw snapshots.", review["non_goals"])

    def test_synthetic_source_to_intake_chain_example_passes_no_write(self) -> None:
        report = load_artifact("source_to_intake_chain_smoke_approved_example.json")

        self.assertTrue(report["passed"])
        self.assertTrue(report["checks"]["source_review_chain_passed"])
        self.assertTrue(report["checks"]["source_review_update_plan_ready"])
        self.assertTrue(report["checks"]["patch_chain_passed"])
        self.assertTrue(report["checks"]["patch_chain_registry_not_modified"])
        self.assertTrue(report["checks"]["snapshot_planning_ready"])
        self.assertTrue(report["checks"]["intake_ready"])
        self.assertTrue(report["checks"]["source_id_consistent"])
        self.assertTrue(report["checks"]["scope_consistent"])
        self.assertEqual(report["required_reviews"], [])
        self.assertIn("Does not create raw snapshots.", report["non_goals"])

    def test_synthetic_parser_and_quality_examples_are_source_bound(self) -> None:
        parser_smoke = load_artifact(
            "source_parser_rows_bundle_smoke_approved_example.json"
        )
        quality_smoke = load_artifact("source_quality_smoke_approved_example.json")

        self.assertTrue(parser_smoke["ready_for_parser"])
        self.assertEqual(
            parser_smoke["scope"]["source_id"],
            "synthetic_reviewed_source_example",
        )
        self.assertEqual(
            parser_smoke["scope"]["snapshot_id"],
            "synthetic_snapshot_2025_001",
        )
        candidate_source = parser_smoke["candidate_previews"][0]["source"]
        self.assertEqual(candidate_source["dataset"], "admission_scores")
        self.assertEqual(candidate_source["year"], 2025)
        self.assertEqual(candidate_source["confidence"], 0.95)
        self.assertTrue(quality_smoke["ready_for_quality_gate"])
        self.assertEqual(
            quality_smoke["source_metadata"]["source_ids"],
            ["synthetic_reviewed_source_example"],
        )
        self.assertEqual(
            quality_smoke["source_metadata"]["snapshot_ids"],
            ["synthetic_snapshot_2025_001"],
        )
        self.assertEqual(quality_smoke["coverage"]["missing_expected_provinces"], [])
        self.assertEqual(quality_smoke["coverage"]["missing_expected_years"], [])

    def test_synthetic_source_to_quality_chain_passes_no_write(self) -> None:
        report = load_artifact("source_to_quality_chain_smoke_approved_example.json")

        self.assertTrue(report["passed"])
        self.assertTrue(report["checks"]["source_to_intake_chain_passed"])
        self.assertTrue(report["checks"]["parser_smoke_ready"])
        self.assertTrue(report["checks"]["quality_smoke_ready"])
        self.assertTrue(report["checks"]["source_scope_matches_parser"])
        self.assertTrue(report["checks"]["parser_scope_matches_quality"])
        self.assertTrue(report["checks"]["quality_source_metadata_matches_parser"])
        self.assertTrue(report["checks"]["candidate_year_matches_source_scope"])
        self.assertEqual(report["required_reviews"], [])
        self.assertEqual(
            report["scope"]["source_id"],
            "synthetic_reviewed_source_example",
        )
        self.assertEqual(report["scope"]["snapshot_id"], "synthetic_snapshot_2025_001")
        self.assertIn("Does not execute canonical loader.", report["non_goals"])

    def test_source_review_human_checklist_keeps_source_review_blocked(self) -> None:
        checklist = load_artifact("sd_source_review_human_checklist_blocked.json")

        self.assertFalse(checklist["ready_for_source_review_approval"])
        self.assertEqual(checklist["issue_counts"]["error"], 4)
        statuses = {
            item["id"]: item["status"]
            for item in checklist["checklist"]
        }
        self.assertEqual(statuses["official_page_verified"], "verified")
        self.assertEqual(statuses["attachment_or_table_verified"], "verified")
        self.assertEqual(statuses["data_category_confirmed"], "confirmed")
        self.assertEqual(statuses["published_year_confirmed"], "confirmed")
        self.assertEqual(statuses["license_or_citation_reviewed"], "pending")
        self.assertEqual(statuses["allow_flag_confirmed"], "pending")
        self.assertTrue(
            checklist["candidate_evidence_summary"]["has_dataset_page_url"],
        )
        self.assertTrue(
            checklist["candidate_evidence_summary"]["has_attachment_url"],
        )
        self.assertIn(
            "Complete license or citation review.",
            checklist["required_reviews"],
        )

    def test_source_review_handoff_keeps_manual_actions_blocked(self) -> None:
        handoff = load_artifact("sd_source_review_handoff_blocked.json")

        self.assertFalse(handoff["ready_for_source_review_handoff"])
        self.assertFalse(handoff["current_state"]["source_review_ready"])
        self.assertFalse(handoff["current_state"]["ready_for_real_snapshot"])
        self.assertTrue(handoff["current_state"]["registry_not_modified"])
        self.assertEqual(handoff["issue_counts"]["error"], 6)
        action_statuses = {
            item["id"]: item["status"]
            for item in handoff["next_manual_actions"]
        }
        self.assertEqual(action_statuses["verify_official_page"], "verified")
        self.assertEqual(
            action_statuses["verify_attachment_or_table"],
            "verified",
        )
        self.assertEqual(action_statuses["confirm_dataset_scope"], "confirmed")
        self.assertEqual(action_statuses["review_usage_and_citation"], "pending")
        self.assertIn(
            "Complete source review handoff manual actions.",
            handoff["required_reviews"],
        )
        self.assertIn(
            "Does not fetch remote source pages or download attachments.",
            handoff["non_goals"],
        )

    def test_registry_update_plan_artifact_keeps_patch_blocked(self) -> None:
        plan = load_artifact("sd_source_registry_update_plan_blocked.json")

        self.assertFalse(plan["ready_for_registry_patch"])
        self.assertEqual(plan["issue_counts"]["error"], 1)
        self.assertEqual(plan["issues"][0]["code"], "approval_review_not_ready")
        self.assertTrue(
            plan["planned_updates"]["review_status"]["will_update"],
        )
        self.assertIn("Does not modify sources.json.", plan["non_goals"])

    def test_registry_patch_approval_artifact_keeps_patch_blocked(self) -> None:
        review = load_artifact("sd_source_registry_patch_approval_blocked.json")

        self.assertFalse(review["ready_for_registry_patch_execution"])
        self.assertEqual(review["issue_counts"]["error"], 5)
        issue_codes = {issue["code"] for issue in review["issues"]}
        self.assertIn("update_plan_not_ready", issue_codes)
        self.assertIn("source_registry_patch_not_allowed", issue_codes)
        self.assertIn(
            "Resolve source registry update plan blockers.",
            review["required_reviews"],
        )
        self.assertIn("Does not modify sources.json.", review["non_goals"])

    def test_registry_patch_preview_artifact_keeps_patch_preview_blocked(self) -> None:
        preview = load_artifact("sd_source_registry_patch_preview_blocked.json")

        self.assertFalse(preview["ready_for_registry_patch_preview"])
        self.assertEqual(preview["issue_counts"]["error"], 2)
        self.assertEqual(preview["changes_applied"], [])
        self.assertEqual(preview["patched_source"], {})
        self.assertIn(
            "Pass source registry patch approval review.",
            preview["required_reviews"],
        )
        self.assertIn("Does not modify sources.json.", preview["non_goals"])

    def test_registry_patch_chain_artifact_keeps_patch_chain_blocked(self) -> None:
        report = load_artifact("sd_source_registry_patch_chain_smoke_blocked.json")

        self.assertFalse(report["checks"]["patch_approval_ready"])
        self.assertFalse(report["checks"]["patch_preview_ready"])
        self.assertTrue(report["checks"]["registry_not_modified"])
        self.assertEqual(report["issue_counts"]["error"], 2)
        self.assertFalse(
            report["reviews"]["patch_preview"][
                "ready_for_registry_patch_preview"
            ]
        )
        self.assertIn(
            "Resolve source registry patch preview blockers.",
            report["required_reviews"],
        )


if __name__ == "__main__":
    unittest.main()
