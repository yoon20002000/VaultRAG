#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
지식 문서 frontmatter 의 status 를 4값 어휘로 정규화한다.

검사 항목
  - 지식 폴더의 status 만 대상
  - 자유 서술을 resolution 으로 이동
  - awaiting-release 예시 status 키 제거
  - 알 수 없는 값은 UNMAPPED 보고

사용법:
    python normalize_status.py [--vault vault] [--apply]

종료 코드: 0 정상 / 1 vault 없음·파일 오류
"""

import argparse
import re
import sys
from pathlib import Path

SYNC_SCRIPTS = Path(__file__).resolve().parents[2] / "vault-sync" / "scripts"
sys.path.insert(0, str(SYNC_SCRIPTS))
from scope_vault import read_text, split_frontmatter, write_text

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

TARGET_FOLDERS = ("architecture", "conventions", "debugging", "decisions", "feedback", "tools", "prd")
CANONICAL = {"open", "resolved", "superseded", "reference"}
STATUS_RE = re.compile(r"(?m)^status:\s*(.*?)(\r?\n|$)")


def classify(value: str) -> tuple[str | None, str | None, bool] | None:
    if value in CANONICAL:
        return value, None, False
    if value.startswith(("확인 완료", "수정 완료", "✅ 해결", "해결")):
        return "resolved", value, False
    if value.startswith(("🔴 조사 완료", "진단 완료", "fix-stashed", "on-hold", "커밋 ")):
        return "open", value, False
    if value == "abandoned":
        return "superseded", value, False
    if value in {"pending-server", "candidate", "active"} or value.startswith("accepted"):
        return "reference", value, False
    if value == "draft":
        return "reference", None, False
    if value == "awaiting-release":
        return None, None, True
    return None


def yaml_resolution(value: str) -> str:
    if ":" in value or "#" in value:
        return '"' + value.replace('"', '\\"') + '"'
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="지식 문서 status 정규화")
    parser.add_argument("--vault", default="vault")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    vault = Path(args.vault).resolve()
    if not vault.is_dir():
        print(f"vault 없음: {vault}", file=sys.stderr)
        return 1

    changed_count = unmapped_count = 0
    for folder in TARGET_FOLDERS:
        root = vault / folder
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.md")):
            try:
                text = read_text(path)
            except OSError as exc:
                print(f"파일 읽기 실패: {path}: {exc}", file=sys.stderr)
                return 1
            parts = split_frontmatter(text)
            if parts is None:
                continue
            opening, frontmatter, rest = parts
            match = STATUS_RE.search(frontmatter)
            if match is None:
                continue
            original = match.group(1).strip()
            value = original.strip('"\'').strip()
            result = classify(value)
            relative = path.relative_to(vault).as_posix()
            if result is None:
                unmapped_count += 1
                print(f"UNMAPPED {relative}: {original}")
                continue
            status, resolution, remove = result
            if remove:
                replacement = ""
                description = "키 삭제"
            elif status == value and resolution is None:
                continue
            else:
                eol = match.group(2) or ("\r\n" if "\r\n" in text else "\n")
                replacement = f"status: {status}{eol}"
                description = f"status: {status}"
                if resolution is not None:
                    replacement += f"resolution: {yaml_resolution(resolution)}{eol}"
                    description += " (+ resolution)"
            new_frontmatter = frontmatter[:match.start()] + replacement + frontmatter[match.end():]
            new_text = opening + new_frontmatter + rest
            changed_count += 1
            print(f"{relative}: {original} → {description}")
            if args.apply:
                try:
                    write_text(path, new_text)
                except OSError as exc:
                    print(f"파일 쓰기 실패: {path}: {exc}", file=sys.stderr)
                    return 1
    print(f"[normalize_status] 변경 {changed_count} · UNMAPPED {unmapped_count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
