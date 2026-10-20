---
name: vault-load
description: >
  작업 시작 시 vault에서 관련 문서를 검색하여 현재 세션 컨텍스트로 로드하는 스킬.
  "vault 로드해줘", "vault-load", "관련 컨벤션 불러와줘", "오늘 작업 컨텍스트 세팅",
  "vault에서 찾아줘", "관련 문서 로드", "컨텍스트 준비해줘",
  세션 시작 시 작업 내용을 말하며 vault 참조를 요청할 때 반드시 이 스킬을 사용.
  obsidian-cli 스킬과 함께 사용하면 더 좋은 결과를 얻을 수 있음.
---

# vault-load

작업 키워드를 기반으로 vault에서 관련 문서를 찾아 현재 세션의 컨텍스트로 로드.
CLAUDE.md를 수정하지 않으며, 세션 내에서만 유효.
주 읽기 경로는 vault-job resume 이다. vault-load 는 job 이 없는 새 주제를 찾을 때 쓴다.

링크 기반 검색을 기본 탐색 수단으로 사용한다. Graphify는 사용자가 명시할 때만 선택한다.
코딩 컨벤션(`coding-style.md`)은 CLAUDE.md에서 항상 주입되므로 이 스킬에서 로드하지 않는다.

## 사전 조건 확인

1. `vault/` 폴더 존재 여부 확인 → 없으면 `/vault-init` 먼저 실행 안내
2. `vault/` 내 MD 파일 존재 여부 확인
3. (선택) graphify 모드를 쓰려면 `graphify-out/graph.json` 존재 확인

## 실행 단계

### Step 1: (삭제됨 — 이 자리는 비워 둔다. job 이 있으면 vault-load 대신 vault-job resume 을 쓴다)

### Step 2: 작업 의도 파악

사용자 입력에서 키워드 추출:

```
입력 예시: "/vault-load 보스 AI 구현"
추출 키워드: ["보스", "AI", "구현", "enemy", "FSM", "StateMachine"]
→ 관련 확장 키워드도 함께 고려
```

키워드가 없는 경우 ("vault-load" 단독):
- vault-load 단독 실행은 아무것도 로드하지 않는다. 진행 중 job 이 있으면 /vault-job resume 을 안내하고 끝낸다.

### Step 3: 문서 탐색 (링크 기반 모드가 기본)

링크 기반 모드가 1순위다. Graphify 모드는 `graphify-out/graph.json` 이 있고 사용자가 명시할 때만 쓴다.

#### 링크 기반 모드 (기본)

```powershell
python .claude/skills/vault-load/scripts/vault_search.py `
    키워드1 키워드2 키워드3
```

기본 검색 대상은 지식 문서와 라이브 job 이다. handoff · evidence · daily · weekly 까지 찾으려면
`--include-records` 를 넘긴다. 개수를 바꾸려면 `--kw-limit` / `--graph-limit` 를 넘긴다.

**출력 해석**

```
# 탭 구분: <버킷>\t<점수>\t<이웃수 또는 ->\t<vault_relative_path>
KW       3    -    vault/architecture/event-system.md
GRAPH    0    2    vault/conventions/probability-feature-verification.md
```

| 필드 | 의미 |
|------|------|
| 버킷 | `KW` = 키워드 매칭 / `GRAPH` = KW 상위 문서의 wikilink 이웃 |
| 점수 | KW 의 키워드 점수 (GRAPH는 항상 0) |
| 이웃수 | GRAPH 문서와 연결된 KW 상위 문서 수 (KW는 `-`) |

출력된 줄이 곧 로드 후보다. 출력 형식이 Graphify 모드와 같으므로 Step 4 이하는 그대로 따른다.
그래프 추출 토큰이 0 이고 스냅샷이 아니라 최신성 경고(Step A-bis)가 필요 없다.

**종료 코드별 처리**

| 코드 | 의미 | 처리 |
|------|------|------|
| 0 | 결과 있음 | 출력된 경로 사용 |
| 1 | 오류 | **폴백 모드** 전환 |
| 2 | vault 매칭 없음 | **폴백 모드** 전환 |

#### Graphify 모드 (`graphify-out/graph.json` 존재 시)

graphify는 독립 CLI가 아니라 Python 패키지(`graphifyy`)다.
`scripts/graphify_query.py`를 통해 graph.json을 직접 탐색한다.

**그래프는 확장 전용이다.** 키워드에 매칭된 문서는 BFS 도달 여부와 무관하게 후보로 남고,
BFS는 키워드가 없는 연관 문서를 *추가로* 끌어오는 역할만 한다.
결과는 `KW`(키워드 매칭)와 `GRAPH`(그래프 유입) 두 버킷으로 분리되어 각각 별도 쿼터를 갖는다 —
그래프가 발굴한 연관 문서가 키워드 상위권에 밀려 전부 탈락하지 않게 하기 위함이다.

**Step A — 스크립트 실행 (PowerShell tool)**

```powershell
python .claude/skills/vault-load/scripts/graphify_query.py `
    graphify-out/graph.json `
    키워드1 키워드2 키워드3
