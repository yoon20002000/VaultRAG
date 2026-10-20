---
name: vault-sync
description: >
  현재 클로드 코드 세션에서 발생한 컨벤션 결정, 버그 해결, 아키텍처 변경사항을
  Obsidian vault MD 문서에 저장하는 스킬. 진행중인 job이 있으면 job 진행 기록도 함께 갱신.
  세션 종료 전, 컨텍스트 압축 전, vault-job done 호출 시 모두 이 스킬이 실행됨.
  "vault 저장해줘", "vault 업데이트", "vault-sync", "오늘 작업 내용 저장",
  "컨벤션 기록해줘", "결정사항 저장", "vault에 추가해줘",
  "컨텍스트 압축 전 저장", "세션 종료 전 저장" 등의 요청 시 반드시 이 스킬을 사용.
  obsidian-cli, obsidian-markdown 스킬과 함께 사용하면 더 좋은 결과를 얻을 수 있음.
---

# vault-sync

세션에서 발생한 의미 있는 내용을 vault와 진행중인 job 문서에 누적 저장하는 스킬.
클로드가 저장 여부를 단독 결정하지 않으며, 반드시 사람의 승인 후에만 저장.

세션 종료 시, 컨텍스트 압축(/compact) 전, vault-job done 호출 시 모두 이 스킬이 실행됨.

## 사전 조건 확인

1. `vault/` 폴더 존재 여부 확인 → 없으면 `/vault-init` 먼저 실행 안내
2. `vault/jobs/` 스캔 → 있는 job 전체 목록과 각 scope 로드
3. Obsidian CLI 사용 가능 여부 확인 (아래 "Obsidian CLI 호출 규칙" 참조) → 불가하면 Read/Write 도구로 직접 파일 수정 방식 폴백
4. vault-evolve 실행 필요 여부 확인 (PowerShell tool, 항상 실행 — 이번 세션 저장 여부와 무관)

```powershell
powershell -ExecutionPolicy Bypass -File ".claude/skills/vault-evolve/scripts/check_evolve_due.ps1"
```

출력: `DUE=<true|false> DAYS_SINCE=<n> LAST_DATE=<yyyy-MM-dd> PROMOTE_COUNT=<n> ...`
`DUE=true`이면 결과를 기억해 두었다가, 이번 sync가 저장할 내용 없이 조기 종료되든 정상 완료되든 **항상** 마지막에 아래 "vault-evolve 추천" 블록을 출력한다. `DUE=false`이면 아무것도 출력하지 않는다.

```
🌱 vault-evolve 추천
  마지막 실행: 2026-06-18 (35일 경과, 기준 7일)
  승격 후보: 0건 누적 (기준 3건)
  → /vault-evolve 실행을 권장합니다.
```

5. 진행 중 job 라이브 문서 전수 린트 (PowerShell tool, 항상 실행)

   python .claude/skills/vault-sync/scripts/lint_job_live.py --all

   ERROR 가 있는 문서는 Step 4 승인 목록에 「🧹 정리 항목」으로 올린다 — 이번 세션과 무관해도 올린다.
   편집 시점 훅만으로는 코드 쪽이 바뀌어 생긴 위반(삭제된 파일 서술 등)을 못 잡기 때문이다.

6. handoff 신규 문서 frontmatter 검사 (PowerShell tool, 항상 실행)

   python .claude/skills/vault-sync/scripts/lint_handoff.py --since <env 의 오늘 날짜>

   ERROR 가 있으면 Step 4 승인 목록에 「🧹 정리 항목」으로 올린다. frontmatter 가 없으면 `--fix` 를 제안한다.
   handoff 는 기록 문서라 그래프·evolve 대상이 아니지만, 분류(kind)·소속(job)이 없으면 Bases 에서 "기타" 로 뭉개진다.

## Obsidian CLI 호출 규칙

- ✅ Obsidian CLI는 **PowerShell 도구로** `obsidian ...` 호출 (Windows에서 `.com` CLI로 resolve됨)
- ❌ Bash 도구(git-bash)로 `obsidian` 호출 금지 → GUI(`Obsidian.exe`)로 새어 명령 무시됨
- vault는 폴더 basename으로 지정: 이 프로젝트는 `vault="vault"`
- CLI 미설치/Obsidian 미실행 시 → Read/Write 도구로 `vault/` 파일 직접 편집 (폴백, 정상)
- 상세: `vault-init/SKILL.md`의 "Obsidian CLI 호출 규칙" 섹션

