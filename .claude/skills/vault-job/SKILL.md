---
name: vault-job
description: >
  Unity 개발 작업(Job) 단위의 컨텍스트를 생성, 추적, 완료 처리하는 스킬.
  작업 시작/재개/완료 시 사용. vault의 지식을 자동으로 연결하고 세션 간 작업 상태를 유지.
  "작업 시작해줘", "job 만들어줘", "vault-job", "이 작업 추적해줘",
  "어디까지 했는지 기록해줘", "작업 재개", "이어서 해줘", "job 완료",
  "작업 끝났어", "다음 세션에서 이어할게" 등의 요청 시 반드시 이 스킬을 사용.
  vault-load, vault-sync, obsidian-cli 스킬과 함께 사용.
---

# vault-job

Job = 완료 조건이 있는 하나의 작업 단위.
지식을 쌓는 vault와 달리, Job은 시작-진행-완료의 생명주기를 가짐.

여러 job이 동시에 active 상태일 수 있으며, 각 job은 생성 시 등록한
scope(파일, 키워드, vault 문서)를 기반으로 vault-sync와 연동됨.

## 명령어 구조

```
vault-job start "작업 이름"        → 새 job 시작 + scope 자동 생성
vault-job start [문서 첨부]        → 첨부 문서 기반으로 job 자동 구성
vault-job resume [slug]            → 특정 job 재개 (생략 시 목록 선택)
vault-job log "내용" [slug]        → 특정 job의 history에 시간순 엔트리 추가
vault-job scope [slug]             → 특정 job의 scope 확인/수정
vault-job done [slug]              → 특정 job 완료 처리
vault-job list                     → active/done job 목록 조회
```

---

## vault-job start

### 사전 조건
- `vault/` 존재 확인 → 없으면 `/vault-init` 먼저 실행 안내
- active job이 이미 있어도 경고 없이 추가 생성 가능 (다중 job 지원)

### 입력 모드 판단

vault-job start 실행 시 입력 형태에 따라 두 가지 모드로 분기:

```
모드 A: 작업명만 있는 경우
  → "vault-job start 보스 2페이즈 구현"
  → 작업명 기반 자동 추출

모드 B: 문서가 첨부된 경우
  → 기획서, 태스크 문서, 이슈 티켓 등 첨부
  → 문서 내용 기반 자동 구성
```

---

### 모드 A: 작업명 기반 자동 추출

**Step 1: 작업명에서 scope 자동 추출**

작업명을 분석하여 scope 전체를 자동으로 생성:

```
입력: "보스 2페이즈 구현"

[scope_keywords 자동 추출]
- 작업명 토큰화: ["보스", "2페이즈", "구현"]
- 영어 대응어 추가: ["boss", "phase", "2", "implement"]
- Unity 도메인 확장:
    "보스/boss" → + ["enemy", "AI", "combat", "monster"]
    "페이즈/phase" → + ["FSM", "StateMachine", "transition", "stage"]
    "구현" → 제거 (동사, 노이즈)
- 최종: ["boss", "phase", "FSM", "StateMachine", "AI", "enemy"]

[scope_files 후보 자동 탐색]
- 추출된 키워드로 프로젝트 파일 검색:
  find Assets/ -name "*.cs" | xargs grep -l "boss\|Boss\|phase\|Phase" 2>/dev/null
- 발견된 파일 목록을 후보로 제시

[scope_vault 자동 연결]
- 키워드로 vault/_index.base 검색
- 관련 vault 문서 자동 등록
```

**Step 2: 자동 추출 결과 확인 요청**

```
🔍 scope 자동 추출 결과: "보스 2페이즈 구현"
────────────────────────────────────────
🏷️  키워드 (자동):
   boss, phase, FSM, StateMachine, AI, enemy
   수정할 키워드가 있으면 입력 (없으면 엔터):
→

📁 관련 파일 후보 (자동 탐색):
   [v] Assets/Scripts/Boss/BossController.cs
   [v] Assets/Scripts/Boss/BossPhaseManager.cs
   [ ] Assets/Scripts/Enemy/EnemyBase.cs       ← 관련 없으면 제외
   제외할 번호 입력 (없으면 엔터):
→

📚 vault 연결 (자동):
   [[event-system]], [[coding-style]]
   추가할 vault 문서가 있으면 입력 (없으면 엔터):
→
```

