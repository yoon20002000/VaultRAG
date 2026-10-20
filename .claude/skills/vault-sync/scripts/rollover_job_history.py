#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
job 진행 기록 롤오버 — 라이브 문서를 통째로 로드 가능한 크기로 유지한다.

job 문서는 진행 기록이 무한 누적되어 전체의 80% 이상을 차지하게 된다
(실측: 2026-07-03-wargame-remake.md 1636줄 중 진행 기록 1355줄 = 83%).
그 결과 vault-load 가 문서를 통째로 못 읽고 head+tail 샘플링에 의존하게 되는데,
엔트리 순서가 일정하지 않아 최신 엔트리를 안정적으로 집지 못한다.

이 스크립트는 진행 기록을 **크기 기준**으로 잘라 오래된 엔트리를 아카이브로 옮긴다.
크기를 쓰는 이유: 목적 자체가 로드 예산 관리이고, 개수·기간 기준은 엔트리 크기 편차
(중앙값 30줄 / 최대 281줄)를 잡지 못해 큰 엔트리 하나로 예산이 무너진다.

**고정 엔트리**: 미해결 마커가 붙은 엔트리는 오래돼도 라이브에 남긴다 —
미해결 이슈는 과거 기록이 아니라 현재 상태이기 때문이다.
다만 고정분이 무한정 쌓이면 규칙이 무력해지므로 별도 상한(--pin-cap)을 둔다.

사용법:
    python rollover_job_history.py vault/jobs/foo.md              # dry-run
    python rollover_job_history.py vault/jobs/foo.md --apply --date 2026-08-14

종료 코드:
    0 - 정상 (롤오버 대상 있음/없음 모두)
    1 - 오류 (파일 없음 / 진행 기록 섹션 없음 / 정산 불일치)
"""

import sys
import re
import argparse
import subprocess
from pathlib import Path

# Windows 콘솔 기본 인코딩(CP949)에서 이모지·한글 출력이 UnicodeEncodeError 로 터진다.
# PowerShell 도구로 호출하면 UTF-8 이라 안 보이지만 git-bash 에서는 크래시한다.
# stdout·stderr 둘 다 지정해야 한다 — 한쪽만 고치면 에러 메시지 쪽에서 다시 터진다.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

DATE_RE = re.compile(r'(20\d\d-\d\d-\d\d)')
# '### 2026-08-06' / '### 2026-08-06 (2)' / '### 2026-08-06 — 요약' 만 엔트리로 본다
ENTRY_HEAD_RE = re.compile(r'^###\s+20\d\d-\d\d-\d\d(\s|$)')
DEFAULT_PINS = ["🔴", "미해결", "유실 확정", "보류", "TODO"]


def read_text(path):
    with path.open("r", encoding="utf-8", errors="replace", newline="") as stream:
        return stream.read()


def write_text(path, text):
    with path.open("w", encoding="utf-8", newline="") as stream:
        stream.write(text)


def find_vault_root(path):
    for candidate in [path.resolve()] + list(path.resolve().parents):
        if candidate.name == "vault" and (candidate / "jobs").is_dir():
            return candidate
    return None


def run_git(vault, *args):
    return subprocess.run(
        ["git", "-C", str(vault), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def snapshot_job(job):
    vault = find_vault_root(job)
    if vault is None or not (vault / ".git").exists():
        print("vault 에 git 저장소가 없다 — 복구 수단이 없으므로 중단", file=sys.stderr)
        return None
    relative = job.resolve().relative_to(vault).as_posix()
    status = run_git(vault, "status", "--porcelain", "--", relative)
    if status.returncode != 0:
        print((status.stderr or status.stdout).strip(), file=sys.stderr)
        return None
    if not status.stdout.strip():
        return "이미 커밋됨"
    committed = run_git(
        vault, "commit", "-q", "-o", relative, "-m",
        f"롤오버 전 스냅샷: {job.name}",
    )
    if committed.returncode != 0:
        print((committed.stderr or committed.stdout).strip(), file=sys.stderr)
        return None
    sha = run_git(vault, "rev-parse", "--short", "HEAD")
    if sha.returncode != 0:
        print((sha.stderr or sha.stdout).strip(), file=sys.stderr)
        return None
    return f"git {sha.stdout.strip()}"


def find_history_section(lines, heading):
    """진행 기록 섹션의 (헤더 인덱스, 본문 시작, 본문 끝) 반환. 없으면 None."""
    start = None
    for i, l in enumerate(lines):
        if l.strip().startswith("## ") and heading in l:
            start = i
            break
    if start is None:
        return None
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].strip().startswith("## "):
            end = j
            break
    return start, start + 1, end


def split_entries(lines, body_start, body_end):
    """### 단위 엔트리로 분해. 첫 ### 이전의 머리말은 별도 반환."""
    marks = [i for i in range(body_start, body_end) if lines[i].strip().startswith("### ")]
    if not marks:
        return lines[body_start:body_end], []
    preamble = lines[body_start:marks[0]]
    entries = []
    for a, b in zip(marks, marks[1:] + [body_end]):
        heading = lines[a].strip()
        m = DATE_RE.search(heading)
        entries.append({
            "start": a, "end": b,
            "heading": heading,
            "date": m.group(1) if m else "0000-00-00",
            "lines": lines[a:b],
        })
    return preamble, entries


