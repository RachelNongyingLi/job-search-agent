#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import re
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path


PROJECT_SLUG = "apply-less-fit-more"

INCLUDE_PATTERNS = (
    "README.md",
    "AGENTS.md",
    "CLAUDE.md",
    "pyproject.toml",
    "docs/**",
    "examples/**",
    "profiles/sample_candidate.json",
    "scripts/build_release.py",
    "src/**",
    "tests/**",
    "web/**",
)

REQUIRED_FILES = (
    "README.md",
    "AGENTS.md",
    "CLAUDE.md",
    "pyproject.toml",
    "profiles/sample_candidate.json",
    "web/index.html",
)

IGNORED_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "venv",
}

FORBIDDEN_PATH_PATTERNS = (
    ".env",
    ".env.*",
    "*.local.json",
    "*.pdf",
    "*.docx",
    "*.xlsx",
    "*.xls",
    "CLAUDE.local.md",
    "applications.csv",
    "data/private/**",
    "inputs/jobs/**",
    "memory.local.json",
    "outputs/**",
    "private_resumes/**",
    "profiles/*.local.json",
)

SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"),
    re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bghp_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
)


@dataclass(frozen=True)
class ReleaseBuild:
    archive_path: Path
    sha256_path: Path
    files: tuple[str, ...]
    digest: str


class ReleaseAuditError(RuntimeError):
    def __init__(self, issues: list[str]):
        self.issues = issues
        super().__init__("\n".join(issues))


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[1]


def read_version(repo_root: Path) -> str:
    pyproject = repo_root / "pyproject.toml"
    match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject.read_text(encoding="utf-8"), re.MULTILINE)
    if not match:
        raise ReleaseAuditError(["Could not read project version from pyproject.toml"])
    return match.group(1)


def matches_pattern(path: str, pattern: str) -> bool:
    if pattern.endswith("/**"):
        prefix = pattern[:-3]
        return path == prefix or path.startswith(prefix + "/")
    return fnmatch.fnmatchcase(path, pattern)


def is_included(path: str) -> bool:
    return any(matches_pattern(path, pattern) for pattern in INCLUDE_PATTERNS)


def is_ignored(path: Path) -> bool:
    return any(part in IGNORED_PARTS for part in path.parts) or path.name == ".DS_Store" or path.suffix == ".pyc"


def audit_release_path(rel_path: str) -> list[str]:
    issues: list[str] = []
    for pattern in FORBIDDEN_PATH_PATTERNS:
        if matches_pattern(rel_path, pattern):
            issues.append(f"Forbidden release path matched {pattern!r}: {rel_path}")
    return issues


def audit_file_content(path: Path, rel_path: str) -> list[str]:
    if path.stat().st_size > 2_000_000:
        return []
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    issues = []
    for pattern in SECRET_PATTERNS:
        if pattern.search(content):
            issues.append(f"Potential secret matched {pattern.pattern!r}: {rel_path}")
    return issues


def collect_release_files(repo_root: Path) -> tuple[list[Path], list[str]]:
    files: list[Path] = []
    issues: list[str] = []
    for path in sorted(repo_root.rglob("*")):
        if not path.is_file():
            continue
        rel_path = path.relative_to(repo_root).as_posix()
        if is_ignored(Path(rel_path)):
            continue
        if not is_included(rel_path):
            continue
        issues.extend(audit_release_path(rel_path))
        issues.extend(audit_file_content(path, rel_path))
        files.append(path)

    included = {path.relative_to(repo_root).as_posix() for path in files}
    for required in REQUIRED_FILES:
        if required not in included:
            issues.append(f"Required release file is missing: {required}")
    return files, issues


def audit_zip_names(zip_path: Path) -> list[str]:
    issues: list[str] = []
    with zipfile.ZipFile(zip_path, "r") as archive:
        for name in archive.namelist():
            parts = name.split("/", 1)
            rel_path = parts[1] if len(parts) == 2 else parts[0]
            issues.extend(audit_release_path(rel_path))
    return issues


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_release(repo_root: Path, out_dir: Path, version: str | None = None, dry_run: bool = False) -> ReleaseBuild:
    repo_root = repo_root.resolve()
    version = version or read_version(repo_root)
    release_root = f"{PROJECT_SLUG}-v{version}"
    archive_path = out_dir / f"{release_root}.zip"
    sha256_path = archive_path.with_suffix(".zip.sha256")

    files, issues = collect_release_files(repo_root)
    if issues:
        raise ReleaseAuditError(issues)

    rel_files = tuple(path.relative_to(repo_root).as_posix() for path in files)
    if dry_run:
        return ReleaseBuild(archive_path=archive_path, sha256_path=sha256_path, files=rel_files, digest="")

    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            rel_path = path.relative_to(repo_root).as_posix()
            archive.write(path, f"{release_root}/{rel_path}")

    zip_issues = audit_zip_names(archive_path)
    if zip_issues:
        archive_path.unlink(missing_ok=True)
        raise ReleaseAuditError(zip_issues)

    digest = sha256_file(archive_path)
    sha256_path.write_text(f"{digest}  {archive_path.name}\n", encoding="utf-8")
    return ReleaseBuild(archive_path=archive_path, sha256_path=sha256_path, files=rel_files, digest=digest)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a privacy-audited release zip.")
    parser.add_argument("--repo-root", default=str(repo_root_from_script()), help="Repository root to package.")
    parser.add_argument("--out-dir", default="dist/releases", help="Directory for release artifacts.")
    parser.add_argument("--version", default=None, help="Release version. Defaults to pyproject.toml version.")
    parser.add_argument("--dry-run", action="store_true", help="Audit and list files without writing the zip.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = repo_root / out_dir
    try:
        build = build_release(repo_root, out_dir, version=args.version, dry_run=args.dry_run)
    except ReleaseAuditError as exc:
        print("Release audit failed:", file=sys.stderr)
        for issue in exc.issues:
            print(f"- {issue}", file=sys.stderr)
        return 1

    print(f"Release files: {len(build.files)}")
    for rel_path in build.files:
        print(f"  {rel_path}")
    if args.dry_run:
        print(f"Dry run passed. Would write: {build.archive_path}")
    else:
        print(f"Wrote: {build.archive_path}")
        print(f"Wrote: {build.sha256_path}")
        print(f"SHA256: {build.digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