## 실행 단계

### Step 1: 세션 분석

현재 세션 대화에서 두 가지를 동시에 감지:

**[A] vault 저장 후보** — 재사용 가능한 지식
```
감지 대상:
- 새로 합의된 코딩 컨벤션이나 규칙
- 해결된 버그 또는 에러 (원인 + 해결법 포함)
- 아키텍처 결정 (근거 포함)
- 발견된 기술 부채
- 패키지/플랫폼 특이사항

감지 제외:
- 단순 질문/답변
- 임시 코드 스니펫
- 사용자가 "저장하지 마" 라고 한 항목
```

**[B] job 매칭 후보** — active job이 있을 때만
```
감지 대상:
- 이 세션에서 완료한 작업 내용 (요약 수준)
- 완료 조건 체크박스 업데이트 필요 항목
- 다음 단계·막힌 부분 → 라이브 `## 현재 상태` / `## 미해결 · 블로커` 에 반영
  (별도 "인계 메모" 항목으로 덧붙이지 않는다 — 유지 섹션이 그 역할을 한다)

감지 제외:
- vault 저장 후보와 중복 항목 (vault에만 저장)
- 세부 구현 코드
```

### Step 2: scope 기반 job 매칭

active job이 있으면 각 job의 scope를 기준으로 감지된 내용을 매칭.

**매칭 판단 순서 (우선순위 순)**:

```
1. scope_files 매칭
   → 변경 내용이 job의 scope_files 내 파일/폴더와 관련 있는 경우
   → 가장 확실한 매칭. 자동 연결.

2. scope_keywords 매칭
   → 변경 내용에 job의 scope_keywords 중 1개 이상 포함된 경우
   → 높은 신뢰도. 자동 연결.

3. scope_vault 매칭 (보조)
   → 변경 내용이 job의 scope_vault 문서와 동일한 vault 문서에 저장되는 경우
   → 낮은 신뢰도. 후보로만 제시.

4. scope 없는 job
   → 자동 매칭 제외. 수동 vault-job log 로만 기록 가능.
```

**복수 job 매칭 처리**:

하나의 변경 내용이 여러 job에 매칭될 수 있음.
예: "FSM 패턴은 보스 AI와 적 AI 모두에 적용" → boss-phase2, enemy-ai 양쪽 매칭.

이 경우 모두에 기록 후보로 제시하고 사용자가 승인/거부.

**매칭되는 job이 없는 내용**:

vault 저장 후보로만 처리. job 기록 없음.

### Step 3: wikilink 후보 계산

vault 저장 항목을 문서에 쓰기 전에, 저장할 내용과 **연관된 다른 vault 문서**를 탐색하여 wikilink 후보를 계산한다.
계산된 wikilink는 Step 4 승인 목록에 함께 표시한다.

**연관 문서 탐색 기준 (우선순위 순)**:

```
1. 저장 내용에 다른 vault 문서의 핵심 키워드가 포함된 경우
   예: "EventBus를 통해 페이즈 전환" → [[architecture/event-system]] 연결

2. 같은 폴더 내 다른 문서에서 동일 개념을 다루는 경우
   예: coding-style.md 저장 시 → scene-hierarchy.md, prefab-rules.md 후보 확인

3. active job의 scope_vault에 등록된 문서
   예: boss-phase2 job scope에 [[event-system]] 있으면 자동 포함
```

연관 문서가 없으면 `관련:` 섹션을 추가하지 않는다.

### Step 3.5: 모순 감지 (저장 직전 가벼운 합성)

저장 후보가 **기존 vault 문서의 결정/규칙과 충돌하는지** 가볍게 확인한다.
무거운 전체 분석이 아니라, 저장 대상과 **직접 관련된 문서만** 비교한다.
(누적된 모순의 일괄 정리는 vault-evolve가 담당. 여기선 즉시 충돌만 잡는다.)

**감지 대상**:

```
- 아키텍처 결정 (decisions/): 새 ADR이 기존 ADR의 결정을 뒤집는가?
  예: 기존 "EventBus 사용 결정" → 새 "Command 패턴으로 전환" → 직접 모순

