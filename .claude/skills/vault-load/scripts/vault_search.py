#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vault 문서를 키워드와 wikilink 이웃으로 검색한다.

검사 항목
  - 지식 문서와 라이브 job 을 기본 검색 대상으로 제한
  - 키워드 점수와 출현 빈도로 KW 버킷 정렬
  - KW 상위 문서의 양방향 wikilink 이웃으로 GRAPH 버킷 구성
  - 파일명 인덱스를 한 번 만들어 링크를 결정적으로 해석

사용법:
    python vault_search.py [--vault vault] [--kw-limit 4] [--graph-limit 2]
                           [--include-records] 키워드...

종료 코드: 0 결과 있음 / 1 vault·인자·파일 오류 / 2 매칭 없음
"""

import argparse
import re
import sys
from pathlib import Path

SYNC_SCRIPTS = Path(__file__).resolve().parents[2] / "vault-sync" / "scripts"
sys.path.insert(0, str(SYNC_SCRIPTS))
from scope_vault import VAULT_SKIP_DIRS, normalize_target, read_text, split_frontmatter

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

KNOWLEDGE_FOLDERS = {
    "conventions", "architecture", "debugging", "decisions", "prd",
    "tools", "ui-specs", "feedback", "tech-debt",
}
RECORD_FOLDERS = {"handoff", "evidence", "daily", "weekly"}
INACTIVE_JOB_STATUSES = {"done", "cancelled"}
WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
H1_RE = re.compile(r"(?m)^#\s+(.+?)\s*$")
KEY_RE = re.compile(r"(?m)^[A-Za-z0-9_-]+:")


def frontmatter_field(text: str, key: str) -> str:
    parts = split_frontmatter(text)
    if parts is None:
        return ""
    frontmatter = parts[1]
    match = re.search(rf"(?m)^{re.escape(key)}:\s*(.*?)(?:\r?\n|$)", frontmatter)
    if match is None:
        return ""
    value = match.group(1).strip()
    if value:
        return value.strip('"\'')
    next_key = KEY_RE.search(frontmatter, match.end())
    end = next_key.start() if next_key else len(frontmatter)
    return frontmatter[match.end():end].strip()


def is_target(relative: Path, text: str, include_records: bool) -> bool:
    if not relative.parts:
        return False
    folder = relative.parts[0]
    if folder in KNOWLEDGE_FOLDERS:
        return True
    if include_records and folder in RECORD_FOLDERS:
        return True
    if folder != "jobs" or relative.name.endswith(".history.md"):
        return False
    return frontmatter_field(text, "status").casefold() not in INACTIVE_JOB_STATUSES


def build_filename_index(vault: Path) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for path in vault.rglob("*.md"):
        relative = path.relative_to(vault)
        if any(part in VAULT_SKIP_DIRS for part in relative.parts[:-1]):
            continue
        result.setdefault(path.stem, []).append(relative.with_suffix("").as_posix())
    for values in result.values():
        values.sort()
    return result


def resolve_link(target: str, vault: Path, filename_index: dict[str, list[str]]) -> list[str]:
    normalized = normalize_target(target)
    if not normalized:
        return []
    if "/" in normalized:
        value = normalized.strip("/")
        return [value] if (vault / f"{value}.md").is_file() else []
    return filename_index.get(normalized, [])


def keyword_score(text: str, terms: list[str]) -> tuple[int, int]:
    parts = split_frontmatter(text)
    body = parts[2] if parts is not None else text
    folded = body.casefold()
    title_match = H1_RE.search(text)
    title = title_match.group(1).casefold() if title_match else ""
    tags = frontmatter_field(text, "tags").casefold()
    hits = 0
    tf = 0
    for term in terms:
        count = folded.count(term)
        if count:
            hits += 1
            tf += count
        if term in title or term in tags:
            hits += 1
    return hits, min(tf, 50)


def main() -> int:
    parser = argparse.ArgumentParser(description="vault 링크 기반 검색")
    parser.add_argument("--vault", default="vault")
    parser.add_argument("--kw-limit", type=int, default=4)
    parser.add_argument("--graph-limit", type=int, default=2)
    parser.add_argument("--include-records", action="store_true")
    parser.add_argument("keywords", nargs="+")
    args = parser.parse_args()
    if args.kw_limit < 0 or args.graph_limit < 0:
        print("--kw-limit 과 --graph-limit 은 0 이상이어야 한다", file=sys.stderr)
        return 1

    vault = Path(args.vault).resolve()
    if not vault.is_dir():
        print(f"vault 없음: {vault}", file=sys.stderr)
        return 1
    terms = [keyword.casefold() for keyword in args.keywords if keyword]
    if not terms:
        print("키워드가 1개 이상 필요하다", file=sys.stderr)
        return 1

    documents: dict[str, str] = {}
    try:
        for path in vault.rglob("*.md"):
            relative = path.relative_to(vault)
            text = read_text(path)
            if is_target(relative, text, args.include_records):
                documents[relative.as_posix()] = text
    except OSError as exc:
        print(f"파일 읽기 실패: {exc}", file=sys.stderr)
        return 1

    scored = []
    for relative, text in documents.items():
        hits, tf = keyword_score(text, terms)
        if hits:
            scored.append((relative, hits, tf))
    scored.sort(key=lambda item: (-item[1], -item[2], item[0]))
    kw_bucket = scored[:args.kw_limit]
    if not kw_bucket:
        return 2

    filename_index = build_filename_index(vault)
    outgoing = {relative: set() for relative in documents}
    incoming = {relative: set() for relative in documents}
    for source, text in documents.items():
        for match in WIKILINK_RE.finditer(text):
            for target in resolve_link(match.group(1), vault, filename_index):
                target_path = f"{target}.md"
                if target_path not in documents or target_path == source:
                    continue
                outgoing[source].add(target_path)
                incoming[target_path].add(source)

    kw_paths = {relative for relative, _, _ in kw_bucket}
    neighbor_counts: dict[str, int] = {}
    for source in kw_paths:
        for neighbor in outgoing[source] | incoming[source]:
            if neighbor in kw_paths:
                continue
            neighbor_counts[neighbor] = neighbor_counts.get(neighbor, 0) + 1
    graph_bucket = sorted(neighbor_counts.items(), key=lambda item: (-item[1], item[0]))

    for relative, hits, _ in kw_bucket:
        print(f"KW\t{hits}\t-\tvault/{relative}")
    for relative, count in graph_bucket[:args.graph_limit]:
        print(f"GRAPH\t0\t{count}\tvault/{relative}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
