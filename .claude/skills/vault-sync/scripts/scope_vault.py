#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
job frontmatter 의 scope_vault 파싱 · 해석 · 정규화를 한 곳에서 처리한다.

검사 항목
  - scope_vault 네 가지 입력 형태를 읽어 정규 블록 리스트로 변환
  - vault 문서 경로 해석과 memory · 훅 주입 · 누락 · 모호 판정
  - 해석 불가 항목을 unresolved 주석으로 보존

사용법:
    python scope_vault.py normalize <job.md>... [--apply]
    python scope_vault.py add <job.md> <folder/name>
    python scope_vault.py check <job.md>

종료 코드: 0 정상 / 1 인자·파일 오류 / 2 check 에서 ERROR 등급 항목 있음
"""

import argparse
import glob
import re
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

VAULT_SKIP_DIRS = {"_templates", "graphify-out", "backup", ".obsidian"}
MEMORY_SLUG_RE = re.compile(r"^(feedback|reference|project)_[a-z0-9_]+$")
HOOK_INJECTED = {"conventions/coding-style"}   # UserPromptSubmit 훅이 항상 주입 → scope_vault 에 둘 이유가 없다
KEY_RE = re.compile(r"(?m)^[A-Za-z0-9_-]+:")
SCOPE_RE = re.compile(r"(?m)^scope_vault:[^\r\n]*(?:\r?\n|$)")
UNRESOLVED_RE = re.compile(r"^\s*#\s*unresolved:\s*(.*)$")


def read_text(path: Path) -> str:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return stream.read()


def write_text(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        stream.write(text)


def find_vault_root(path: Path) -> Path | None:
    """path 의 조상 중 이름이 vault 이고 jobs 폴더가 있는 경로를 찾는다."""
    resolved = path.resolve()
    candidates = [resolved] + list(resolved.parents)
    for candidate in candidates:
        if candidate.name == "vault" and (candidate / "jobs").is_dir():
            return candidate
    return None


def split_frontmatter(text: str) -> tuple[str, str, str] | None:
    """(여는 구분선, frontmatter 본문, 닫는 구분선부터 나머지)를 반환한다."""
    opening = re.match(r"\A\ufeff?---(\r?\n)", text)
    if opening is None:
        return None
    eol = opening.group(1)
    closing = re.search(r"(?m)^---(?:\r?\n|$)", text[opening.end():])
    if closing is None:
        return None
    fm_start = opening.end()
    fm_end = fm_start + closing.start()
    return text[:fm_start], text[fm_start:fm_end], text[fm_end:]


def _split_inline(value: str) -> list[str]:
    inner = value.strip()[1:-1]
    if not inner.strip():
        return []
    return [part.strip() for part in inner.split(",") if part.strip()]


def extract_block(fm: str) -> tuple[int, int, list[str], list[str]] | None:
    """scope_vault 블록 범위, 항목 원문, 주석 줄을 반환한다."""
    match = SCOPE_RE.search(fm)
    if match is None:
        return None
    first_line = match.group(0).rstrip("\r\n")
    value = first_line.split(":", 1)[1].strip()
    next_key = KEY_RE.search(fm, match.end())
    end = next_key.start() if next_key else len(fm)
    block_tail = fm[match.end():end]
    comments = []
    for line in block_tail.splitlines():
        if UNRESOLVED_RE.match(line):
            comments.append(line.strip())
    if value:
        items = _split_inline(value) if value.startswith("[") and value.endswith("]") else [value]
        return match.start(), end, items, comments

    items = []
    for line in block_tail.splitlines():
        item = re.match(r"^\s*-\s*(.*?)\s*$", line)
        if item:
            items.append(item.group(1))
    return match.start(), end, items, comments


def normalize_target(raw: str) -> str:
    """scope_vault 항목을 vault 상대 경로 후보로 정리한다."""
    target = raw.strip().strip('"\'').strip()
    if target.startswith("[[") and target.endswith("]]" ):
        target = target[2:-2]
    target = target.split("|", 1)[0].split("#", 1)[0].strip()
    if target.lower().endswith(".md"):
        target = target[:-3]
    target = target.replace("\\", "/").lstrip("/")
    if target.startswith("vault/"):
        target = target[len("vault/"):]
    return target


def resolve(target: str, vault: Path) -> tuple[str, str]:
    """target 을 ok · memory · hook · missing · ambiguous 로 판정한다."""
    if MEMORY_SLUG_RE.fullmatch(target):
        return "memory", target
    if "/" in target:
        value = target.strip("/")
        status = "ok" if (vault / f"{value}.md").is_file() else "missing"
        if status == "ok" and value in HOOK_INJECTED:
            return "hook", value
        return status, value

    matches = []
    for candidate in vault.rglob(f"{target}.md"):
        relative = candidate.relative_to(vault)
        if any(part in VAULT_SKIP_DIRS for part in relative.parts[:-1]):
            continue
        matches.append(candidate.with_suffix("").relative_to(vault).as_posix())
    matches.sort()
    if not matches:
        return "missing", target
    if len(matches) > 1:
        return "ambiguous", ", ".join(matches)
    value = matches[0]
    if value in HOOK_INJECTED:
        return "hook", value
    return "ok", value


def render(items: list[str], unresolved: list[str], eol: str) -> str:
    """scope_vault 정규 블록을 렌더링한다."""
    if not items and not unresolved:
        return f"scope_vault: []{eol}"
    lines = ["scope_vault:" if items else "scope_vault: []"]
    lines.extend(f'  - "[[{item}]]"' for item in items)
    for value in unresolved:
        if value.lstrip().startswith("# unresolved:"):
            value = value.split("# unresolved:", 1)[1].strip()
        lines.append(f"  # unresolved: {value}")
    return eol.join(lines) + eol


def _block_end(fm: str, key: str) -> int | None:
    key_match = re.search(rf"(?m)^{re.escape(key)}:[^\r\n]*(?:\r?\n|$)", fm)
    if key_match is None:
        return None
    next_key = KEY_RE.search(fm, key_match.end())
    return next_key.start() if next_key else len(fm)


def replace_block(text: str, new_block: str) -> str:
    """scope_vault 블록을 치환하거나 scope_keywords 뒤에 삽입한다."""
    parts = split_frontmatter(text)
    if parts is None:
        raise ValueError("frontmatter 없음")
    opening, fm, rest = parts
    block = extract_block(fm)
    if block is not None:
        start, end = block[:2]
        new_fm = fm[:start] + new_block + fm[end:]
    else:
        insert_at = _block_end(fm, "scope_keywords")
        if insert_at is None:
            insert_at = len(fm)
        prefix = fm[:insert_at]
        if prefix and not prefix.endswith(("\n", "\r")):
            prefix += "\r\n" if "\r\n" in opening else "\n"
        new_fm = prefix + new_block + fm[insert_at:]
    return opening + new_fm + rest


def _eol(text: str) -> str:
    return "\r\n" if "\r\n" in text else "\n"


def analyze(path: Path):
    text = read_text(path)
    parts = split_frontmatter(text)
    if parts is None:
        raise ValueError("frontmatter 없음")
    _, fm, _ = parts
    block = extract_block(fm)
    raw_items = block[2] if block else []
    comments = block[3] if block else []
    vault = find_vault_root(path)
    if vault is None:
        raise ValueError("vault 루트를 찾을 수 없음")

    resolved_items = []
    unresolved = []
    counts = {key: 0 for key in ("ok", "memory", "hook", "missing", "ambiguous")}
    details = []
    for raw in raw_items:
        target = normalize_target(raw)
        status, value = resolve(target, vault)
        counts[status] += 1
        details.append((raw, target, status, value))
        if status == "ok" and value not in resolved_items:
            resolved_items.append(value)
        elif status == "missing":
            unresolved.append(f"[[{target}]]")
        elif status == "ambiguous":
            unresolved.append(f"[[{target}]] (후보: {value})")
    for comment in comments:
        value = UNRESOLVED_RE.match(comment).group(1).strip()
        if value not in unresolved:
            unresolved.append(value)
    new_block = render(resolved_items, unresolved, _eol(text))
    new_text = replace_block(text, new_block)
    return text, new_text, raw_items, comments, details, counts


def command_normalize(paths: list[str], apply: bool) -> int:
    expanded = []
    for raw_path in paths:
        is_pattern = any(char in raw_path for char in "*?[")
        matches = sorted(glob.glob(raw_path)) if is_pattern else [raw_path]
        if not matches:
            print(f"파일 없음: {raw_path}", file=sys.stderr)
            return 1
        expanded.extend((match, is_pattern) for match in matches if not Path(match).name.endswith(".history.md"))
    for raw_path, from_pattern in expanded:
        path = Path(raw_path)
        if not path.is_file():
            print(f"파일 없음: {path}", file=sys.stderr)
            return 1
        try:
            before, after, _, _, details, counts = analyze(path)
        except (OSError, ValueError) as exc:
            if from_pattern and str(exc) == "frontmatter 없음":
                print(f"=== {path} ===")
                print("건너뜀 — frontmatter 없음")
                continue
            print(f"{path}: {exc}", file=sys.stderr)
            return 1
        print(f"=== {path} ===")
        if before == after:
            print("변경 없음")
        else:
            old = extract_block(split_frontmatter(before)[1])
            new = extract_block(split_frontmatter(after)[1])
            print("변경 전")
            print(split_frontmatter(before)[1][old[0]:old[1]].rstrip("\r\n") if old else "(없음)")
            print("→ 변경 후")
            print(split_frontmatter(after)[1][new[0]:new[1]].rstrip("\r\n"))
            if apply:
                write_text(path, after)
        for raw, _, status, value in details:
            print(f"  {status:<9} {raw} → {value}")
        print("판정: " + " · ".join(f"{key} {counts[key]}" for key in counts))
    return 0


def command_add(raw_path: str, raw_target: str) -> int:
    path = Path(raw_path)
    if not path.is_file():
        print(f"파일 없음: {path}", file=sys.stderr)
        return 1
    try:
        text, normalized_text, _, _, details, _ = analyze(path)
        vault = find_vault_root(path)
        target = normalize_target(raw_target)
        status, value = resolve(target, vault)
    except (OSError, ValueError) as exc:
        print(f"{path}: {exc}", file=sys.stderr)
        return 1
    if status != "ok":
        print(f"scope_vault 추가 실패: {raw_target} — {status}: {value}", file=sys.stderr)
        return 1
    existing = [item_value for _, _, item_status, item_value in details if item_status == "ok"]
    if value in existing:
        return 0
    existing.append(value)
    normalized_fm = split_frontmatter(normalized_text)[1]
    normalized_block = extract_block(normalized_fm)
    unresolved = [UNRESOLVED_RE.match(comment).group(1).strip() for comment in normalized_block[3]]
    new_text = replace_block(normalized_text, render(existing, unresolved, _eol(text)))
    write_text(path, new_text)
    for raw, item_target, item_status, item_value in details:
        if item_status in ("memory", "hook"):
            print(f"scope_vault 제거: {raw} — {item_status}")
        elif item_status == "ok" and "/" not in item_target and "/" in item_value:
            print(f"scope_vault 정규화: {raw} → [[{item_value}]]")
    print(f"scope_vault 추가: [[{value}]]")
    return 0


def _canonical_raw(raw: str) -> bool:
    return bool(re.fullmatch(r'"\[\[[^\]|#]+/[^\]|#]+\]\]"', raw.strip()))


def command_check(raw_path: str) -> int:
    path = Path(raw_path)
    if not path.is_file():
        print(f"파일 없음: {path}", file=sys.stderr)
        return 1
    try:
        _, _, raw_items, _, details, counts = analyze(path)
        fm = split_frontmatter(read_text(path))[1]
        block = extract_block(fm)
        block_text = fm[block[0]:block[1]] if block else ""
    except (OSError, ValueError) as exc:
        print(f"{path}: {exc}", file=sys.stderr)
        return 1
    inline = bool(re.match(r"^scope_vault:\s*\[\s*[^\]\s]", block_text))   # `[]` 는 정규 빈 값
    errors = 0
    if inline:
        errors += 1
        print("ERROR scope_vault 인라인 리스트 → 블록 리스트로 (scope_vault.py normalize)")
    for raw, _, status, value in details:
        if status in ("ok", "hook") and not _canonical_raw(raw):
            errors += 1
            print(f'ERROR scope_vault 표기 위반: {raw} → "[[folder/name]]" (scope_vault.py normalize)')
        if status == "memory":
            errors += 1
            print(f"ERROR scope_vault 에 memory 슬러그: {raw} — vault 밖이라 resume 이 로드 못 함")
        elif status == "missing":
            errors += 1
            print(f"ERROR scope_vault 대상 없음: {raw}")
        elif status == "ambiguous":
            errors += 1
            print(f"ERROR scope_vault 대상 모호: {raw} (후보: {value})")
        elif status == "hook":
            print(f"WARN scope_vault 의 {value} 는 훅이 항상 주입 — 제거 권장")
    print("판정: " + " · ".join(f"{key} {counts[key]}" for key in counts))
    return 2 if errors else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="scope_vault 정규화 · 추가 · 검사")
    sub = parser.add_subparsers(dest="command", required=True)
    normalize = sub.add_parser("normalize")
    normalize.add_argument("jobs", nargs="+")
    normalize.add_argument("--apply", action="store_true")
    add = sub.add_parser("add")
    add.add_argument("job")
    add.add_argument("target")
    check = sub.add_parser("check")
    check.add_argument("job")
    args = parser.parse_args()
    if args.command == "normalize":
        return command_normalize(args.jobs, args.apply)
    if args.command == "add":
        return command_add(args.job, args.target)
    return command_check(args.job)


if __name__ == "__main__":
    sys.exit(main())
