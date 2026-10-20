#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
graphify 그래프 신선도 감사기

graphify 는 exit 0 으로도 조용히 낡은 그래프를 남긴다. 이 스크립트는 graph.json 을
디스크의 실제 파일과 대조해 "낡음"을 세 축으로 계량한다.

    1. 좀비      - 그래프 노드의 source_file 이 디스크에 없음 (이동·삭제된 문서)
    2. 누적층    - 한 파일의 그래프 노드 수가 마지막 추출 결과보다 많음
                   (--update 가 옛 노드를 지우지 않고 층층이 쌓은 흔적)
    3. 라벨 중복 - 같은 파일 안에서 같은 라벨이 여러 노드로 존재
    4. 얕은 추출 - 문서 크기 대비 노드가 너무 적음 (있어야 할 것이 없는 축)

1~3 은 "있으면 안 될 것이 있다" 를 본다. 그것만으로는 추출 에이전트가 30KB 문서를
1 노드로 훑고 지나간 경우가 오염 0% 로 통과한다 - 그래서 4 번 축이 필요하다.

사용법:
    python .claude/scripts/graphify_audit.py                 # 저장소 루트에서
    python .claude/scripts/graphify_audit.py --out-dir graphify-out
    python .claude/scripts/graphify_audit.py --fail-over 5   # 오염률 5% 초과 시 exit 1

종료 코드:
    0 - 임계값 이내
    1 - 오염률이 --fail-over 초과
    2 - graph.json 없음
