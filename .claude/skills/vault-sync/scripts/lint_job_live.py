#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
라이브 job 문서 검사 — 「지금의 상태만」 규칙이 지켜지는지 기계적으로 확인한다.

규칙을 문장으로만 두면 에이전트는 지우지 않고 얹는다. 지우는 쪽은 복구 수단이
.bak 뿐이라 불리하고, 예전 문단이 아직 유효한지 sync 시점엔 모르기 때문이다.
실측: 2026-08-27-hero-accessory-equip-ui.md 가 09-28 정리(990→637) 뒤 sync 마다
늘어 743줄, 「현재 상태」에 `**▶ 10-07 (history (42))**` 형태 문단 7개,
「미해결」에 ✅ 해소 항목 15건가량. 기존 금지 규칙(`### YYYY-MM-DD`)과
rollover 스크립트(`## 진행 기록` 전용)는 이 형태를 하나도 잡지 못했다.

검사 항목
  ERROR (exit 2) — 규칙 위반, 고쳐야 한다
    - 날짜 엔트리 헤딩 `### YYYY-MM-DD`
    - `## 현재 상태` 안의 날짜 붙은 ▶ 문단 2개 이상
    - `## 미해결` 안의 ✅ · 🟢 · 「해소」로 시작하는 항목
    - 백틱 안 `Assets/...` 경로가 디스크에 없음 (삭제·개명된 파일 서술)
    - scope_vault 표기 위반
    - scope_vault 에 memory 슬러그
    - scope_vault 대상 없음 또는 대상 모호
  WARN (exit 0) — 판단 필요, 승인 목록에 보고한다
    - 본문 300줄 초과 (vault-load FULL 임계)
    - 섹션 예산 초과
    - `## 최신 결정` 안의 경위 단어(롤백 · 기각 · 폐기 · 번복 · 대체)
    - scope_vault 의 훅 상시 주입 문서

사용법:
    python lint_job_live.py vault/jobs/<job>.md
    python lint_job_live.py vault/jobs/<job>.md --quiet   # ERROR 만 출력 (훅용)

종료 코드: 0 통과(경고만 있어도 0) / 2 ERROR 있음 / 1 실행 오류
"""

import sys
import re
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from scope_vault import find_vault_root, normalize_target, resolve

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

TOTAL_BUDGET = 300
SECTION_BUDGETS = {
    "현재 상태": 60,
    "최신 결정": 110,
    "작업 플로우": 20,
    "미해결": 90,
}
DATE_HEADING_RE = re.compile(r"^###\s+20\d\d-\d\d-\d\d")
DATED_ARROW_RE = re.compile(r"▶\s*(20\d\d-)?\d\d-\d\d")
RESOLVED_ITEM_RE = re.compile(r"^\s*-\s*(✅|🟢|~~|\**해소)")
HISTORY_WORD_RE = re.compile(r"롤백|기각|폐기|번복|대체")
ASSET_PATH_RE = re.compile(r"`(Assets/[^`*]+?\.(?:cs|prefab|asset|unity))`")
FRONTMATTER_KEY_RE = re.compile(r"^[A-Za-z0-9_-]+:")


def find_repo_root(path):
    for p in [path.resolve()] + list(path.resolve().parents):
        if (p / "Assets").is_dir():
            return p
    return None


def split_sections(lines):
    """## 단위 (이름, 시작, 끝). 이름은 제목에서 '## ' 제거."""
    marks = [i for i, l in enumerate(lines) if l.startswith("## ")]
    out = []
    for a, b in zip(marks, marks[1:] + [len(lines)]):
        out.append((lines[a][3:].strip(), a, b))
    return out


def section_key(name):
    for key in SECTION_BUDGETS:
        if name.startswith(key):
            return key
    return None


def extract_frontmatter(lines):
    """--- 로 감싼 YAML 프론트매터를 반환. 없으면 빈 리스트."""
    if not lines or lines[0].strip() != "---":
        return []
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            return lines[1:i]
    return []


def job_status(lines):
    """job 문서 frontmatter 의 status 값. 없거나 빈 값이면 None."""
    for line in extract_frontmatter(lines):
        match = re.match(r"status:\s*(.*)$", line.strip())
        if match:
            return match.group(1).strip().strip('"' + "'") or None
    return None


def scope_vault_entries(lines):
    """scope_vault 항목 목록과 인라인 리스트의 라인 번호를 반환한다."""
    frontmatter = extract_frontmatter(lines)
    for offset, line in enumerate(frontmatter, 2):
        if not line.startswith("scope_vault:"):
            continue
        value = line.split(":", 1)[1].strip()
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1]
            items = [item.strip() for item in inner.split(",") if item.strip()]
            return [(offset, item, False) for item in items], (offset if items else None)   # `[]` 는 정규 빈 값
        if value:
            return [(offset, value, True)], None
        entries = []
        start = offset - 1
        for index in range(start + 1, 1 + len(frontmatter)):
            block_line = lines[index]
            if FRONTMATTER_KEY_RE.match(block_line):
                break
            match = re.match(r"^\s*-\s*(.*?)\s*$", block_line)
            if match:
                raw = match.group(1)
                entries.append((index + 1, raw, block_line != f"  - {raw}"))
        return entries, None
    return [], None


def canonical_scope_item(raw):
    return bool(re.fullmatch(r'"\[\[[^\]|#]+/[^\]|#]+\]\]"', raw.strip()))