**Step 3: 완료 조건 수집**

```
✅ 완료 조건을 체크리스트로 작성해주세요 (없으면 엔터):
→
```

---

### 모드 B: 문서 첨부 기반 자동 구성

기획서, 태스크 문서, 이슈 티켓, 스프린트 카드 등 개발 문서를 첨부하면
문서 내용을 분석하여 job 전체를 자동으로 구성.

**Step 1: 문서 분석**

첨부 문서에서 아래 항목을 추출:

```
추출 대상:
- 작업명 / 제목
- 작업 배경 및 목적
- 구현 범위 (어떤 기능, 어떤 시스템)
- 완료 조건 / 인수 조건 / Done 기준
- 관련 파일 언급 (클래스명, 씬명, 프리팹명 등)
- 기술 키워드 (패턴, 컴포넌트, 패키지명 등)
- 참고 자료 / 관련 문서 언급
```

**Step 2: 자동 구성 결과 제시**

```
📄 문서 분석 완료: "보스전_기획서_v2.pdf"
────────────────────────────────────────
📌 작업명 (추출):
   "보스 2페이즈 구현 및 연출 추가"
   수정: →

🏷️  키워드 (추출):
   boss, phase, FSM, Cinemachine, ShakeEffect, HealthBar
   수정: →

📁 관련 파일 후보 (문서 언급 + 프로젝트 탐색):
   [v] Assets/Scripts/Boss/BossController.cs
   [v] Assets/Scripts/Boss/BossPhaseManager.cs
   [v] Assets/VFX/BossPhaseTransition.prefab
   [ ] Assets/Scripts/UI/HealthBar.cs         ← 관련 없으면 제외
   수정: →

✅ 완료 조건 (추출):
   - [ ] 체력 50% 도달 시 페이즈 2 자동 전환
   - [ ] 페이즈 전환 시 카메라 셰이크 연출
   - [ ] 페이즈 2 전용 공격 패턴 3종 구현
   - [ ] 보스 체력바 페이즈 구분 표시
   수정: →

📚 vault 연결 (자동):
   [[event-system]], [[coding-style]], [[scene-hierarchy]]
   추가: →

📋 작업 범위 (추출):
   "보스 FSM에 페이즈 2 상태 추가. Cinemachine으로
    전환 연출 구현. UI 체력바 페이즈 색상 구분."
   수정: →

────────────────────────────────────────
위 내용으로 job을 생성할까요? (y/수정항목번호)
```

**Step 3: 확인 후 job 생성**

사용자가 `y` 입력 시 즉시 job 문서 생성.
수정 필요 시 해당 항목만 재입력.

---

### 공통: job 생성 및 시작 출력

job 은 **파일 두 개**로 생성한다. 구조는 템플릿을 그대로 따른다:

| 파일 | 템플릿 | 성격 |
|------|--------|------|
| `jobs/<slug>.md` | `vault/_templates/job.md` | 라이브 — 지금의 상태, **갱신(교체)** |
| `jobs/<slug>.history.md` | `vault/_templates/job-history.md` | 로그 — 시간순, **추가만** |

라이브 문서에 `## 진행 기록` 섹션을 만들지 않는다. 시간순 기록의 목적지는 history 하나뿐이다.

두 모드 모두 확인 완료 후 동일한 출력:

```
🚀 job 시작: "보스 2페이즈 구현"
────────────────────────────────────────
파일: vault/jobs/2025-04-11-boss-phase2.md
      vault/jobs/2025-04-11-boss-phase2.history.md

scope:
  📁 파일 (2개): BossController.cs, BossPhaseManager.cs
  🏷️  키워드: boss, phase, FSM, StateMachine, AI
  📚 vault: [[event-system]], [[coding-style]]

완료 조건:
  - [ ] 체력 50% 이하 시 페이즈 2 전환
  - [ ] 페이즈 전환 이벤트 발행

────────────────────────────────────────
vault-sync 실행 시 scope 기반으로 이 job이 자동 연결됩니다.
```

---

## vault-job resume

