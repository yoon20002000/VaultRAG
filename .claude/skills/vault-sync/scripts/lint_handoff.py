#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
handoff 문서의 최소 frontmatter 메타데이터를 검사하고 보완한다.

검사 항목
  - tags · created · kind 필수 키
  - kind 허용값
  - job 권장 키
  - frontmatter 가 없거나 필수 키가 빠진 문서에 최소 메타데이터 자동 삽입

사용법:
    python lint_handoff.py [--vault vault] [--fix] [--since YYYY-MM-DD]

종료 코드: 0 통과 / 2 ERROR 있음 / 1 인자·파일 오류
"""

import argparse
import re
import sys
from datetime import date, datetime
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

ALLOWED_KINDS = {
    "spec", "tc", "handoff", "plan", "report", "checklist", "guide",
    "brief", "summary", "log", "review", "result", "backup", "other",
}
KEY_RE = re.compile(r"(?m)^([A-Za-z0-9_-]+):\s*(.*)$")
FILE_DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})")


def read_text(path: Path) -> str:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return stream.read()


def write_text(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        stream.write(text)


def split_frontmatter(text: str) -> str | None:
    opening = re.match(r"\A---\r?\n", text)
    if opening is None:
        return None
    closing = re.search(r"(?m)^---(?:\r?\n|$)", text[opening.end():])
    if closing is None:
        return None
    start = opening.end()
    return text[start:start + closing.start()]


def metadata(frontmatter: str) -> dict[str, str]:
    return {
        match.group(1): match.group(2).strip().strip('"\'')
        for match in KEY_RE.finditer(frontmatter)
    }


def parse_date(value: str) -> date | None:
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def document_date(path: Path, values: dict[str, str]) -> date | None:
    created = parse_date(values.get("created", ""))
    match = FILE_DATE_RE.match(path.name)
    filename_date = parse_date(match.group(1)) if match else None
    dates = [value for value in (created, filename_date) if value is not None]
    return max(dates) if dates else None


def infer_kind(path: Path) -> str:
    stem = path.stem.lower()
    suffixes = (
        (("-codex-spec", "-spec"), "spec"),
        (("-test-cases", "-tc"), "tc"),
        (("-handoff",), "handoff"),
        (("-fix-plan", "-plan"), "plan"),
        (("-report",), "report"),
        (("-checklist",), "checklist"),
        (("-guide",), "guide"),
        (("-brief",), "brief"),
        (("-summary",), "summary"),
        (("-log",), "log"),
        (("-review",), "review"),
        (("-result",), "result"),
        (("-backup",), "backup"),
    )
    for endings, kind in suffixes:
        if stem.endswith(endings):
            return kind
    return "other"


def add_frontmatter(path: Path, text: str) -> str:
    eol = "\r\n" if "\r\n" in text else "\n"
    match = FILE_DATE_RE.match(path.name)
    created = match.group(1) if match else datetime.fromtimestamp(path.stat().st_mtime).date().isoformat()
    prefix = eol.join((
        "---", "tags: [handoff]", f"created: {created}",
        f"kind: {infer_kind(path)}", "job:", "---", "",
    ))
    return prefix + text


def add_missing_metadata(path: Path, text: str, values: dict[str, str]) -> str:
    opening = re.match(r"\A---(\r?\n)", text)
    if opening is None:
        return text
    closing = re.search(r"(?m)^---(?:\r?\n|$)", text[opening.end():])
    if closing is None:
        return text

    lines = []
    if "tags" not in values:
        lines.append("tags: [handoff]")
    if "created" not in values:
        match = FILE_DATE_RE.match(path.name)
        created = match.group(1) if match else datetime.fromtimestamp(path.stat().st_mtime).date().isoformat()
        lines.append(f"created: {created}")
    if "kind" not in values:
        lines.append(f"kind: {infer_kind(path)}")
    if "job" not in values:
        lines.append("job:")
    if not lines:
        return text

    insertion_at = opening.end() + closing.start()
    insertion = opening.group(1).join(lines) + opening.group(1)
    return text[:insertion_at] + insertion + text[insertion_at:]


def main() -> int:
    parser = argparse.ArgumentParser(description="handoff frontmatter 검사")
    parser.add_argument("--vault", default="vault")
    parser.add_argument("--fix", action="store_true")
    parser.add_argument("--since", default=None, metavar="YYYY-MM-DD")
    args = parser.parse_args()
    since = parse_date(args.since) if args.since else None
    if args.since and since is None:
        print("--since 는 YYYY-MM-DD 형식이어야 한다", file=sys.stderr)
        return 1
    vault = Path(args.vault).resolve()
    handoff = vault / "handoff"
    if not handoff.is_dir():
        print(f"handoff 폴더 없음: {handoff}", file=sys.stderr)
        return 1

    document_count = error_count = warn_count = 0
    for path in sorted(handoff.glob("*.md")):
        try:
            text = read_text(path)
        except OSError as exc:
            print(f"파일 읽기 실패: {path}: {exc}", file=sys.stderr)
            return 1
        frontmatter = split_frontmatter(text)
        values = metadata(frontmatter) if frontmatter is not None else {}
        selected_date = document_date(path, values)
        if since is not None and (selected_date is None or selected_date < since):
            continue
        document_count += 1
        relative = path.relative_to(vault).as_posix()
        if frontmatter is None and args.fix:
            text = add_frontmatter(path, text)
            write_text(path, text)
            frontmatter = split_frontmatter(text)
            values = metadata(frontmatter)
        elif args.fix:
            fixed_text = add_missing_metadata(path, text, values)
            if fixed_text != text:
                write_text(path, fixed_text)
                text = fixed_text
                frontmatter = split_frontmatter(text)
                values = metadata(frontmatter)
        if frontmatter is None:
            error_count += 1
            print(f"ERROR {relative}: frontmatter 없음")
            continue
        missing = [key for key in ("tags", "created", "kind") if key not in values]
        if missing:
            error_count += 1
            print(f"ERROR {relative}: 키 없음 {','.join(missing)}")
        if "job" not in values:
            warn_count += 1
            print(f"WARN {relative}: job 없음")
        kind = values.get("kind")
        if kind is not None and kind not in ALLOWED_KINDS:
            error_count += 1
            print(f"ERROR {relative}: kind 값 위반 {kind}")
    print(f"[lint_handoff] 문서 {document_count} · ERROR {error_count} · WARN {warn_count}")
    return 2 if error_count else 0


if __name__ == "__main__":
    sys.exit(main())