def scan_all_entries(lines):
    """문서 전체에서 '### YYYY-MM-DD...' 엔트리를 찾는다.

    날짜 엔트리가 '## 진행 기록' 밖의 다른 섹션에 섞여 들어간 문서가 실제로 존재한다
    (10개 중 2개). 엔트리의 끝은 '다음 ###' 또는 '다음 ##' 중 먼저 오는 쪽이다 —
    ## 로 끊지 않으면 뒤따르는 라이브 섹션까지 통째로 끌려간다.
    """
    # 날짜가 제목 **맨 앞**에 오는 것만 로그 엔트리다.
    # '### 커버리지 실측 (2026-08-06 기준)' 처럼 제목 안에 날짜가 든 라이브 소제목이
    # 실제로 존재하므로, 단순 날짜 포함으로 판정하면 본문을 통째로 끌고 간다.
    marks = [i for i, l in enumerate(lines) if ENTRY_HEAD_RE.match(l.strip())]
    entries = []
    for a in marks:
        b = len(lines)
        for j in range(a + 1, len(lines)):
            st = lines[j].strip()
            if st.startswith("### ") or st.startswith("## "):
                b = j
                break
        heading = lines[a].strip()
        entries.append({
            "start": a, "end": b,
            "heading": heading,
            "date": DATE_RE.search(heading).group(1),
            "lines": lines[a:b],
        })
    return entries