- 코딩 컨벤션 (conventions/): 새 규칙이 기존 규칙과 어긋나는가?
  예: 기존 "_camelCase 사용" → 새 "m_ 접두사 사용" → 충돌
```

**감지 방법**:
- graph.json이 있으면 같은 카테고리 노드를 우선 비교
  (`graphify_query.py graphify-out/graph.json <저장키워드>`로 관련 문서 탐색)
- 없으면 같은 폴더 내 문서를 Grep으로 확인

모순이 감지되면 Step 4 승인 목록에 **별도 `⚠️ 모순` 항목**으로 포함시킨다.
모순이 없으면 이 단계를 조용히 통과한다. (무승인 자동처리 아님 — 반드시 Step 4 승인 거침)

### Step 4: 통합 승인 목록 제시

vault 저장 항목과 job별 갱신 항목을 **통합 목록**으로 출력.
항목이 하나도 없으면 "저장할 내용이 감지되지 않았습니다" 출력 후 종료.
단, 사전 조건 확인 4번에서 `DUE=true`였다면 종료 전에 "vault-evolve 추천" 블록은 반드시 출력한다
(이 확인은 이번 세션 저장 여부와 무관하게 항상 유효하다).

```
📋 vault-sync: 저장 후보 목록
────────────────────────────────────────
📚 vault 저장 항목

[1] 📐 conventions/coding-style.md 에 추가
    "MonoBehaviour Awake는 자기 초기화 전용"
    🔗 연결 예정: [[conventions/scene-hierarchy]] [[architecture/game-manager-pattern]]
    승인? (y/n/e)

[2] 🐛 debugging/performance-fixes.md 에 추가
    "2025-04-11: UI Canvas 분리 → 드로우콜 40% 감소"
    🔗 연결 예정: [[conventions/coding-style]]
    승인? (y/n/e)

────────────────────────────────────────
📋 job 갱신: boss-phase2  (매칭 근거: keywords=boss,FSM)

[3] history 엔트리 추가 → boss-phase2.history
    "### 2026-08-14 — BossController FSM 기본 구조 완성"
    승인? (y/n/e)

[4] 라이브 갱신 → boss-phase2 · ## 현재 상태 (교체)  라이브 212 → 209줄 · lint ERROR 0
    기존: "FSM 골격 설계 중"
    변경: "FSM 기본 구조 완성. 다음: 페이즈 전환 이벤트 연결"
    삭제 후보: 미해결 "🔴 FSM 상태 enum 미정" (이번 세션 해소)
    승인? (y/n/e)

[5] 완료 조건 체크
    ✅ "체력 50% 이하 시 페이즈 2 전환" → 완료 처리
    승인? (y/n/e)

[6] 라이브 갱신 → boss-phase2 · ## 미해결 · 블로커 (교체)
    추가: "🔴 EventBus.Publish() 연결 미완료"
    승인? (y/n/e)

────────────────────────────────────────
📋 job 갱신: login-ui-fix  (매칭 근거: keywords=UI,login)

[7] history 엔트리 추가 → login-ui-fix.history
    "### 2026-08-14 — 로그인 버튼 레이아웃 수정 완료"
    승인? (y/n/e)

────────────────────────────────────────
⚠️ 모순 감지 (Step 3.5)

[8] 새 결정이 기존 결정과 충돌
    새 결정:   "Command 패턴으로 전환"
    기존 결정: [[decisions/adr-003-eventbus]] "EventBus 사용" (2025-03-12)
    처리 선택:
      [s] 기존을 superseded 표시 + 새 결정 저장 (권장)
      [b] 둘 다 유지 (의도적 공존)
      [n] 저장 취소

