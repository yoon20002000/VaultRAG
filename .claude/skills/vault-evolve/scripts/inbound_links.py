#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vault 지식 문서의 실제 인바운드 wikilink 수를 계산한다.

검사 항목
  - 자동 생성·미러·설정 폴더를 출발 문서에서 제외
  - 지식 폴더 문서만 도착 대상으로 집계
  - 모호한 파일명 링크는 모든 후보에 집계
  - 인바운드 상위 문서와 0회 문서 출력

사용법:
    python inbound_links.py [--vault vault] [--top N] [--zero]

종료 코드: 0 정상 / 1 vault 없음·인자 오류
"""

import argparse
import re
import sys
from pathlib import Path

SYNC_SCRIPTS = Path(__file__).resolve().parents[2] / "vault-sync" / "scripts"
sys.path.insert(0, str(SYNC_SCRIPTS))
from scope_vault import normalize_target, read_text, resolve, split_frontmatter

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

SOURCE_EXCLUDES = {"_templates", ".memory-mirror", ".obsidian", "daily", "weekly"}
TARGET_FOLDERS = {
    "conventions", "architecture", "debugging", "decisions", "prd",
    "tools", "ui-specs", "feedback", "tech-debt",
}
WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def frontmatter_value(text: str, key: str) -> str:
    parts = split_frontmatter(text)
    if parts is None:
        return "-"
    match = re.search(rf"(?m)^{re.escape(key)}:\s*(.*?)\s*$", parts[1])
    if match is None or not match.group(1).strip():
        return "-"
    return match.group(1).strip().strip('"\'')


def target_documents(vault: Path) -> dict[str, Path]:
    result = {}
    for folder in sorted(TARGET_FOLDERS):
        root = vault / folder
        if not root.is_dir():
            continue
        for path in root.rglob("*.md"):
            result[path.relative_to(vault).with_suffix("").as_posix()] = path
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="vault 인바운드 wikilink 집계")
    parser.add_argument("--vault", default="vault")
    parser.add_argument("--top", type=int, default=5, metavar="N")
    parser.add_argument("--zero", action="store_true")
    args = parser.parse_args()
    if args.top < 0:
        print("--top 은 0 이상이어야 한다", file=sys.stderr)
        return 1
    vault = Path(args.vault).resolve()
    if not vault.is_dir():
        print(f"vault 없음: {vault}", file=sys.stderr)
        return 1

    targets = target_documents(vault)
    counts = {name: 0 for name in targets}
    resolved_targets = {}
    for source in vault.rglob("*.md"):
        relative = source.relative_to(vault)
        if any(part in SOURCE_EXCLUDES for part in relative.parts[:-1]):
            continue
        try:
            text = read_text(source)
        except OSError as exc:
            print(f"파일 읽기 실패: {source}: {exc}", file=sys.stderr)
            return 1
        for match in WIKILINK_RE.finditer(text):
            target = normalize_target(match.group(1))
            if target not in resolved_targets:
                if "/" in target:
                    value = target.strip("/")
                    resolved_targets[target] = ("ok", value) if (vault / f"{value}.md").is_file() else ("missing", value)
                else:
                    resolved_targets[target] = resolve(target, vault)
            status, value = resolved_targets[target]
            if status not in ("ok", "hook", "ambiguous"):
                continue
            candidates = value.split(", ") if status == "ambiguous" else [value]
            for candidate in candidates:
                if candidate in counts:
                    counts[candidate] += 1

    if args.zero:
        for name in sorted(key for key, count in counts.items() if count == 0):
            text = read_text(targets[name])
            print(f"0\t{name}\t{frontmatter_value(text, 'updated')}\t{frontmatter_value(text, 'confidence')}")
    else:
        ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        for name, count in ordered[:args.top]:
            print(f"{count}\t{name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
