"""Checksum helpers for local raw snapshot files."""

from hashlib import sha256
from pathlib import Path

from backend.data_pipeline.raw_store.manifest import RawSnapshotManifest


def compute_sha256(path: Path | str) -> str:
    """Compute a SHA-256 checksum for a local file."""
    file_path = Path(path)
    digest = sha256()

    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def verify_manifest_files(base_dir: Path | str, manifest: RawSnapshotManifest) -> list[str]:
    """Return checksum or existence problems for files referenced by a manifest."""
    root = Path(base_dir)
    issues: list[str] = []

    for file_entry in manifest.files:
        file_path = root / file_entry.path
        if not file_path.exists():
            issues.append(f"missing file: {file_entry.path}")
            continue
        actual = compute_sha256(file_path)
        if actual != file_entry.sha256:
            issues.append(f"checksum mismatch: {file_entry.path}")

    return issues