────────────────────────────────────────
전체 승인: all  |  전체 거부: none  |  job만 승인: jobs
```

모순 항목은 일반 항목과 달리 `s`/`b`/`n`로 응답받는다:
- `s` → 기존 문서 frontmatter에 `status: superseded`, `superseded_by: [[새문서]]` 추가.
  새 문서에는 `supersedes: [[기존문서]]` 추가 (결정 이력 추적 가능).
- `b` → 양쪽 모두 유지. 둘 다 유효한 맥락이면 새 문서에 조건을 명시
  (예: "신규 코드는 Command, 레거시는 EventBus").
- `n` → 새 결정 저장 취소.

### Step 5: 승인 처리

- `y` → 해당 항목 저장
- `n` → 건너뜀
- `e` → 내용 수정 후 저장
- `all` → 전체 y
- `none` → 전체 n
- `jobs` → job 갱신 항목만 전체 y, vault 항목은 개별 판단

### Step 6: 문서 업데이트

**vault 저장 항목**:

wikilink가 있는 경우 저장할 내용 블록 하단에 `관련:` 섹션으로 추가:

```markdown
## Awake 초기화 규칙
MonoBehaviour Awake는 자기 초기화 전용으로 사용한다.
다른 오브젝트 참조는 Start에서 처리.

관련: [[conventions/scene-hierarchy]] [[architecture/game-manager-pattern]]
```

```powershell
# Obsidian CLI — PowerShell 도구로 호출, vault="vault" 명시
obsidian vault="vault" append file="coding-style" content="\n\n## Awake 초기화 규칙\n...\n\n관련: [[conventions/scene-hierarchy]]"
obsidian vault="vault" property:set name="updated" value="YYYY-MM-DD" file="coding-style"
```

직접 파일 수정 시:
- 적절한 섹션 하단에 추가
- frontmatter `updated` 갱신
- `confidence: low` → `medium` 상향

**job 에 매칭된 저장 건은 그 job 의 `scope_vault` 에 연결한다.**
Step 2 에서 scope_files · scope_keywords 로 매칭된 job 이 있고 이번에 vault 문서를 새로 만들었거나
기존 문서에 섹션을 추가했다면, 저장 직후 실행한다:

    python .claude/skills/vault-sync/scripts/scope_vault.py add "vault/jobs/<job>.md" "<folder>/<name>"

이미 있으면 무변경이다. 승인 목록의 해당 job 항목에 `scope_vault 추가: [[<folder>/<name>]]` 를 적어 사용자가 본다.
이 연결이 없으면 다음 resume 이 그 문서를 모른다 — scope_vault 는 job 에서 지식으로 가는 유일한 다리다.
출력에 `scope_vault 제거:` · `scope_vault 정규화:` 줄이 있으면 승인 목록의 같은 항목에 그대로 옮겨 적는다.

**job 갱신 항목** (job별로 처리)

job 문서는 **두 파일로 나뉘며 쓰기 방식이 서로 다르다.** 이걸 섞으면 라이브가 다시 비대해진다.

| 파일 | 성격 | 쓰기 방식 |
|------|------|-----------|
| `<job>.md` (라이브) | 지금의 상태 | **갱신(교체)** — 낡은 내용을 지우고 최신으로 덮어쓴다 |
| `<job>.history.md` | 시간순 로그 | **추가(append)** — 기존 방식 그대로, 지우지 않는다 |

**① history 에 이번 세션 엔트리 추가** (기존 진행 기록 작성 방식 그대로)

```powershell
obsidian vault="vault" append file="2026-07-03-wargame-remake.history" content="\n### YYYY-MM-DD — 한 줄 요약\n- 구체 내용"
```

history 파일이 없으면 먼저 만든다 (frontmatter `tags: [job-history]`, `job: <slug>`).

**② 라이브 문서의 유지 섹션을 갱신** — 아래 4개는 **누적이 아니라 교체**다.

| 섹션 | 갱신 규칙 |
|------|-----------|
| `## 현재 상태` | 지금 어디까지 왔고 다음이 무엇인지. 이전 내용을 **지우고** 다시 쓴다 |
| `## 최신 결정` | 확정된 결정만. 번복되면 옛 결정을 **교체**하고 근거를 한 줄로 남긴다 |
| `## 작업 플로우` | 현재 작업 방식·파이프라인·팀 규칙. 바뀐 부분만 교체 |
| `## 미해결 · 블로커` | 🔴 항목. **해소되면 줄을 삭제한다** (해소 경위는 history 몫) |

그 외 라이브 섹션(`작업 범위` `완료 조건` `관련 파일`)은 기존대로 처리 —
완료 조건은 체크박스 `- [ ]` → `- [x]`, frontmatter `updated` 날짜 갱신.