def main():
    ap = argparse.ArgumentParser(description="job 진행 기록 롤오버")
    ap.add_argument("job_path")
    ap.add_argument("--budget", type=int, default=200,
                    help="라이브에 남길 진행 기록 줄 수 상한 (기본 200)")
    ap.add_argument("--pin-cap", type=int, default=100,
                    help="고정(미해결) 엔트리 합계 상한. 초과 시 오래된 고정분도 이동 (기본 100)")
    ap.add_argument("--heading", default="진행 기록", help="진행 기록 섹션 제목 (기본: 진행 기록)")
    ap.add_argument("--scan-all", action="store_true",
                    help="문서 전체에서 '### YYYY-MM-DD' 엔트리를 찾는다. "
                         "날짜 엔트리가 다른 ## 섹션 안에 섞여 들어간 문서용")
    ap.add_argument("--pin-marker", action="append", default=None,
                    help=f"고정 마커 (반복 지정 가능). 기본: {' '.join(DEFAULT_PINS)}")
    ap.add_argument("--date", default=None, help="아카이브 스탬프 날짜 YYYY-MM-DD (--apply 시 필수)")
    ap.add_argument("--apply", action="store_true", help="실제로 파일을 수정 (미지정 시 dry-run)")
    args = ap.parse_args()

    pins = args.pin_marker if args.pin_marker else DEFAULT_PINS
    job = Path(args.job_path)
    if not job.exists():
        print(f"ERROR: {job} not found", file=sys.stderr)
        sys.exit(1)
    if args.apply and not args.date:
        print("ERROR: --apply 에는 --date YYYY-MM-DD 가 필요합니다 (env 의 오늘 날짜를 넘길 것)", file=sys.stderr)
        sys.exit(1)

    job_text = read_text(job)
    job_eol = "\r\n" if "\r\n" in job_text else "\n"
    lines = job_text.splitlines()
    sec = find_history_section(lines, args.heading)
    if sec is None:
        if not args.scan_all:
            print(f"ERROR: '## {args.heading}' 섹션을 찾지 못했습니다", file=sys.stderr)
            sys.exit(1)
        sec = (len(lines), len(lines), len(lines))   # scan-all 은 섹션이 없어도 동작한다
    head_i, body_start, body_end = sec
    if args.scan_all:
        preamble = []
        entries = scan_all_entries(lines)
    else:
        preamble, entries = split_entries(lines, body_start, body_end)

    if not entries:
        print(f"진행 기록에 ### 엔트리가 없습니다 — 롤오버 불필요")
        sys.exit(0)

    # 핀 판정은 **헤딩만** 본다. 본문까지 보면 무의미해진다 —
    # 실측: 🔴 는 본문에서 29/37 엔트리에 나오지만(인라인 강조 용도) 헤딩엔 1개뿐이고,
    # 그 1개가 정확히 미해결 엔트리다. 헤딩은 작성자가 엔트리 상태를 적는 자리다.
    for e in entries:
        e["pinned"] = any(p in e["heading"] for p in pins)
        e["size"] = len(e["lines"])

    pinned = [e for e in entries if e["pinned"]]
    normal = [e for e in entries if not e["pinned"]]

    # 고정분이 상한을 넘으면 오래된 고정분부터 해제 (규칙 무력화 방지)
    pin_total = sum(e["size"] for e in pinned)
    unpinned_by_cap = []
    if pin_total > args.pin_cap:
        for e in sorted(pinned, key=lambda x: x["date"]):
            if pin_total <= args.pin_cap:
                break
            e["pinned"] = False
            unpinned_by_cap.append(e)
            pin_total -= e["size"]
        pinned = [e for e in entries if e["pinned"]]
        normal = [e for e in entries if not e["pinned"]]

    # 예산에서 고정분을 먼저 차감하고, 남는 만큼 최신순으로 채운다
    remaining = max(0, args.budget - sum(e["size"] for e in pinned))
    keep_ids = {id(e) for e in pinned}
    used = 0
    for e in sorted(normal, key=lambda x: x["date"], reverse=True):
        if used + e["size"] > remaining:
            continue
        keep_ids.add(id(e))
        used += e["size"]

    # 원본 순서 유지 — 재정렬하지 않는다 (엔트리 내 (2)(3) 같은 의도된 그룹이 깨진다)
    kept = [e for e in entries if id(e) in keep_ids]
    moved = [e for e in entries if id(e) not in keep_ids]

    # ── 정산: 한 줄도 잃지 않았는지 ──────────────────────────────
    orig_body = sum(e["size"] for e in entries)
    if sum(e["size"] for e in kept) + sum(e["size"] for e in moved) != orig_body:
        print("ERROR: 줄 수 정산 불일치 — 중단", file=sys.stderr)
        sys.exit(1)

    live_total = len(lines) - sum(e["size"] for e in moved)
    print(f"=== 롤오버 {'적용' if args.apply else 'DRY-RUN'}: {job.name} ===")
    print(f"  현재 {len(lines)}줄 (진행 기록 {orig_body}줄, 엔트리 {len(entries)}개)")
    print(f"  예산 {args.budget}줄 / 고정 상한 {args.pin_cap}줄 / 고정 마커 {pins}")
    print(f"  유지 {len(kept)}개 ({sum(e['size'] for e in kept)}줄, 그중 고정 {len(pinned)}개 {sum(e['size'] for e in pinned)}줄)")
    print(f"  이동 {len(moved)}개 ({sum(e['size'] for e in moved)}줄)")
    print(f"  → 라이브 문서 {len(lines)}줄 ⇒ {live_total}줄")
    if unpinned_by_cap:
        print(f"  ⚠️ 고정 상한 초과로 고정 해제된 엔트리 {len(unpinned_by_cap)}개:")
        for e in unpinned_by_cap:
            print(f"       {e['heading'][:72]}")

    print(f"\n  [유지]")
    for e in kept:
        tag = "📌" if e["pinned"] else "  "
        print(f"    {tag} {e['size']:>4}줄  {e['heading'][:68]}")
    print(f"\n  [이동 → {job.stem}.history.md]")
    for e in moved:
        print(f"       {e['size']:>4}줄  {e['heading'][:68]}")

    if not args.apply:
        print(f"\n  (dry-run — 실제 적용하려면 --apply --date YYYY-MM-DD)")
        sys.exit(0)
    if not moved:
        print("\n  이동 대상 없음 — 파일 변경 없음")
        sys.exit(0)

    # ── 적용 ────────────────────────────────────────────────────
    # 적용하면 원본이 사라진다. 복구 수단은 vault 자체 git 이므로 적용 전에 이 파일만 먼저 커밋한다.
    snapshot = snapshot_job(job)
    if snapshot is None:
        sys.exit(1)

    hist_path = job.with_name(job.stem + ".history.md")
    moved_blob = []
    for e in moved:
        moved_blob.extend(e["lines"])

    if hist_path.exists():
        hist_text = read_text(hist_path)
        hist_eol = "\r\n" if "\r\n" in hist_text else "\n"
        hist_lines = hist_text.splitlines()
    else:
        hist_eol = job_eol
        hist_lines = [
            "---",
            "tags: [job-history]",
            f"job: {job.stem}",
            "---",
            "",
            f"# {job.stem} — 진행 기록 아카이브",
            "",
            f"라이브 문서 [[{job.stem}]] 에서 롤오버된 과거 엔트리. 최신 상태는 라이브 문서를 볼 것.",
            "",
        ]
    hist_lines += [f"<!-- rollover {args.date} -->", ""] + moved_blob + [""]
    write_text(hist_path, hist_eol.join(hist_lines) + hist_eol)

    if args.scan_all:
        # 엔트리가 문서 곳곳에 흩어져 있으므로 라인 범위로 걷어낸다.
        drop = set()
        for e in moved:
            drop.update(range(e["start"], e["end"]))
        new_lines = [l for i, l in enumerate(lines) if i not in drop]
        new_lines += ["",
                      f"> 시간순 엔트리 {len(moved)}건은 [[{hist_path.stem}]] 로 이동됨 (롤오버 {args.date})"]
    else:
        new_lines = lines[:body_start] + preamble
        for e in kept:
            new_lines.extend(e["lines"])
        new_lines.append(f"> 과거 엔트리 {len(moved)}건은 [[{hist_path.stem}]] 로 이동됨 (롤오버 {args.date})")
        new_lines.append("")
        new_lines.extend(lines[body_end:])
    write_text(job, job_eol.join(new_lines) + job_eol)

    print(f"\n  ✅ 적용 완료")
    print(f"     라이브   : {job}  ({len(new_lines)}줄)")
    print(f"     아카이브 : {hist_path}  ({len(hist_lines)}줄)")
    print(f"     스냅샷   : {snapshot}")
    sys.exit(0)


if __name__ == "__main__":
    main()
