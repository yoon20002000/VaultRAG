#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vault-load 섹션 인덱스 생성기

선정된 vault 문서에 대해 "무엇이 어디에 있는지"만 뽑아낸다.
본문을 잘라 담는 대신 프론트매터 + 섹션 목록(라인 번호 포함)을 보유하고,
실제 내용은 질문이 왔을 때 해당 라인 범위만 Read 로 인출한다.

문서를 두 부류로 나눠 출력한다:
    FULL  - 임계값보다 짧음 → Read 로 통째로 읽는다
    INDEX - 임계값보다 김   → 프론트매터 + 섹션 목록만 보유

vault/jobs/ 의 라이브 job 문서(frontmatter status 가 done·cancelled 가 아닌 것)는
임계값과 무관하게 항상 FULL 이다. 폴더가 아니라 status 가 판정 근거다.
FULL 인데 임계값을 초과하면 롤오버가 밀렸다는 뜻이라 경고를 붙인다.

사용법:
    python build_section_index.py <md_path> [<md_path> ...]
    python build_section_index.py --full-under 300 vault/a.md vault/b.md

종료 코드:
    0 - 정상
    1 - 읽을 수 있는 파일이 하나도 없음
"""

import sys
import re
import argparse
from pathlib import Path

# Windows 콘솔 기본 인코딩(CP949)에서 이모지·한글 출력이 UnicodeEncodeError 로 터진다.
# PowerShell 도구로 호출하면 UTF-8 이라 안 보이지만 git-bash 에서는 크래시한다.
# stdout·stderr 둘 다 지정해야 한다 — 한쪽만 고치면 에러 메시지 쪽에서 다시 터진다.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

HEADER_RE = re.compile(r'^(#{1,4})\s+(.*)$')


def read_lines(path: Path):
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


def extract_frontmatter(lines):
    """--- 로 감싼 YAML 프론트매터를 반환. 없으면 빈 리스트."""
    if not lines or lines[0].strip() != "---":
        return []
    for i, l in enumerate(lines[1:], 1):
        if l.strip() == "---":
            return lines[1:i]
    return []


def job_status(lines):
    """job 문서 frontmatter 의 status 값. 없으면 None."""
    for l in extract_frontmatter(lines):
        m = re.match(r'status:\s*(.*)$', l.strip())
        if m:
            return m.group(1).strip().strip('"' + "'") or None
    return None


def build_index(lines):
    """(라인번호, 부모경로付 제목, 레벨) 목록. 부모 헤더를 붙여 동명 섹션을 구분한다."""
    out = []
    stack = {}  # level -> title
    for i, l in enumerate(lines):
        m = HEADER_RE.match(l)
        if not m:
            continue
        level = len(m.group(1))
        title = m.group(2).strip()
        if level == 1:            # 문서 제목은 인덱스에 넣지 않는다
            continue
        stack[level] = title
        for deeper in [k for k in stack if k > level]:
            del stack[deeper]
        parent = stack.get(level - 1)
        # Start() 처럼 짧은 제목은 부모 없이는 구분이 안 된다
        label = f"{parent} > {title}" if parent and level >= 3 else title
        out.append((i + 1, label, level))
    return out


def main():
    ap = argparse.ArgumentParser(description="vault 섹션 인덱스 생성기")
    ap.add_argument("paths", nargs="+", help="인덱싱할 md 파일 경로")
    ap.add_argument("--full-under", type=int, default=300,
                    help="일반 문서: 이 줄 수 미만이면 FULL(통째로 읽기) 판정 (기본 300)")
    # 라이브 job 문서는 항상 FULL 이므로 임계값이 아니라 '경고선'이 필요하다.
    # 진행 기록을 다 비워도 완료 조건·조사 기록 등 비-히스토리 상태만 279줄이라
    # 일반 임계값(300)으로는 구조적으로 통과가 불가능하다.
    ap.add_argument("--job-warn", type=int, default=600,
                    help="라이브 job 문서가 이 줄 수 이상이면 롤오버 경고 (기본 600)")
    args = ap.parse_args()

    ok = 0
    for raw in args.paths:
        p = Path(raw)
        if not p.exists():
            print(f"=== {raw} | 없음 ===", file=sys.stderr)
            continue
        ok += 1

        lines = read_lines(p)
        n = len(lines)
        rel = str(p).replace("\\", "/")
        # 완료 여부는 폴더가 아니라 status 로 판정한다 — job 문서는 이동하지 않는다.
        is_live_job = ("vault/jobs/" in rel
                       and not rel.endswith(".history.md")
                       and (job_status(lines) or "") not in ("", "done", "cancelled"))

        if is_live_job:
            mode = "FULL"
            note = ""
            if n >= args.job_warn:
                note = f"  ⚠️ 롤오버 권장 ({n}줄 ≥ {args.job_warn}) — /vault-sync 롤오버 실행"
        elif n < args.full_under:
            mode = "FULL"
            note = ""
        else:
            mode = "INDEX"
            note = ""

        print(f"=== {rel} | {n}줄 | {mode} ==={note}")

        fm = extract_frontmatter(lines)
        if fm:
            print("--- frontmatter ---")
            for l in fm:
                print(l)

        if mode == "FULL":
            print(f"--- 본문 {n}줄 전체를 Read 로 읽을 것 ---")
        else:
            idx = build_index(lines)
            print(f"--- sections ({len(idx)}개) ---")
            for ln, label, level in idx:
                indent = "  " * (level - 2)
                print(f"L{ln:<6}{indent}{label}")
        print()

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
