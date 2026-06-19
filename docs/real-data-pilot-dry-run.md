# 真实数据 Pilot Dry Run

本文档说明如何用手工审核的小样本跑通真实数据入库前检查。

当前入口只做本地 dry-run：

- 不爬取远程网站
- 不写入数据库
- 不修改 seed 数据
- 不调用 canonical loader

## 适用场景

在山东或河南单省试点时，先把少量官方/授权来源数据人工整理成
normalized rows，再用 dry-run 验证：

```text
source registry -> snapshot manifest -> manual rows -> parser -> quality gate -> audit report
```

只有 audit report 里 `load_ready=true`、`blockers=[]`，且
`coverage.missing_expected_provinces=[]`、
`coverage.missing_expected_years=[]`，后续才可以进入 loader 审批。

整理真实官方样本前，先按
`docs/real-data-pilot-review-checklist.md` 完成来源、快照、字段和
loader 审批项复核。

## Bundle 格式

dry-run CLI 接收一个 JSON bundle：

```json
{
  "source": {
    "source_id": "sd_exam_authority",
    "name": "Shandong Education Admissions Examination Institute",
    "source_type": "provincial_exam_authority",
    "homepage_url": "https://www.sdzk.cn/default.aspx",
    "data_categories": ["admission_scores"],
    "coverage": {
      "provinces": ["山东"],
      "years": [2025]
    },
    "trust_score": 1.0,
    "update_frequency": "annual",
    "collection_method": "manual_download",
    "license_note": "Official public source; review citation requirements."
  },
  "manifest": {
    "snapshot_id": "sd_pilot_2025_001",
    "source_id": "sd_exam_authority",
    "dataset": "admission_scores",
    "source_url": "https://example.gov.cn/manual-sample.csv",
    "published_year": 2025,
    "collected_at": "2026-06-06T00:00:00Z",
    "collector": "manual",
    "collector_version": "0.1.0",
    "files": [
      {
        "path": "files/manual-sample.csv",
        "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "content_type": "text/csv"
      }
    ],
    "license_note": "Test fixture only."
  },
  "quality_config": {
    "current_year": 2026,
    "expected_provinces": ["山东"],
    "expected_years": [2025],
    "require_review_metadata": true
  },
  "rows": [
    {
      "school_name": "山东大学",
      "major_name": null,
      "province": "山东",
      "year": 2025,
      "batch": "本科批",
      "subject_type": "综合",
      "min_score": 620,
      "min_rank": 12000,
      "source_record_ref": "manual_row=1",
      "review": {
        "extracted_by": "example-extractor",
        "reviewed_by": "example-reviewer",
        "reviewed_at": "2026-06-07",
        "notes": "Synthetic example row; replace with official evidence."
      }
    }
  ]
}
```

## 运行命令

先确保使用已安装项目依赖的 Python 环境，例如项目根目录执行过：

```bash
pip install -e ".[dev]"
```

```bash
python -m backend.data_pipeline.pilots.cli path/to/pilot_bundle.json
```

CLI 会把 audit report 输出到 stdout。

需要归档审计报告时，可加 `--audit-output`：

```bash
python -m backend.data_pipeline.pilots.cli \
  --audit-output artifacts/real_data/sd_pilot_2025_audit.json \
  path/to/pilot_bundle.json
```

审计通过并满足 `review_status=ready_for_loader_review` 后，可以同时生成
loader 审批包：

```bash
python -m backend.data_pipeline.pilots.cli \
  --audit-output artifacts/real_data/sd_pilot_2025_audit.json \
  --approval-output artifacts/real_data/sd_pilot_2025_loader_approval.json \
  path/to/pilot_bundle.json
```

如果 audit 是 `blocked` 或 `needs_warning_review`，`--approval-output` 不会
写出审批包。

如果已经有本地 raw snapshot 目录，使用 `--snapshot-dir` 让 CLI 从目录里的
`manifest.json` 读取快照元数据并校验文件 checksum。此时 bundle 可以只包含
`source`、`quality_config` 和 `rows`：

```bash
python -m backend.data_pipeline.pilots.cli \
  --snapshot-dir data/raw/sd_exam_authority/admission_scores/2025/sd_pilot_2025_001 \
  path/to/pilot_rows_bundle.json
```

仓库内提供了一个 snapshot-dir 示例，可同时生成 audit 和 approval artifact：

```bash
python -m backend.data_pipeline.pilots.cli \
  --snapshot-dir examples/real_data/snapshots/sd_pilot_2025_001 \
  --audit-output artifacts/real_data/sd_snapshot_pilot_audit.json \
  --approval-output artifacts/real_data/sd_snapshot_pilot_approval.json \
  examples/real_data/sd_snapshot_pilot_rows.json
```

如果要把 source audit、intake review、dry-run audit、loader approval 和输入
路径汇总成一个 review manifest，可继续执行：

```bash
python -m backend.data_pipeline.pilots.artifacts_cli \
  --source-audit artifacts/real_data/sd_source_audit.json \
  --intake-review artifacts/real_data/sd_intake_review.json \
  --dry-run-audit artifacts/real_data/sd_snapshot_pilot_audit.json \
  --loader-approval artifacts/real_data/sd_snapshot_pilot_approval.json \
  --rows-bundle examples/real_data/sd_snapshot_pilot_rows.json \
  --snapshot-dir examples/real_data/snapshots/sd_pilot_2025_001 \
  --manifest-output artifacts/real_data/sd_pilot_artifact_manifest.json
```