> **판정 기준**: "나중에 돌아봤을 때 필요한 것"이면 history, **"지금 작업하려면 필요한 것"이면 라이브**다.
> 경위·시도·실패 기록은 전부 history. 라이브에는 그 결과만 남는다.
> 라이브에 날짜 붙은 진행 문단을 추가하면 안 된다 — `### YYYY-MM-DD` 헤딩이든 `**▶ MM-DD (history (n))**` 굵은 문단이든 같다.

**교체의 구체 동작** — 「새 문단을 위에 얹기」는 교체가 아니다.

- `## 현재 상태` 의 `▶` 문단은 **문서 전체에 하나**다. 이번 세션 ▶ 를 쓰면 이전 ▶ 는 지운다.
  이전 ▶ 의 「다음」 중 아직 안 끝난 것만 새 「다음」 목록으로 옮긴다.
- `## 미해결` 에 ✅ · 🟢 · 「해소」를 표시해 남기지 않는다 — 해소되면 **줄째 삭제**한다.
- `## 최신 결정` 은 결과만 쓴다. 기각안 · 롤백 · 번복 경위는 history 에 쓴다.
- 이번 세션에서 사실이 바뀐 서술(스테이징 → 커밋, 파일 삭제 · 개명)은 **그 줄을 고친다**. 새 줄을 덧붙이지 않는다.
- 지우는 것이 불안하면 지우지 말고 **승인 목록에 「삭제 후보」로 올린다** — 판단은 사용자가 한다.
  남겨 두는 것은 안전한 선택이 아니다. 라이브가 불어 vault-load 가 문서를 통째로 못 읽게 된다.

**③ 라이브 검사 (필수)** — 라이브 편집안을 만든 뒤, Step 4 승인 목록을 내기 전에 실행한다.

```powershell
python .claude/skills/vault-sync/scripts/lint_job_live.py "vault/jobs/<job>.md"
```

- `ERROR` 가 있으면 편집안에 정리를 포함시킨다 — 지울 줄과 history 로 보낼 줄을 승인 항목으로 따로 올린다.
- `WARN`(줄 수 예산 · 결정 안의 경위 단어)은 승인 목록에 그대로 보여 주고, 정리할지 사용자에게 묻는다.
- 승인 목록의 라이브 항목에는 **줄 수 변화**(`라이브 337 → 341`)를 적는다. 늘기만 하면 교체가 안 되고 있다는 신호다.
- 검사는 Edit/Write 훅(`.claude/hooks/lint_job_live_hook.py`)으로도 돈다 — 세션 중 직접 편집도 같은 기준을 받는다.

**진행 기록 롤오버 (안전망 — 상시 실행 아님)**

위 ①②③을 지키면 라이브에는 날짜 엔트리가 쌓이지 않는다. 롤오버는 두 경우에만 쓴다.
롤오버는 `## 진행 기록` 섹션의 `### YYYY-MM-DD` 엔트리만 다룬다. 다른 섹션에 쌓인 것은 ③ 검사가 잡는다.

- **마이그레이션**: 기존 방식으로 누적된 job 문서를 신규 구조로 옮길 때 (job당 1회)
- **복구**: 실수로 라이브에 `### YYYY-MM-DD` 엔트리가 들어갔을 때

라이브 문서에 `## 진행 기록` 섹션이 남아 있으면 아직 마이그레이션 전이라는 신호다.
방치하면 vault-load 가 문서를 통째로 못 읽고 샘플링으로 떨어지는데, 엔트리 순서가 일정치 않아
최신 엔트리를 놓친다 (실측: `2026-07-03-wargame-remake.md` 1636줄 중 진행 기록 1355줄 = **83%**).

마이그레이션은 전량 이동이므로 `--budget 0 --pin-cap 0` 을 쓴다 —
미해결 항목은 history 로 보내되, 그 요지를 라이브 `## 미해결 · 블로커` 에 한 줄로 옮겨 적는다.

```powershell
# 1) 먼저 dry-run 으로 무엇이 이동하는지 확인
python .claude/skills/vault-sync/scripts/rollover_job_history.py "vault/jobs/<job>.md"

# 2) Step 4 승인 목록에 포함시켜 승인받은 뒤 적용 (--date 는 env 의 오늘 날짜)
python .claude/skills/vault-sync/scripts/rollover_job_history.py "vault/jobs/<job>.md" --apply --date YYYY-MM-DD
```