```

키워드는 Step 2에서 추출한 한글/영문 용어를 공백으로 나열한다.
예: `python .claude/skills/vault-load/scripts/graphify_query.py graphify-out/graph.json 성장 미션 GrowthMission`

**출력 해석**

```
# 탭 구분: <버킷>\t<점수>\t<홉>\t<vault_relative_path>
KW       3    0    vault/jobs/2026-04-28-character-growth-mission.md
KW       2    0    vault/prd/character-growth-mission-prd.md
KW       1    -    vault/conventions/reward-popup-pattern.md
GRAPH    0    2    vault/architecture/event-system.md
```

| 필드 | 의미 |
|------|------|
| 버킷 | `KW` = 키워드 매칭 / `GRAPH` = 키워드 없이 그래프 연결로만 유입 |
| 점수 | 매칭된 키워드 개수 (GRAPH는 항상 0) |
| 홉 | 시작 노드로부터의 최단 거리. `-` 는 BFS 미도달(키워드로만 매칭) |

출력된 줄이 곧 로드 후보다 — 스크립트가 이미 쿼터(KW 4개 + GRAPH 2개)를 적용해서 내보낸다.
개수를 바꾸려면 `--kw-limit` / `--graph-limit` 를 넘긴다.

랭킹은 **키워드 점수 ↓ → 홉 거리 ↑ → 경로** 순이며, 마지막 경로 키가 동점을 확정해
같은 쿼리가 항상 같은 문서를 반환한다.

**종료 코드별 처리**

| 코드 | 의미 | 처리 |
|------|------|------|
| 0 | 결과 있음 | 출력된 경로 사용 |
| 1 | 오류 (graph.json 없음 / networkx 없음) | **폴백 모드** 전환 |
| 2 | vault 매칭 없음 | **폴백 모드** 전환 |

**Step A-bis — 그래프 최신성(staleness) 확인 (PowerShell tool, 항상 실행)**

graph.json은 스냅샷이라 마지막 생성 이후 vault가 바뀌어도 조용히 낡은 결과를 낸다.
이를 침묵 없이 드러내기 위해 매 Graphify 모드 탐색마다 드리프트를 확인한다.

```powershell
powershell -ExecutionPolicy Bypass -File ".claude/skills/vault-load/scripts/check_graphify_staleness.ps1"
```

출력: `DRIFT=<n> MODIFIED=<n> NEW=<n> THRESHOLD=<n> STALE=<true|false>` (드리프트 있으면 변경 파일 목록 추가 출력).
`NO_MANIFEST`(exit 1) 이면 이 확인을 건너뛴다 (manifest.json 자체가 없는 초기 상태).

기본 manifest는 Step A가 조회하는 `graphify-out/graph.json` 과 **같은 실행분**인
`graphify-out/manifest.json` 이다. 다른 실행분의 manifest를 보면 드리프트 수치가 통째로 무의미해진다.
`MANIFEST_OLDER_THAN_GRAPH` 라인이 출력되면 짝이 어긋난 상태이므로,
드리프트 수치를 신뢰하지 말고 `/graphify vault --update` 재생성을 먼저 권고한다.

`STALE=true`이면 Step 5 출력에 경고 라인을 반드시 포함한다 (아래 "그래프 최신성 경고" 참조).
`STALE=false`이면 경고 없이 진행.

**Step B — God nodes 확인 (선택)**

Read tool로 `graphify-out/GRAPH_REPORT.md` 앞부분(limit=60)을 읽어
"God nodes" 섹션에 `vault/` 파일이 언급되면 로드 후보에 추가.
GRAPH_REPORT.md가 없으면 이 단계 생략.

#### 폴백 모드 (`graphify-out/graph.json` 없을 시)

**1순위: Obsidian CLI 검색 (Obsidian 실행 중인 경우)**
- ✅ **PowerShell 도구로** 호출 (Windows에서 `.com` CLI로 resolve). ❌ git-bash 금지(GUI로 샘). vault는 폴더 basename = `vault`.
```powershell
obsidian vault="vault" search query="키워드" limit=5
```
CLI 미설치/Obsidian 미실행 시 2순위(grep)로 폴백.

**2순위: 직접 파일 내용 검색**
```bash
grep -r "키워드" vault/ --include="*.md" -l
```

**3순위: 폴더 기반 추론**
```
키워드 → 폴더 매핑 예시:
"UI", "Canvas", "Panel", "Button" → conventions/, debugging/performance-fixes.md
"Physics", "Rigidbody", "Collider" → debugging/physics-issues.md
"Save", "Load", "Persistent" → architecture/save-system.md
"Event", "Message", "Broadcast" → architecture/event-system.md
"iOS", "Android", "Mobile" → debugging/mobile-specific.md
"ADR", "결정", "왜" → decisions/
"부채", "리팩토링", "TODO" → tech-debt/
```

### Step 4: 로드 대상 선정

```
KW 버킷 (최대 4개):
- 키워드 점수 높은 순. 스크립트가 이미 정렬·컷해서 내보냄