def lint(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    body_start = 0
    if lines and lines[0].strip() == "---":
        body_start = next((i + 1 for i in range(1, len(lines)) if lines[i].strip() == "---"), 0)
    errors, warns = [], []

    body_len = len(lines) - body_start
    if body_len > TOTAL_BUDGET:
        warns.append((0, f"본문 {body_len}줄 > {TOTAL_BUDGET} — vault-load 가 통째로 못 읽는다"))

    for i, l in enumerate(lines):
        if DATE_HEADING_RE.match(l):
            errors.append((i + 1, f"날짜 엔트리 헤딩 → history 로: {l.strip()[:60]}"))

    for name, a, b in split_sections(lines):
        key = section_key(name)
        if key is None:
            continue
        size = b - a - 1
        if size > SECTION_BUDGETS[key]:
            warns.append((a + 1, f"`## {name}` {size}줄 > 예산 {SECTION_BUDGETS[key]}"))
        sec = range(a + 1, b)
        if key == "현재 상태":
            arrows = [i for i in sec if DATED_ARROW_RE.search(lines[i])]
            if len(arrows) > 1:
                errors.append((arrows[1] + 1,
                               f"날짜 ▶ 문단 {len(arrows)}개 — 하나만 남기고 덮어쓴다 (줄 {', '.join(str(x + 1) for x in arrows)})"))
        elif key == "미해결":
            for i in sec:
                if RESOLVED_ITEM_RE.match(lines[i]):
                    errors.append((i + 1, f"해소 항목은 줄째 삭제(경위는 history): {lines[i].strip()[:60]}"))
        elif key == "최신 결정":
            for i in sec:
                m = HISTORY_WORD_RE.search(lines[i])
                if m:
                    warns.append((i + 1, f"경위 단어 「{m.group(0)}」 — 결과만 남았는지 확인: {lines[i].strip()[:50]}"))

    root = find_repo_root(path)
    if root is not None:
        seen = set()
        for i, l in enumerate(lines):
            # 다른 브랜치 · stash 에만 있는 파일은 서술 자체가 맞다 — 줄에 그 표시가 있으면 건너뛴다
            if "stash" in l or "브랜치" in l:
                continue
            for m in ASSET_PATH_RE.finditer(l):
                rel = m.group(1)
                if rel in seen or any(c in rel for c in "*{<"):
                    continue
                seen.add(rel)
                if not (root / rel).exists():
                    errors.append((i + 1, f"없는 파일을 서술 중: {rel}"))

    vault = find_vault_root(path)
    if vault is not None:
        scope_entries, inline_line = scope_vault_entries(lines)
        if inline_line is not None:
            errors.append((inline_line, "scope_vault 인라인 리스트 → 블록 리스트로 (scope_vault.py normalize)"))
        for line_no, raw, bad_format in scope_entries:
            target = normalize_target(raw)
            status, value = resolve(target, vault)
            if status in ("ok", "hook") and (bad_format or not canonical_scope_item(raw)):
                errors.append((line_no, f'scope_vault 표기 위반: {raw} → "[[folder/name]]" (scope_vault.py normalize)'))
            if status == "memory":
                errors.append((line_no, f"scope_vault 에 memory 슬러그: {raw} — vault 밖이라 resume 이 로드 못 함"))
            elif status == "missing":
                errors.append((line_no, f"scope_vault 대상 없음: {raw}"))
            elif status == "ambiguous":
                errors.append((line_no, f"scope_vault 대상 모호: {raw} (후보: {value})"))
            elif status == "hook":
                warns.append((line_no, f"scope_vault 의 {value} 는 훅이 항상 주입 — 제거 권장"))
    return body_len, errors, warns


def main():
    ap = argparse.ArgumentParser()
    target = ap.add_mutually_exclusive_group(required=True)
    target.add_argument("doc", nargs="?")
    target.add_argument("--all", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    if args.all:
        root = find_repo_root(Path(__file__))
        if root is None:
            print("저장소 루트를 찾을 수 없음", file=sys.stderr)
            return 1
        paths = []
        for candidate in sorted((root / "vault" / "jobs").glob("*.md")):
            if candidate.name.endswith(".history.md"):
                continue
            lines = candidate.read_text(encoding="utf-8").splitlines()
            status = job_status(lines)
            if status is None or status in ("done", "cancelled"):
                continue
            paths.append(candidate)
        total_errors = 0
        total_warns = 0
        for path in paths:
            body_len, errors, warns = lint(path)
            total_errors += len(errors)
            total_warns += len(warns)
            print(f"[lint_job_live] {path.name} — 본문 {body_len}줄, ERROR {len(errors)}, WARN {len(warns)}")
            for ln, msg in errors:
                print(f"  ERROR L{ln}: {msg}")
            for ln, msg in warns:
                print(f"  WARN  L{ln}: {msg}")
        print(f"[lint_job_live] 합계: 문서 {len(paths)} · ERROR {total_errors} · WARN {total_warns}")
        return 2 if total_errors else 0

    path = Path(args.doc)
    if not path.is_file():
        print(f"파일 없음: {path}", file=sys.stderr)
        return 1
    if path.name.endswith(".history.md"):
        return 0
    body_len, errors, warns = lint(path)
    if not args.quiet or errors:
        print(f"[lint_job_live] {path.name} — 본문 {body_len}줄, ERROR {len(errors)}, WARN {len(warns)}")
    for ln, msg in errors:
        print(f"  ERROR L{ln}: {msg}")
    if not args.quiet:
        for ln, msg in warns:
            print(f"  WARN  L{ln}: {msg}")
    return 2 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