仓库内提供了一个可直接 dry-run 的示例 bundle：

```bash
python -m backend.data_pipeline.pilots.cli examples/real_data/sd_pilot_bundle.json
python -m backend.data_pipeline.pilots.cli examples/real_data/sd_plan_pilot_bundle.json
```

这些示例只用于验证流程形状，不代表已审核官方真实数据。仓库还提供
`examples/real_data/artifacts/*.json` 作为静态证据链示例，用于检查
source audit、intake review、dry-run audit、loader approval 和 artifact
manifest 的 JSON 形状；真实 pilot 必须重新生成并人工复核这些 artifact。

## Exit Code

| Exit code | 含义 |
|-----------|------|
| 0 | dry-run 通过，`load_ready=true` |
| 1 | bundle 可解析，但 quality/source gate 阻断 |
| 2 | JSON 或 bundle 契约错误 |

## Audit Report 关键字段

| 字段 | 说明 |
|------|------|
| `snapshot_id` | 原始快照 ID |
| `source_id` | 数据源 ID |
| `dataset` | 数据集类型 |
| `candidate_count` | parser 产出的候选行数 |
| `passed` | 是否无阻断 |
| `load_ready` | 是否允许进入 loader 审批 |
| `blockers` | 阻断原因，如 `quality_error:value_out_of_range` |
| `source_validation_issues` | source 与 manifest 不一致原因 |
| `snapshot_file_issues` | manifest 文件缺失或 checksum 不一致原因 |
| `coverage` | 省份、年份、实体类型覆盖统计 |
| `issue_counts` | quality gate issue 计数 |
| `review_status` | `ready_for_loader_review` / `needs_warning_review` / `blocked` |
| `review_notes` | 给人工审批看的阻断或 warning 摘要 |
| `issues` | quality gate 详细 issue |

## 下一步审批点

如果 `load_ready=true`，下一步仍需单独审批才可以：

- 写入 raw snapshot 目录
- 运行 canonical loader
- 写入应用数据库
- 刷新 RAG 或 Agent 可见数据

审批包应引用 `--audit-output` 生成的审计报告文件，并说明 `blockers`、
`snapshot_file_issues`、`source_validation_issues`、`issue_counts`、
`review_status` 和 `review_notes` 的状态。

如果还生成了 artifact manifest，也应一并引用。它能把 source audit、
dry-run audit、loader approval、rows bundle 和 snapshot dir 串成一份证据清单。
进入 loader 前，manifest 里的 `artifact_path_issues`、
`intake_review_issues`、`artifact_scope_issues` 和
`loader_approval_issues` 必须都为空。
manifest 还会输出 `loader_handoff`，其中会标明推荐的 loader 入口、
artifact manifest ready 状态，以及仍需单独审批 loader run command。

如果 `quality_config.expected_provinces` 或 `expected_years` 声明了期望覆盖，
dry-run 会把缺失省份和年份转成阻断项，例如
`coverage_missing:province:河南` 或 `coverage_missing:year:2024`。这些项必须
通过补齐样本或调整本次试点范围后重跑 dry-run 消除。

进入 canonical loader 前，`review_status` 必须是
`ready_for_loader_review`。如果是 `needs_warning_review`，即使
`load_ready=true`，也必须先完成人工复核并重新生成审计报告或单独审批
复核结论。

代码层可以用 `build_loader_approval_packet(...)` 生成标准审批包。CLI 的
`--approval-output` 使用同一套规则。该函数只生成复核 JSON，不写数据库：

```python
from backend.data_pipeline.loaders import build_loader_approval_packet

packet = build_loader_approval_packet(
    audit=audit,
    candidates=candidates,
    parser_name="ManualSampleParser",
    parser_version="0.1.0",
).to_review_dict()
```

## 受控 Loader 交接

代码层进入 canonical loader 前，应使用带审计门禁的入口：

```python
from backend.data_pipeline.loaders import load_candidates_after_artifact_manifest

load_candidates_after_artifact_manifest(
    db,
    candidates,
    artifact_manifest,
    parser_name="ManualSampleParser",
    parser_version="0.1.0",
)
```

该入口会先检查 `artifact_manifest["ready_for_loader_execution"]`。如果 source
audit、dry-run、loader approval、路径或 scope 证据包没有全部通过，会抛出
`PilotLoadNotReadyError`，并保留 `required_reviews` 或 artifact issues 供人工
复核。`load_candidates_after_audit(...)` 仍可用于低层 dry-run guard，但真实
pilot 写入前应优先使用完整 artifact manifest guard。
artifact manifest 的 `loader_handoff.recommended_entrypoint` 应与这个入口保持
一致；`requires_separate_loader_run_command=true` 表示 manifest ready 后仍要
单独审批具体写库命令。

如果样本已经整理成 raw snapshot 目录，代码层应优先使用
`run_manual_pilot_snapshot_dir(...)` 或
`build_load_ready_candidates_snapshot_dir(...)`。这两个入口会先通过
`ManualSnapshotCollector` 校验 `manifest.json` 和原始文件 checksum，
并把文件问题写入 `snapshot_file_issues` 与 `snapshot_file:*` blockers。