GRAPH 버킷 (최대 2개):
- 키워드에 안 걸렸지만 그래프로 연결된 문서. KW와 슬롯을 다투지 않는다
- 이 자리가 그래프 도입의 실효분이므로 KW가 부족해도 GRAPH를 먼저 버리지 않는다

제외 기준:
- confidence: low 이고 내용이 거의 없는 파일 (todo만 있는 경우)
- _templates/ 하위 파일
- graphify-out/ 하위 파일 (graphify가 자기 출력을 인덱싱한 것 — GRAPH_REPORT.md 등)
- conventions/coding-style.md (CLAUDE.md에서 항상 주입됨, 중복 로드 불필요)
```

### Step 4-bis: 인덱스 우선 로드 (본문 샘플링 금지)

본문을 잘라 담지 않는다. **프론트매터 + 섹션 목록**만 보유하고, 실제 내용은 질문이 왔을 때
해당 라인 범위만 인출한다. 문서 전체가 주소지정 가능해지므로 "중간 구간이 통째로 없는" 상태가 사라진다.

**절차**:

1. 선정된 파일 전체를 한 번에 인덱싱한다 (PowerShell tool):

```powershell
python .claude/skills/vault-load/scripts/build_section_index.py `
    vault/jobs/foo.md vault/architecture/bar.md
```

2. 출력의 판정을 그대로 따른다:

| 판정 | 처리 |
|------|------|
| `FULL` | `Read` 로 **통째로** 읽는다 (임계값 미만이거나 `jobs/` 라이브 문서) |
| `INDEX` | 프론트매터 + 섹션 목록만 보유. 본문은 읽지 않는다 |

