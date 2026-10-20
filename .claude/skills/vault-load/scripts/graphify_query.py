#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vault-load graphify query helper

graph.json을 networkx로 로드하여 키워드 매칭 + 그래프 확장 탐색을 수행하고
파일 경로를 관련도 순으로 출력한다.

그래프는 **확장 전용**이다 — 키워드에 매칭된 파일은 BFS 도달 여부와 무관하게
전부 후보로 남고, BFS는 키워드가 없는 연관 문서를 추가로 끌어오는 역할만 한다.
(이전 구현은 BFS 미도달 매칭을 버려서 후보가 최대 77% 유실됐다.)

결과는 두 버킷으로 분리 출력한다:
    KW    - 키워드 매칭 문서 (기본 상위 4개)
    GRAPH - 키워드 없이 그래프 연결로만 유입된 문서 (기본 상위 2개)

사용법:
    python graphify_query.py <graph_json_path> <keyword1> [keyword2 ...]
    python graphify_query.py <graph_json_path> --path-filter ClientDocs/ <keyword1> [keyword2 ...]
    python graphify_query.py <graph_json_path> --kw-limit 4 --graph-limit 2 <keyword1> ...
    python graphify_query.py <graph_json_path> --god-nodes [N]

출력 형식 (탭 구분, 경로가 항상 마지막 필드):
    키워드 모드:    <bucket>\t<score>\t<hop>\t<relative_path>
                    bucket: KW | GRAPH
                    hop:    시작 노드로부터의 최단 홉 수, BFS 미도달이면 '-'
    God nodes 모드: <degree>\t<relative_path>

예시:
    # vault 탐색 (기본)
    python graphify_query.py graphify-out/graph.json 성장 미션 GrowthMission

    # 코딩 컨벤션 탐색
    python graphify_query.py graphify-out/convention-graph.json --path-filter ClientDocs/ UI Panel async

    # God nodes (참조 횟수 상위 N개 문서) — vault-evolve 정제 작업용
    python graphify_query.py graphify-out/graph.json --god-nodes 5

종료 코드:
    0 - 매칭 결과 있음
    1 - 오류 (graph.json 없음, import 실패 등)
    2 - 매칭 결과 없음 (폴백 모드 전환 신호)
