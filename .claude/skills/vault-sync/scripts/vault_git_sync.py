#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vault 변경을 자동 커밋하고 원격 저장소로 best-effort push 한다.

검사 항목
  - memory 폴더를 .memory-mirror 로 미러 (복구 수단이 없던 유일한 계층)
  - 첨부 PNG 를 256색으로 양자화 (TC 스크린샷 1장 2.8MB → 0.6MB)
  - 변경이 없으면 커밋과 push 생략
  - 변경 파일 전부를 정해진 메시지 형식으로 커밋
  - 비대화형 push 실패 시 로컬 커밋을 보존하고 경고

사용법:
    python vault_git_sync.py [--vault vault] [--date YYYY-MM-DD] [--no-push]
                             [--mirror-memory DIR] [--quantize-attachments]

종료 코드: 0 정상(변경 없음·push 실패 포함) / 1 git·인자 오류
"""

import argparse
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass


def run_git(vault: Path, *args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    return subprocess.run(
        ["git", "-C", str(vault), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )


def first_error(result: subprocess.CompletedProcess) -> str:
    lines = (result.stderr or result.stdout).strip().splitlines()
    return lines[0] if lines else f"git exit {result.returncode}"


def mirror_memory(source: Path, destination: Path) -> tuple[int, int, int]:
    """memory 폴더를 destination 에 완전 미러하고 파일별 결과 수를 반환한다."""
    copied = 0
    deleted = 0
    unchanged = 0
    destination.mkdir(parents=True, exist_ok=True)
    source_files = {
        path.relative_to(source): path
        for path in source.rglob("*")
        if path.is_file()
    }
    destination_files = {
        path.relative_to(destination): path
        for path in destination.rglob("*")
        if path.is_file()
    }
    for relative, source_file in sorted(source_files.items()):
        destination_file = destination / relative
        if destination_file.is_file() and source_file.read_bytes() == destination_file.read_bytes():
            unchanged += 1
            continue
        destination_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, destination_file)
        copied += 1
    for relative, destination_file in sorted(destination_files.items(), reverse=True):
        if relative not in source_files:
            destination_file.unlink()
            deleted += 1
    for directory in sorted(
        (path for path in destination.rglob("*") if path.is_dir()),
        key=lambda path: len(path.parts),
        reverse=True,
    ):
        try:
            directory.rmdir()
        except OSError:
            pass
    return copied, deleted, unchanged


def quantize_attachments(root: Path) -> tuple[int, int, int] | None:
    """첨부 PNG 를 256색으로 양자화하고 변환·동일·절감 바이트를 반환한다."""
    try:
        from PIL import Image
    except ImportError:
        print("[vault_git_sync] Pillow 없음 — 양자화 건너뜀")
        return None

    converted = 0
    unchanged = 0
    saved_bytes = 0
    for path in sorted(root.rglob("*.png")) if root.is_dir() else []:
        with Image.open(path) as image:
            if image.mode == "P":
                unchanged += 1
                continue
            before = path.stat().st_size
            quantized = image.convert("RGB").quantize(
                colors=256,
                method=Image.Quantize.FASTOCTREE,
                dither=Image.Dither.NONE,
            )
            quantized.save(path, "PNG", optimize=True)
            saved_bytes += before - path.stat().st_size
            converted += 1
    return converted, unchanged, saved_bytes


def main() -> int:
    parser = argparse.ArgumentParser(description="vault git 자동 동기화")
    parser.add_argument("--vault", default="vault")
    parser.add_argument("--date", default=None, help="커밋 날짜 YYYY-MM-DD")
    parser.add_argument("--no-push", action="store_true")
    parser.add_argument("--mirror-memory", default=None, metavar="DIR")
    parser.add_argument("--quantize-attachments", action="store_true")
    args = parser.parse_args()

    vault = Path(args.vault).resolve()
    if not (vault / ".git").exists():
        print(f"vault 에 git 저장소가 없다: {vault}", file=sys.stderr)
        return 1
    now = datetime.now()
    if args.date:
        try:
            day = datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            print("--date 는 YYYY-MM-DD 형식이어야 한다", file=sys.stderr)
            return 1
        now = datetime.combine(day, now.time())

    mirror_result = None
    if args.mirror_memory:
        memory = Path(args.mirror_memory).expanduser().resolve()
        if not memory.is_dir():
            print(f"[vault_git_sync] memory 폴더 없음 — 미러 건너뜀: {args.mirror_memory}")
        else:
            mirror_result = mirror_memory(memory, vault / ".memory-mirror")
    if mirror_result is not None:
        copied, deleted, unchanged = mirror_result
        print(f"[vault_git_sync] memory 미러: 복사 {copied} · 삭제 {deleted} · 동일 {unchanged}")

    if args.quantize_attachments:
        quantize_result = quantize_attachments(vault / "handoff" / "attachments")
        if quantize_result is not None:
            converted, unchanged, saved_bytes = quantize_result
            print(
                f"[vault_git_sync] 첨부 양자화: 변환 {converted} · "
                f"이미 256색 {unchanged} · 절감 {saved_bytes / (1024 * 1024):.2f}MB"
            )

    status = run_git(vault, "status", "--porcelain")
    if status.returncode != 0:
        print(first_error(status), file=sys.stderr)
        return 1
    changes = [line for line in status.stdout.splitlines() if line]
    if not changes:
        print("[vault_git_sync] 변경 없음")
        return 0

    paths = [line[3:] if len(line) > 3 else line for line in changes]
    subject = f"vault-sync {now:%Y-%m-%d %H:%M}"
    body_lines = [f"- 변경 {len(changes)}개 파일"] + [f"- {path}" for path in paths[:5]]
    message = subject + "\n\n" + "\n".join(body_lines)

    added = run_git(vault, "add", "-A")
    if added.returncode != 0:
        print(first_error(added), file=sys.stderr)
        return 1
    committed = run_git(vault, "commit", "-m", message)
    if committed.returncode != 0:
        print(first_error(committed), file=sys.stderr)
        return 1
    sha_result = run_git(vault, "rev-parse", "--short", "HEAD")
    if sha_result.returncode != 0:
        print(first_error(sha_result), file=sys.stderr)
        return 1
    sha = sha_result.stdout.strip()

    push_status = "건너뜀"
    if not args.no_push:
        pushed = run_git(vault, "push")
        if pushed.returncode == 0:
            push_status = "완료"
        else:
            push_status = "실패"
            print(f"[vault_git_sync] push 실패 — 로컬 커밋은 남아 있다: {first_error(pushed)}")
    print(f"[vault_git_sync] {sha} 커밋 · push {push_status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
