#!/usr/bin/env python

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from importlib.metadata import PackageNotFoundError, distribution
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATCH_PATH = ROOT / "patches" 
_DIFF_HEADER = re.compile(r"^diff --git a/(\S+) b/(\S+)$", re.MULTILINE)
_FILE_LINE = re.compile(r"^(?:--- a|\+\+\+ b)/([^\t\n]+)", re.MULTILINE)
_NUMBERED = re.compile(r"^\d{4}-")

class PatchError(Exception):
    pass

def apply(root: Path, patch: Path, *flags: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "apply", "-p1", *flags, str(patch)],
        cwd=root,
        env={**os.environ, "GIT_DIR": os.devnull},
        capture_output=True,
        text=True,
        check=False,
    )

def _touched_paths(patches: list[Path]) -> set[str]:
    paths: set[str] = set()
    for patch in patches:
        text = patch.read_text(encoding="utf-8", errors="surrogateescape")
        for old, new in _DIFF_HEADER.findall(text):
            paths.update((old, new))
        paths.update(_FILE_LINE.findall(text))
    return paths


def _applied_count(root: Path, patches: list[Path]) -> int:
    with tempfile.TemporaryDirectory() as temp:
        scratch = Path(temp)
        for rel in _touched_paths(patches):
            if (root / rel).is_file():
                (scratch / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(root / rel, scratch / rel)
        applied = 0
        for index in reversed(range(len(patches))):
            reverses = apply(scratch, patches[index], "--reverse").returncode == 0
            if not applied and reverses:
                applied = index + 1
            elif applied and not reverses:
                raise PatchError(
                    f"{patches[index].name} is missing from a tree that already holds the later "
                    f"{patches[applied - 1].name}; reinstall the package and run again"
                )
        return applied

def _install_root(dist_name: str) -> tuple[Path, str]:
    try:
        dist = distribution(dist_name)
    except PackageNotFoundError as e:
        raise PatchError(f"{dist_name} is not installed") from e
    root = dist.locate_file("")
    return Path(str(root)), dist.version

def _series(directory: Path) -> list[Path]:
    series = directory / "series"
    if series.is_file():
        names = [ln.strip() for ln in series.read_text().splitlines()]
        names = [n for n in names if n and not n.startswith("#")]
        if not names:
            raise PatchError(f"{series} lists no patches")
        missing = [n for n in names if not (directory / n).is_file()]
        if missing:
            raise PatchError(f"{series} names files that do not exist: {', '.join(missing)}")
        return [directory / n for n in names]

    files = sorted(directory.glob("*.patch"))
    if not files:
        raise PatchError(f"{directory} holds no .patch files")
    unnumbered = [f.name for f in files if not _NUMBERED.match(f.name)]
    if unnumbered:
        raise PatchError(
            f"{directory}: without a series file the apply order comes from a NNNN- prefix, "
            f"which these lack: {', '.join(unnumbered)}"
        )
    return files
    

def process(dist_dir: Path, *, check_only: bool, allow_unpatched: bool) -> tuple[int, int]:
    dist_name = dist_dir.name
    root, installed = _install_root(dist_name)
    version_dir = dist_dir / installed

    if not version_dir.is_dir():
        available = ", ".join(sorted(d.name for d in dist_dir.iterdir() if d.is_dir())) or "none"
        message = (
            f"{dist_name} {installed} is installed, but patches exist only for: {available}.\n"
            f"  An upgrade past a patch set drops those changes silently. Write "
            f"patches/{dist_name}/{installed}/, or pass --allow-unpatched."
        )
        if allow_unpatched:
            print(f"! {message}")
            return (0, 0)
        raise PatchError(message)
    
    patches = _series(version_dir)
    print(f"{dist_name} {installed} — {len(patches)} patch(es), root {root}")

    already = _applied_count(root, patches)
    applied = missing = 0

    for index, patch in enumerate(patches):
        if index < already:
            print(f" = {patch.name} already applied")
            continue
        if check_only:
            print(f" {patch.name} not found")
            missing += 1
            continue
        result = apply(root, patch)
        if result.returncode != 0:
            raise PatchError(
                f"{patch.name} does not apply to {dist_name} {installed}:\n{(result.stderr or result.stdout).rstrip()}"
            )
        print(f"  + {patch.name}")
        applied += 1
    return (applied, missing)

def _patch_sets(package: str | None) -> list[Path]:
    if not PATCH_PATH.is_dir():
        return []
    dirs = sorted(d for d in PATCH_PATH.iterdir() if d.is_dir())
    return [d for d in dirs if package is None or d.name == package]

def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--package", help="only this distribution (default: every set under patches/)")
    parser.add_argument(
        "--check", action="store_true", help="report state, write nothing; exit 1 if any patch is missing"
    )
    parser.add_argument(
        "--allow-unpatched",
        action="store_true",
        help="warn instead of failing when the installed version has no patch set",
    )
    
    args = parser.parse_args()

    sets = _patch_sets(args.package)
    if not sets:
        target = f" for {args.package}" if args.package else ""
        print(f"no patch sets{target} under {PATCH_PATH}")
        return 0
    
    total_applied = total_missing = 0
    for dist_dir in sets:
        try:
            applied, missing = process(dist_dir, check_only=args.check, allow_unpatched=args.allow_unpatched)
        except PatchError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        total_applied += applied
        total_missing += missing

    if total_missing:
        print(f"\n{total_missing} patch(es) not applied — run without --check")
        return 1
    if args.check:
        print("\nall patches applied")
    else:
        print(
            f"\napplied {total_applied} patch(es)"
            if total_applied
            else "\nnothing to do — every patch was already applied"
        )
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