- **크기 기준**이다 (기본 예산 200줄). 개수·기간 기준은 엔트리 크기 편차
  (중앙값 30줄 / 최대 281줄)를 못 잡아 큰 엔트리 하나로 예산이 무너진다.
- **고정 엔트리**: 헤딩에 미해결 마커(`🔴` `미해결` `유실 확정` `보류` `TODO`)가 있으면
  오래돼도 라이브에 남긴다 — 미해결 이슈는 과거 기록이 아니라 현재 상태다.
  판정은 **헤딩만** 본다. 본문까지 보면 무의미해진다(실측: `🔴` 가 본문엔 29/37 엔트리,
  헤딩엔 1개 — 본문의 것은 인라인 강조 용도다).
- 고정분이 `--pin-cap`(기본 100줄)을 넘으면 오래된 고정분부터 해제하고 경고한다. 규칙 무력화 방지.
- 이동분은 `<job>.history.md` 로 가고, 라이브에 `[[<job>.history]]` 링크가 남는다.
  원본 순서를 재정렬하지 않는다 — 엔트리의 `(2)` `(3)` 같은 의도된 그룹이 깨진다.
- `--apply` 는 적용 전에 그 job 파일만 git 커밋한다 (`롤오버 전 스냅샷`). 줄 수 정산이 안 맞으면 중단한다.
  복구는 `git -C vault log -- jobs/<job>.md` 로 그 커밋을 찾아 되돌린다.

**승격 후보 카운트 (가벼운 누적 감지)**:

저장 시, 같은 주제가 **반복 누적되는지 카운트만** 한다. 실제 승격(규칙 생성)은 vault-evolve가 처리한다.

```
debugging/(또는 동일 카테고리)에 유사 증상/패턴이 누적되면:
→ 같은 폴더 + 유사 태그/키워드 매칭 횟수를 센다 (가벼운 판단, 무거운 합성 금지)
→ frontmatter promote_count 증가
→ promote_count가 임계치(기본 3) 이상이면 promote_candidate: true 플래그 추가
```

여기서는 카운트와 플래그만 남긴다. 규칙으로 일반화하는 합성은 하지 않는다.

**모든 저장 완료 후 vault 커밋 (PowerShell tool)**

    python .claude/skills/vault-sync/scripts/vault_git_sync.py --date <env 의 오늘 날짜> --mirror-memory "$env:USERPROFILE\.claude\projects\<project-slug>\memory" --quantize-attachments

memory 는 repo 밖이라 백업이 없었다. 미러가 vault 커밋에 실리면서 처음으로 복구 가능해진다.
TC 스크린샷은 저장 시점에 256색이 된다. 원본이 필요하면 캡처 도구 쪽에서 따로 보관한다.
변경이 없으면 아무것도 하지 않는다. push 실패는 경고일 뿐 sync 실패가 아니다 — 로컬 커밋이 남아 있다.
vault 의 복구 수단은 이 커밋이다. `.bak` 류 사본을 따로 만들지 않는다.

**coding-style.md 변경 시 CLAUDE.md 동기화**:

저장 항목 중 `conventions/coding-style.md`가 포함된 경우,
`CLAUDE.md`의 `## Coding Conventions` 섹션을 업데이트된 내용으로 교체한다.

```bash
# coding-style.md 내용을 CLAUDE.md Coding Conventions 섹션에 반영
# ## Coding Conventions 섹션 시작 ~ 다음 ## 섹션 직전까지 교체
```

### Step 7: 완료 출력

```
✅ vault-sync 완료

📚 vault 저장 (2건):
  📐 conventions/coding-style.md → Awake 초기화 규칙 추가
      🔗 [[conventions/scene-hierarchy]] [[architecture/game-manager-pattern]]
  🐛 debugging/performance-fixes.md → Canvas 분리 기록 추가
      🔗 [[conventions/coding-style]]

📋 job 갱신 (2개 job):
  boss-phase2:  history 엔트리 1건, 라이브 [현재 상태·최신 결정] 갱신, 완료 조건 1건 체크
  login-ui-fix: history 엔트리 1건 (라이브 변경 없음)

건너뜀 (1건):
  📋 decisions/adr-001 → 사용자 거부

🌱 성장 신호:
  ⚠️  모순 1건 해결: [[decisions/adr-003-eventbus]] → superseded 처리
  📈 승격 후보: debugging/ui-layout 패턴 3회 누적 → /vault-evolve 검토 권장

🗂 vault 커밋: <short-sha> · push 완료
다음 세션에서 /vault-job resume 실행 시 위 내용이 자동으로 복원됩니다.
```