"""

import sys
import json
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

# BFS 미도달을 나타내는 정렬용 센티넬 (실제 홉 수보다 항상 큼)
UNREACHED = 10**6


def score_node(ndata, terms, source_norm=None):
    """노드 하나의 키워드 매칭 점수 — label 과 source_file 양쪽을 본다."""
    label = ndata.get("label", "").lower()
    source = source_norm if source_norm is not None else ndata.get("source_file", "").lower()
    return sum(1 for t in terms if t in label or t in source)


def rel_path(source_file, path_filter):
    """source_file 을 path_filter 기준 상대경로로 정규화. 대상 밖이면 None."""
    if not source_file or not source_file.endswith(".md"):
        return None
    norm = source_file.replace("\\", "/")
    idx = norm.find(path_filter)
    if idx == -1:
        return None
    return norm[idx:]


def main():
    parser = argparse.ArgumentParser(description="graphify query helper")
    parser.add_argument("graph_json", help="Path to graph.json")
    parser.add_argument(
        "--path-filter",
        default="vault/",
        metavar="PREFIX",
        help="파일 경로 필터 prefix (기본값: vault/). 예: ClientDocs/CodingConvention/"
    )
    parser.add_argument(
        "--god-nodes",
        nargs="?",
        type=int,
        const=10,
        default=None,
        metavar="N",
        help="참조 횟수(degree) 상위 N개 문서를 출력 (기본 10). 키워드 대신 사용."
    )
    parser.add_argument("--kw-limit", type=int, default=4, help="키워드 매칭 문서 출력 개수 (기본 4)")
    parser.add_argument("--graph-limit", type=int, default=2, help="그래프 유입 문서 출력 개수 (기본 2)")
    parser.add_argument("--depth", type=int, default=3, help="BFS 탐색 깊이 (기본 3)")
    parser.add_argument("--starts", type=int, default=5, help="BFS 시작 노드 개수 (기본 5)")
    parser.add_argument("keywords", nargs="*", help="검색 키워드 (키워드 모드에서 1개 이상)")

    args = parser.parse_args()

    graph_path = Path(args.graph_json)
    path_filter = args.path_filter.replace("\\", "/")

    # graph.json 존재 확인
    if not graph_path.exists():
        print(f"ERROR: {graph_path} not found", file=sys.stderr)
        sys.exit(1)

    # networkx + graphify 임포트
    try:
        from networkx.readwrite import json_graph
    except ImportError:
        print("ERROR: networkx not available", file=sys.stderr)
        sys.exit(1)

    # graph.json 로드
    try:
        data = json.loads(graph_path.read_text(encoding="utf-8"))
        G = json_graph.node_link_graph(data, edges="links")
    except Exception as e:
        print(f"ERROR: failed to load graph: {e}", file=sys.stderr)
        sys.exit(1)

    # ── God nodes 모드 (참조 횟수 상위 문서) ─────────────────────────
    # vault-evolve 정제 작업: 가장 많이 연결된 핵심 문서를 우선 점검 대상으로 추출.
    if args.god_nodes is not None:
        file_degree: dict[str, int] = {}
        for nid, deg in G.degree():
            rel = rel_path(G.nodes[nid].get("source_file", ""), path_filter)
            if rel is None:
                continue
            # 한 파일에 여러 노드가 있으면 degree 합산 (문서 전체의 연결도)
            file_degree[rel] = file_degree.get(rel, 0) + deg

        if not file_degree:
            sys.exit(2)

        # 동점은 경로로 확정 — 실행마다 결과가 바뀌지 않게 한다
        top = sorted(file_degree.items(), key=lambda x: (-x[1], x[0]))[: args.god_nodes]
        for path, deg in top:
            print(f"{deg}\t{path}")
        sys.exit(0)

    # ── 키워드 모드 ──────────────────────────────────────────────────
    if not args.keywords:
        print("ERROR: 키워드 모드에는 키워드가 1개 이상 필요합니다 (또는 --god-nodes 사용)", file=sys.stderr)
        sys.exit(1)

    terms = [t.lower() for t in args.keywords]

    # ── 1단계: 전 노드 키워드 스코어링 ───────────────────────────────
    # 여기서 매칭된 파일은 이후 어떤 단계에서도 탈락하지 않는다 (확장 전용 원칙).
    scored = []          # BFS 시작점 선정용 (노드 단위)
    kw_files: dict[str, int] = {}   # 파일 → 최고 키워드 점수

    for nid, ndata in G.nodes(data=True):
        source_norm = ndata.get("source_file", "").lower()
        s = score_node(ndata, terms, source_norm)
        if s <= 0:
            continue
        scored.append((s, nid))
        rel = rel_path(ndata.get("source_file", ""), path_filter)
        if rel is not None and s > kw_files.get(rel, 0):
            kw_files[rel] = s

    if not scored:
        # 매칭 없음 → 폴백 신호
        sys.exit(2)

    # ── 2단계: BFS 확장 (홉 거리 기록) ───────────────────────────────
    # 시작점은 점수순, 동점은 노드 ID로 확정 → 실행마다 동일한 시작점.
    start_nodes = [nid for _, nid in sorted(scored, key=lambda x: (-x[0], x[1]))[: args.starts]]

    hops: dict[str, int] = {nid: 0 for nid in start_nodes}
    frontier = list(start_nodes)
    for level in range(1, args.depth + 1):
        next_frontier = []
        for n in frontier:
            for neighbor in G.neighbors(n):
                if neighbor not in hops:
                    hops[neighbor] = level
                    next_frontier.append(neighbor)
        frontier = next_frontier
        if not frontier:
            break

    # 파일 단위 최단 홉 집계
    file_hop: dict[str, int] = {}
    for nid, h in hops.items():
        rel = rel_path(G.nodes[nid].get("source_file", ""), path_filter)
        if rel is None:
            continue
        if h < file_hop.get(rel, UNREACHED):
            file_hop[rel] = h

    # ── 3단계: 합집합 후보 구성 + 버킷 분리 ──────────────────────────
    # KW    = 키워드 매칭 (BFS 도달 여부 무관)
    # GRAPH = 키워드 0점인데 BFS 로만 유입된 문서 (그래프의 순수 기여분)
    kw_bucket = [
        (rel, score, file_hop.get(rel, UNREACHED))
        for rel, score in kw_files.items()
    ]
    graph_bucket = [
        (rel, 0, h)
        for rel, h in file_hop.items()
        if rel not in kw_files
    ]

    if not kw_bucket and not graph_bucket:
        sys.exit(2)  # 결과 없음 → 폴백

    # 랭킹: 키워드 점수 ↓ → 홉 거리 ↑ → 경로 (동점 결정성 확보)
    kw_bucket.sort(key=lambda x: (-x[1], x[2], x[0]))
    graph_bucket.sort(key=lambda x: (x[2], x[0]))

    def fmt_hop(h):
        return "-" if h >= UNREACHED else str(h)

    for rel, score, h in kw_bucket[: args.kw_limit]:
        print(f"KW\t{score}\t{fmt_hop(h)}\t{rel}")
    for rel, score, h in graph_bucket[: args.graph_limit]:
        print(f"GRAPH\t{score}\t{fmt_hop(h)}\t{rel}")

    sys.exit(0)


if __name__ == "__main__":
    main()