3. `⚠️ 롤오버 권장` 이 붙은 라이브 job 문서는 진행 기록이 다시 비대해졌다는 뜻이다.
   Step 5 출력에 경고를 포함하고 `/vault-sync` 롤오버를 권고한다.

> **라이브 job 문서는 임계값과 무관하게 항상 FULL 이다.** 일반 문서 임계값(`--full-under` 300)을
> job 에 적용하면 안 된다 — 진행 기록을 다 비워도 완료 조건·조사 기록 같은 비-히스토리 상태만
> 279줄이라 구조적으로 통과가 불가능하다. job 은 별도 경고선(`--job-warn` 600)을 쓴다.

**왜 샘플링을 버렸나** — 실측 근거:

- head+tail 은 898줄 문서에서 **18%** 만 보유했다. 섹션 인덱스는 **75줄**로 문서 전체 주제를 주소지정한다.
- 200줄 이상 문서 72개 평균으로 현행 160줄 → 인덱스 **25줄**. 약 6배 싸다.
- 인덱스 생성은 선정 6개 기준 **4.9ms**(전체 222개도 48ms). 순수 정규식이라 캐시가 필요 없고,
  따라서 graphify 같은 staleness 문제가 이 계층엔 존재하지 않는다.
- 결정적으로, `jobs/2026-07-03-wargame-remake.md` 는 엔트리 순서가 08-13 → 07-31 → 08-03 으로
  뒤섞여 있어 **head 도 tail 도 최신 엔트리를 못 집었다.** 샘플링 위치 조정으로는 해결되지 않는다.

> **코드블록은 떼지 않는다.** vault 전체의 21%지만 job 문서에선 6%뿐이라 비대의 원인이 아니고,
> 블록 크기 중앙값이 6줄인데 내용이 API 시그니처·JSON 설정·흐름도라 줄당 정보밀도가 산문보다 높다.
> 떼면 21% 아끼고 가장 압축된 부분을 잃는다.

> **근거**: `vault/jobs/` 파일은 시간순 누적 구조라 하단(최신 엔트리)이 가장 가치 높고,
> frontmatter 가 메타데이터 전체를 담는다. 중간 섹션은 대부분 과거 진행 로그다.

### Step 5: 컨텍스트 선언

로드 결과 출력:

```
📂 vault-load 완료: "보스 AI 구현"
────────────────────────────────────────
🔍 탐색 방식: Graphify(키워드+그래프 확장) / 폴백(grep)

[키워드] architecture/event-system.md
  → 이벤트 버스 패턴, 보스 페이즈 전환에 활용 가능
  → 연결 문서: [[architecture/game-manager-pattern]]

[키워드] jobs/2026-04-28-growth-mission.md [FULL 287줄]
  → 라이브 job 문서 — 전체 로드됨

[키워드] architecture/wargame-turn-simulation.md [INDEX 898줄 · 섹션 75개]
  → 프론트매터 + 섹션 목록 보유. 질문 시 해당 섹션만 인출

[연관←2홉] conventions/probability-feature-verification.md
  → 키워드에는 없지만 그래프로 연결됨 — 확률 기능 검증 절차

────────────────────────────────────────
⚠️  graph.json 없음 — /graphify . 실행 시 탐색 정확도가 향상됩니다.
(graph.json 있으면 이 줄 표시 안 함)
⚠️  graph.json이 최신 변경 9건을 반영 못했습니다 (드리프트 9건 ≥ 임계값 5) — /graphify vault --update 권장
(Step A-bis에서 STALE=false 이면 이 줄 표시 안 함)
⚠️  manifest가 graph.json보다 오래됨 — 드리프트 수치를 신뢰할 수 없습니다. 재생성 권장
(MANIFEST_OLDER_THAN_GRAPH 출력 시에만 표시)
────────────────────────────────────────
이 세션에서 위 컨텍스트를 참고하여 작업합니다.
작업 종료 후 /vault-sync 를 실행하세요.
```