"""

import argparse
import collections
import glob
import json
import os
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

BS = chr(92)


def norm(p):
    return (p or "").replace(BS, "/")


def load_latest_cache_counts(cache_dir):
    """파일별 '가장 최근 추출 회차의 노드 수'. 캐시가 없으면 빈 dict."""
    latest = {}
    for f in glob.glob(os.path.join(cache_dir, "*.json")):
        try:
            d = json.loads(Path(f).read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(d, dict) or not d.get("nodes"):
            continue
        sf = norm(d["nodes"][0].get("source_file"))
        mt = os.path.getmtime(f)
        if sf not in latest or mt > latest[sf][0]:
            latest[sf] = (mt, len(d["nodes"]))
    return {k: v[1] for k, v in latest.items()}


def main():
    ap = argparse.ArgumentParser(description="graphify 그래프 신선도 감사")
    ap.add_argument("--out-dir", default="graphify-out", help="graphify 산출물 폴더")
    ap.add_argument("--fail-over", type=float, default=None,
                    help="오염 노드 비율(%%)이 이 값을 넘으면 exit 1")
    ap.add_argument("--list", type=int, default=15, help="축별 상세 출력 개수")
    ap.add_argument("--thin-under", type=float, default=0.15,
                    help="이 값(노드/KB) 미만이면 얕은 추출로 본다 (기본 0.15, 중앙값은 보통 0.6~0.7)")
    ap.add_argument("--thin-min-kb", type=float, default=8.0,
                    help="얕은 추출 판정 최소 문서 크기 (기본 8KB)")
    args = ap.parse_args()

    gpath = Path(args.out_dir) / "graph.json"
    if not gpath.exists():
        print(f"graph.json 없음: {gpath}", file=sys.stderr)
        return 2

    g = json.loads(gpath.read_text(encoding="utf-8"))
    nodes = g.get("nodes", [])
    links = g.get("links") or g.get("edges") or []
    total = len(nodes)

    node_by_src = collections.Counter(norm(n.get("source_file")) for n in nodes)
    # 캐시는 시맨틱 추출만 담는다 — AST 노드를 섞어 비교하면 누적층으로 오탐한다.
    # 단 제외 기준은 노드의 file_type 이 아니라 '소스 파일의 확장자' 다.
    # 추출 에이전트는 C# 클래스를 서술한 .md 문서의 노드에도 file_type="code" 를 붙인다 —
    # file_type 으로 거르면 그 문서가 통째로 얕은 추출로 오판된다(실측 33건 오탐).
    CODE_EXT = (".cs", ".py", ".ts", ".js", ".go", ".java", ".cpp", ".c", ".rs")
    semantic_by_src = collections.Counter(norm(n.get("source_file")) for n in nodes
                                          if not norm(n.get("source_file")).lower().endswith(CODE_EXT))
    edge_by_src = collections.Counter(norm(e.get("source_file")) for e in links)

    # 1. 좀비
    gone = [s for s in node_by_src if s and not os.path.exists(s)]
    zombie_nodes = sum(node_by_src[s] for s in gone)
    zombie_edges = sum(edge_by_src.get(s, 0) for s in gone)

    # 2. 누적층
    latest = load_latest_cache_counts(os.path.join(args.out_dir, "cache"))
    # 좀비 파일은 1번 축에서 이미 전량 계상됐다 — 여기서 또 세면 이중 계산이다.
    stacked = []
    for s, cnt in semantic_by_src.items():
        if s in gone:
            continue
        if s in latest and cnt > latest[s]:
            stacked.append((s, cnt, latest[s]))
    stacked_nodes = sum(a - b for _, a, b in stacked)

    # 3. 라벨 중복
    dup = collections.Counter((norm(n.get("source_file")), n.get("norm_label") or n.get("label"))
                              for n in nodes)
    dup_pairs = [k for k, v in dup.items() if v > 1]
    dup_extra = sum(dup[k] - 1 for k in dup_pairs)

    # 4. 얕은 추출 (문서만 대상 - 코드/이미지/PDF 는 밀도 기준이 다르다)
    thin = []
    densities = []
    for s_, cnt in semantic_by_src.items():
        if s_ in gone or not s_ or not os.path.exists(s_):
            continue
        if s_.lower().endswith((".png", ".jpg", ".jpeg", ".svg", ".pdf")):
            continue
        kb = os.path.getsize(s_) / 1024
        if kb <= 0:
            continue
        d = cnt / kb
        densities.append(d)
        if kb >= args.thin_min_kb and d < args.thin_under:
            thin.append((s_, cnt, kb, d))
    thin.sort(key=lambda x: -x[2])

    dirty = zombie_nodes + stacked_nodes
    pct = (dirty / total * 100) if total else 0.0

    print(f"그래프: {total} 노드 · {len(links)} 엣지  ({gpath})")
    print()
    print(f"1. 좀비 (디스크에 없는 source_file)  : {zombie_nodes:5d} 노드 · {zombie_edges:5d} 엣지 · {len(gone)} 파일")
    for s in sorted(gone, key=lambda x: -node_by_src[x])[:args.list]:
        print(f"      {node_by_src[s]:4d}  {s}")
    print()
    if latest:
        print(f"2. 누적층 (그래프 > 최신 추출)      : {stacked_nodes:5d} 노드 · {len(stacked)} 파일")
        for s, a, b in sorted(stacked, key=lambda x: -(x[1] - x[2]))[:args.list]:
            print(f"      그래프 {a:4d} / 최신 {b:4d}   {s}")
    else:
        print("2. 누적층                           : 캐시 없음 — 측정 불가 (재빌드 직후면 정상)")
    print()
    print(f"3. 같은 파일 내 라벨 중복           : {dup_extra:5d} 잉여 노드 · {len(dup_pairs)} 라벨")
    for k in sorted(dup_pairs, key=lambda x: -dup[x])[:args.list]:
        print(f"      {dup[k]}회  {k[1]}  ({k[0]})")
    print()
    if densities:
        densities.sort()
        med = densities[len(densities) // 2]
        thin_kb = sum(x[2] for x in thin)
        print(f"4. 얕은 추출 (< {args.thin_under} 노드/KB)      : {len(thin):5d} 문서 · {thin_kb:.0f}KB"
              f"  (중앙값 {med:.2f} 노드/KB)")
        for s_, cnt, kb, d in thin[:args.list]:
            print(f"      {d:5.2f} 노드/KB  {cnt:3d}노드  {kb:6.1f}KB  {s_}")
    print()
    print(f"오염 추정: {dirty} / {total} 노드 = {pct:.1f}%")
    if thin:
        print(f"누락 추정: 얕은 문서 {len(thin)}개 — 재추출 대상")

    if args.fail_over is not None and pct > args.fail_over:
        print(f"임계값 {args.fail_over}% 초과", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