slug 인자가 있으면 해당 job 즉시 로드.
없으면 active job 목록 출력 후 선택:

```
📂 active job 목록:
  [1] 보스 2페이즈 구현     2025-04-11 시작 (3일 경과)  boss, FSM
  [2] 로그인 UI 수정        2025-04-13 시작 (1일 경과)  UI, login
재개할 job 번호를 선택하세요 (복수 선택 가능: 1,2):
```

복수 선택 시 선택된 job들의 컨텍스트를 모두 로드.

재개 시 출력:

**로드 대상** — 문서 종류에 따라 읽는 방식이 다르다 (`vault-load` Step 4-bis 의 FULL/INDEX 판정과 동일).

| 파일 | 로드 |
|------|------|
| `<slug>.md` (라이브) | **FULL** — 통째로 |
| `<slug>.history.md` | 판정에 맡긴다 — 300줄 미만이면 FULL, 넘으면 **INDEX** |
| `scope_vault` 의 문서 전부 | **항상 INDEX** (프론트매터 + 섹션 목록). 코드 작업 의도가 보이면(`"이어서 구현"` `"마저 작성"` 등) FULL |

history 의 섹션 제목이 곧 시간순 요약이므로, INDEX 로 잡혀도 본문 없이 최근 흐름을 보여줄 수 있다.
작은 history 는 통째로 읽는 편이 인덱스보다 싸므로 임계값 판정에 맡긴다.

```
🔄 job 재개: "보스 2페이즈 구현"
────────────────────────────────────────
시작일: 2025-04-11 (3일 경과)

📍 현재 상태
  FSM 기본 구조 완성. 다음: 페이즈 전환 이벤트 연결

🔴 미해결 · 블로커
  EventBus.Publish() 연결 미완료

완료 조건:
  ✅ 체력 50% 이하 시 페이즈 2 전환
  ⬜ 페이즈 전환 이벤트 발행

📚 scope_vault (3)
  architecture/accessory-value-units   [INDEX 412줄 · 섹션 31]
  architecture/party-cost-ui-pattern   [INDEX 318줄 · 섹션 24]
  debugging/enhanced-scroller-pitfalls [FULL 96줄]

🕘 최근 기록 (boss-phase2.history — 제목만, 전체는 "history 보여줘")
  2025-04-12 — BossController FSM 기본 구조 완성
  2025-04-11 (2) — 페이즈 판정 임계값 결정
  2025-04-11 — 초기 설계
────────────────────────────────────────
```

`현재 상태`·`미해결 · 블로커` 는 라이브 문서에서 **그대로** 가져온다.
이 두 섹션이 최신이 아니면 그건 vault-sync 가 갱신을 빠뜨린 것이지, resume 이 추론으로 메울 일이 아니다.

**컨벤션은 resume 이 로드하지 않는다.** `.claude/settings.json` 의 `UserPromptSubmit` 훅이
프롬프트 키워드(`구현` `작성` `수정` `코드` `class` `async` `.cs` 등)를 보고
`ClientDocs/CodingConvention/` 5종을 자동 주입한다. 여기서 또 읽으면 중복이다.

**scope_vault 문서는 매 resume 에 인덱스로 올린다.** 라이브 · history · scope_vault 문서를 한 번에 넘긴다:

    python .claude/skills/vault-load/scripts/build_section_index.py vault/jobs/<slug>.md vault/jobs/<slug>.history.md vault/<folder>/<name>.md ...

인덱스는 문서당 25줄 안팎이라 비용이 작고, 작업 중에 생긴 지식이 매번 눈에 들어온다.
코드 작업 의도가 보이면 scope_vault 문서를 FULL 로 올린다. 단순 조회면 인덱스에서 멈춘다.
scope_vault 가 `[]` 이거나 `# unresolved:` 주석만 있으면 그 사실을 출력에 적는다 — 연결이 끊긴 job 이다.

**복수 선택 시** 각 job 의 라이브 문서를 FULL 로 모두 로드한다.
라이브가 `--job-warn`(600줄)을 넘으면 롤오버가 밀린 것이므로 경고를 함께 출력한다.

---

## vault-job log

active job이 1개면 자동으로 해당 job에 기록.
active job이 여러 개면 slug 인자 또는 선택 요청:

```
📝 어느 job에 기록할까요?
  [1] 보스 2페이즈 구현
  [2] 로그인 UI 수정
→
```

시간순 엔트리는 **history 파일**에 추가한다 — 라이브 job 문서가 아니다.

```powershell
# Obsidian CLI는 PowerShell 도구로 호출, vault="vault" 명시 (git-bash 금지 — GUI로 샘)
obsidian vault="vault" append file="2025-04-11-boss-phase2.history" content="\n### YYYY-MM-DD — 한 줄 요약\n- BossController FSM 구조 결정"
```
CLI 미사용 시 Read/Write 도구로 history 문서를 직접 편집 (폴백).
history 파일이 없으면 먼저 만든다 (frontmatter `tags: [job-history]`, `job: <slug>`).

**라이브 job 문서에는 날짜 엔트리를 추가하지 않는다.** 라이브는 "지금의 상태"만 담고,
`## 현재 상태` `## 최신 결정` `## 작업 플로우` `## 미해결 · 블로커` 는 누적이 아니라 **교체**한다.
이번 기록이 그 상태를 바꿨다면 해당 섹션을 갱신하고, 아니면 history 추가만으로 끝낸다.
갱신은 덧붙이기가 아니다. `▶` 문단은 하나뿐이라 이전 것을 지우고 쓰고, 해소된 미해결은 줄째 지운다.
라이브를 고쳤으면 `python .claude/skills/vault-sync/scripts/lint_job_live.py "vault/jobs/<slug>.md"` 로 확인한다
(규칙 상세는 vault-sync 「교체의 구체 동작」).

완료 조건 체크박스 업데이트가 필요한 경우 함께 처리 (라이브 문서).

---

## vault-job scope

특정 job의 scope 확인 및 수정.
작업 도중 범위가 바뀐 경우 사용.

```
📎 현재 scope: boss-phase2
  파일: Assets/Scripts/Boss/
  키워드: boss, FSM, phase, AI
  vault: [[event-system]], [[coding-style]]

수정할 항목 (files/keywords/vault/없음):
→
```

---

## vault-job done

slug 인자 없으면 미완료 job 목록(`status` 가 `done`·`cancelled` 가 아닌 것)에서 선택.

**Step 1**: 미완료 항목 경고
**Step 2**: 완료 메모 수집
**Step 3**: vault-sync 자동 호출 (이 job의 scope 전달)
**Step 4**: frontmatter 갱신 — **파일을 옮기지 않는다**
```
vault/jobs/2025-04-11-boss-phase2.md
  status: in-progress → done
  completed: YYYY-MM-DD
```
history 문서는 손대지 않는다 (status 필드가 없다).

**job 문서는 생성 위치에서 절대 이동하지 않는다.** 완료 여부의 유일한 근거는 frontmatter `status` 다.
경로가 바뀌면 graphify 지식그래프가 옛 경로 노드를 지우지 못해 같은 job 이 두 벌로 남는다
(2026-09-09 실측: 이동 38쌍 · 좀비 노드 412개). 폴더 분류를 되살리지 말 것.
**Step 5**: 완료 출력

---

## vault-job list

```
📋 job 목록
────────────────────────────────────────
active (2):
  🔄 보스 2페이즈 구현     2025-04-11 시작  boss, FSM, phase
  🔄 로그인 UI 수정        2025-04-13 시작  UI, login

done (3):
  ✅ iOS 빌드 크래시 수정  2025-04-10 (2일 소요)
  ✅ 인벤토리 시스템 구현  2025-04-01 (5일 소요)
────────────────────────────────────────
```

---

## vault 폴더 구조

```
vault/
  jobs/       ← 모든 job 문서 (진행중·완료 구분 없이 한 폴더, 다중 허용)
```

진행 상태는 폴더가 아니라 frontmatter `status` 로만 구분한다 (`vault/conventions/job-status-values.md`).
`vault-job list` 는 `status` 를 읽어 분류하고, `vault-load` 의 라이브 판정도 같은 값을 본다.

## 참고 파일

- `references/job-template.md` → job 문서 초기 템플릿
- `references/doc-analysis-guide.md` → 문서 유형별 분석 가이드