두 경고는 서로 배타적이지 않다 — graph.json이 아예 없으면 첫 줄만, 있는데 드리프트가 임계값 이상이면 둘째 줄만, 둘 다 해당 없으면 경고 섹션 전체 생략.

키워드 없이 단독 실행한 경우:
```
📂 vault-load 완료
────────────────────────────────────────
────────────────────────────────────────
이 세션에서 위 컨텍스트를 참고하여 작업합니다.
작업 종료 후 /vault-sync 를 실행하세요.
```

### Step 6: 로드된 내용 실제 읽기

Step 4-bis 의 판정을 그대로 따른다:
- `FULL` 문서: `Read` 로 전체 취득
- `INDEX` 문서: 프론트매터 + 섹션 목록만 보유. **본문은 이 시점에 읽지 않는다**

### Step 7: 로드 이후 응답 규칙 (필수)

vault-load 의 목적은 "읽어두는 것"이 아니라 **이후 질문에 재검색 없이 답하는 것**이다.
로드 이후 vault 관련 질문을 받으면 아래 순서를 지킨다.

1. **먼저 이미 로드된 내용에서 답을 찾는다.** 답이 있으면 파일을 다시 열지 말고 즉시 답한다.
   근거 위치는 `문서명 — 섹션명` 으로 밝힌다.
2. `INDEX` 문서라면 **섹션 목록에서 해당 섹션을 고른다.** 제목만으로 답할 수는 없으므로,
   고른 섹션의 라인 범위를 `Read offset=<L-1>, limit=<다음 섹션까지>` 로 인출한 뒤 답한다.
   - 인접 섹션에 답이 걸쳐 있는 구조(`### 문제` / `### 해법`)가 흔하므로,
     매칭된 섹션과 **그 하위 `###` 전부**를 함께 가져온다
   - 섹션 1개 중앙값이 10줄이라 2~3개를 가져와도 비용이 작다
3. 섹션 목록에도 해당 주제가 없으면 → 로드되지 않은 문서에 있을 수 있다. 키워드를 바꿔 재탐색한다.
4. **이미 인출한 섹션을 재확인하려고 같은 범위를 다시 읽지 않는다.** 이미 컨텍스트에 있다.

> `INDEX` 문서는 "무엇이 어디 있는지"만 보유한 상태다.
> 섹션 목록에 있는데 아직 안 읽었으면 **"문서에 없음"이 아니라 "아직 인출하지 않음"** 이다 — 읽고 답한다.
> 이 둘을 구분하지 않으면 vault에 있는 내용을 없다고 답하게 된다.

## 로드 판단 예시

| 작업 의도 | 추가 로드 문서 |
|----------|---------------|
| 키워드 없음 ("vault-load") | 없음 |
| "보스 AI FSM 구현" | event-system + game-manager-pattern |
| "UI 최적화" | performance-fixes + scene-hierarchy |
| "모바일 빌드" | mobile-specific + asset-management |
| "새 기능 설계" | event-system + decisions/ |
| "버그 잡기" | 로드됨 | 증상 관련 debugging 문서 |

## 컨텍스트 활용 방식

### 코드 작성 / 설계 요청 시

코딩 컨벤션은 CLAUDE.md를 통해 항상 주입되므로 별도 로드 불필요.
vault-load는 작업 관련 아키텍처/디버깅/결정 문서에 집중한다.

- vault에 없는 결정이 필요한 경우 → "이 부분은 vault에 기록이 없습니다. 어떻게 하시겠습니까?" 질문

### 버그 해결 요청 시

- debugging 문서에서 유사 사례 먼저 확인
- 없으면 일반 디버깅 진행 후 vault-sync에서 저장 제안