`🌱 성장 신호` 섹션은 이번 sync에서 **모순을 해결했거나 승격 후보 임계치에 도달했을 때만** 표시한다.
둘 다 없으면 섹션 전체를 생략한다. (vault-evolve로의 인계 신호 역할)

완료 출력 직후 순서대로: ① 사전 조건 확인 4번에서 `DUE=true`였다면 "vault-evolve 추천" 블록, ② 이번 sync에서 저장된 파일 목록을 기준으로 graphify 갱신 필요 여부 안내. 두 블록은 독립적이라 하나만 뜰 수도, 둘 다 뜰 수도, 둘 다 생략될 수도 있다.

#### graphify 갱신 안내 기준

저장된 vault 파일들을 아래 기준으로 분류하여 출력한다.

**필수** — vault-load가 새 내용을 **찾지 못하는** 상황:
- `conventions/`, `architecture/`, `debugging/`, `decisions/`, `prd/` 에 **새 파일이 생성**됨
- 기존 파일에 **새 개념·패턴·시스템**이 추가됨 (섹션 신규 추가)

**제안** — vault-load가 찾을 수는 있으나 **연결 정확도가 떨어지는** 상황:
- 기존 파일에 **소규모 내용** 추가 (버그 해결 기록, 보완 설명)
- `debugging/` 파일에 새 이슈 기록 추가

**불필요** — 그래프 구조에 영향 없는 변경:
- `jobs/` 파일의 체크박스 변경·날짜 갱신·라이브 유지 섹션 갱신만 발생
- `<job>.history.md` 에만 엔트리 추가 (시간순 로그는 그래프 탐색 대상이 아니다)
- frontmatter(`updated`, `tags`)만 변경

출력 형식:

```
─────────────────────────────────────────
🔄 graphify 갱신 필요 여부
  [필수] conventions/coding-style.md — 새 개념 추가됨
         → /graphify vault --update 를 지금 실행하세요.
         (미실행 시 vault-load가 이 내용을 찾지 못합니다)

또는:
  [제안] debugging/performance-fixes.md — 기존 파일에 내용 추가
         → /graphify vault --update 를 실행하면 탐색 정확도가 높아집니다.
         (미실행 시에도 vault-load grep 폴백으로 파일은 찾을 수 있습니다)

또는:
  [불필요] jobs/ 파일만 갱신됨 — 그래프 구조에 영향 없음
```

저장된 vault 파일이 없는 경우(job 갱신만 있거나 전체 거부)에는 이 섹션을 출력하지 않는다.

## vault 저장 품질 기준

| 저장 O | 저장 X |
|--------|--------|
| "Awake는 자기 초기화만" (규칙) | "Awake에서 초기화했어요" (단순 사실) |
| "Canvas 분리로 드로우콜 40% 감소" (수치) | "Canvas 분리가 좋을 것 같아요" (의견) |
| "Addressables 도입 - 동적 로딩 필요" (근거) | "Addressables 써봤어요" (경험) |
| 재현 가능한 버그 해결법 | 일회성 이슈 |

## job 갱신 품질 기준

| 기록 O | 기록 X |
|--------|--------|
| "FSM 구조 완성, 트리거 구현" (완료 단위) | "코드 조금 수정함" (모호) |
| "EventBus 연결 미완료" (`미해결 · 블로커` 에 남김) | 완료 내용만 기록 |
| 완료 조건 체크박스 업데이트 | 완료했는데 체크 안 함 |
| 이전 ▶ 를 지우고 새 ▶ 하나 | ▶ 문단을 위에 하나 더 얹기 |
| 해소된 미해결 줄 삭제 | `✅ 해소(날짜)` 로 표시하고 남김 |

## 참고 파일

- `references/adr-numbering.md` → ADR 번호 부여 규칙
- `references/sync-examples.md` → 좋은/나쁜 저장 예시
