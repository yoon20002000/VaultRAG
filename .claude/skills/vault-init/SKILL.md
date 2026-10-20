---
name: vault-init
description: >
  Unity 프로젝트에 Obsidian 기반 knowledge vault를 초기화하는 스킬.
  프로젝트 최초 시작 시 또는 기존 프로젝트에 vault를 처음 도입할 때 사용.
  "vault 만들어줘", "vault 초기화", "vault-init", "knowledge base 세팅",
  "옵시디언 vault 생성", "프로젝트 컨벤션 저장소 만들어줘" 등의 요청 시 반드시 이 스킬을 사용.
  obsidian-cli, obsidian-markdown 스킬과 함께 사용하면 더 좋은 결과를 얻을 수 있음.
---

# vault-init

Unity 프로젝트의 지식을 Obsidian vault에 구조화하여 저장하는 초기화 스킬.
클로드 코드 세션 간 컨텍스트를 유지하고 팀/개인 knowledge base를 구축하는 것이 목적.

## 사전 조건 확인

실행 전 반드시 확인:
1. 현재 디렉토리가 Unity 프로젝트 루트인지 확인 (`Assets/`, `ProjectSettings/` 존재 여부)
2. `vault/` 폴더가 이미 존재하는지 확인 → 존재하면 중단하고 사용자에게 알림
3. Obsidian CLI 사용 가능 여부 판정 → 아래 "Obsidian CLI 호출 규칙" 참조. 사용 가능하면 CLI 방식, 불가하면 Read/Write 도구로 직접 파일 생성 방식 폴백

## Obsidian CLI 호출 규칙 (공통 — 모든 vault 스킬 동일)

Obsidian CLI 명령은 `obsidian`이지만, Windows에는 GUI 앱(`Obsidian.exe`)과 CLI 런처(`Obsidian.com`)가 같은 폴더에 공존한다. 어느 셸로 호출하느냐에 따라 갈린다:

- ✅ **PowerShell 도구로 호출한다** → `PATHEXT`가 `.COM`을 우선하므로 `obsidian`이 `Obsidian.com`(CLI)으로 resolve된다.
- ❌ **Bash 도구(git-bash)로 `obsidian`을 호출하지 않는다** → `.exe`(GUI)로 새어 명령이 무시되고 앱만 뜬다. 불가피하면 `"C:\Users\<user>\AppData\Local\Programs\Obsidian\Obsidian.com"` 절대경로를 명시한다.
- vault는 등록된 **폴더 basename**으로 지정한다. 기본값은 `vault="vault"` (프로젝트 루트의 `vault/` 폴더).

**사용 가능 판정** (PowerShell 도구):
```powershell
$cli = Get-Command obsidian -ErrorAction SilentlyContinue
# $cli.Source 가 ...\Obsidian.com 이고, Obsidian 앱이 실행 중이면 CLI 사용 가능
$running = [bool](Get-Process Obsidian -ErrorAction SilentlyContinue)
```
- `obsidian` 미발견 / `.com` 아님 / Obsidian 미실행 → **CLI 사용 불가** → Read/Write 도구로 `vault/` 파일을 직접 편집하는 폴백으로 전환한다.

## 실행 단계

### Step 1: 프로젝트 스캔

아래 항목을 분석하여 초기 문서 내용을 추출:

```
분석 대상:
- Assets/Scripts/ 하위 C# 파일들 → 네이밍 패턴, 네임스페이스 구조
- Packages/manifest.json → 사용 중인 패키지 목록
- ProjectSettings/ProjectSettings.asset → 플랫폼, 회사명, 프로젝트명
- .cs 파일에서 추출: 클래스 상속 패턴, 인터페이스 사용, 주석 스타일
```

스캔 결과를 내부적으로 메모:
- 감지된 패턴 → 해당 문서에 실제 내용으로 작성
- 감지 실패 항목 → 빈 템플릿으로 생성

### Step 2: vault 폴더 구조 생성

```
vault/
├── .obsidian/                    ← Obsidian 설정 (git 포함)
│   └── app.json
├── _templates/                   ← 문서 작성 템플릿
│   ├── job.md                    ← job 라이브 (지금의 상태, 갱신형)
│   ├── job-history.md            ← job 히스토리 (시간순, 추가형)
│   ├── convention-template.md
│   ├── decision-template.md
│   └── debugging-template.md
├── _index.base                   ← 자동 인덱싱 (obsidian-bases)
├── session-context.md            ← 세션 시작 시 주입할 고정 컨텍스트 (사용자 직접 관리)
├── conventions/                  ← 코딩 컨벤션
│   ├── coding-style.md
│   ├── scene-hierarchy.md
│   ├── prefab-rules.md
│   └── asset-management.md
├── architecture/                 ← 아키텍처 결정
│   ├── event-system.md
│   ├── save-system.md
│   └── game-manager-pattern.md
├── debugging/                    ← 버그 해결 기록
│   ├── performance-fixes.md
│   ├── physics-issues.md
│   └── mobile-specific.md
├── decisions/                    ← ADR (Architecture Decision Records)
│   └── adr-template.md
├── jobs/                         ← 작업 단위 추적 (vault-job 스킬)
│                                   job 1개 = 파일 2개 (<slug>.md + <slug>.history.md)
│   ├── active/                   ← 현재 진행중인 job 문서
│   └── done/                     ← 완료된 job 히스토리
├── archive/                      ← vault-evolve가 미사용 문서를 이동 (삭제 아님, 복구 가능)
└── tech-debt/
    └── refactor-list.md
```

`archive/`는 vault-init 시 빈 폴더로 생성한다(`.gitkeep` 또는 README 1줄). vault-evolve의 정제 작업이 오래되고 고립된 문서를 이곳으로 이동시키며, 원본은 삭제하지 않으므로 언제든 복구 가능하다.

### Step 3: 각 문서 작성 규칙

모든 문서는 Obsidian frontmatter를 포함해야 함:

```markdown
---
tags: [convention, unity, <세부카테고리>]
created: <오늘날짜 YYYY-MM-DD>
updated: <오늘날짜 YYYY-MM-DD>
confidence: low | medium | high
---
```

**생애주기(lifecycle) 필드 — 선택**: 아래 필드는 초기 생성 시 넣지 않으며,
vault-sync(축적)와 vault-evolve(합성)가 문서를 진화시킬 때 추가하는 공통 스키마다.
모든 vault 스킬이 동일하게 해석하므로 여기서 한 번만 정의한다.

| 필드 | 의미 | 기록 주체 |
|------|------|-----------|
| `promote_candidate: true` | 유사 패턴이 반복 누적되어 규칙 승격 후보임 | vault-sync |
| `promote_count: N` | 누적 반복 횟수 (승격 임계치 판단용) | vault-sync |
| `status: superseded` | 더 이상 유효하지 않은(대체된) 결정 | vault-sync / vault-evolve |
| `superseded_by: [[새문서]]` | 이 문서를 대체한 문서 | vault-sync / vault-evolve |
| `supersedes: [[기존문서]]` | 이 문서가 대체한 기존 문서 | vault-sync / vault-evolve |
| `promoted_to: [[규칙문서]]` | 이 사례가 승격되어 일반화된 규칙 문서 | vault-evolve |
| `archived: YYYY-MM-DD` | 아카이브 이동 날짜 | vault-evolve |
| `archive_reason: <사유>` | 아카이브 사유 (예: "7개월 미사용, 고립 노드") | vault-evolve |

이 필드들은 **결정의 이력을 잃지 않기 위한** 장치다. 문서를 삭제하거나 덮어쓰지 않고,
대체·승격·아카이브 관계를 frontmatter로 추적해 언제든 "왜 그렇게 됐는지"를 역추적할 수 있게 한다.

**스캔에서 패턴이 감지된 경우**: 실제 코드 예시와 함께 내용 작성
**감지되지 않은 경우**: 아래 형식으로 빈 템플릿 작성

```markdown
> [!todo] 작성 필요
> 이 문서는 아직 작성되지 않았습니다. vault-sync 실행 시 내용이 추가됩니다.
```

**session-context.md 초기 파일**: vault/ 루트에 아래 형식으로 생성

```markdown
---
tags: [session-context]
updated: <오늘날짜 YYYY-MM-DD>
---

# Session Context

> 이 파일은 매 세션 시작 시 자동으로 로드됩니다.
> 원하는 내용을 자유롭게 작성하세요. Claude가 이 파일을 수정하지 않습니다.

## 작업 중인 프로젝트
(작성 예시: 마지막 날을 대비하는 우리의 자세 - 타워 디펜스 게임)

## 현재 집중 영역
(작성 예시: 보스 페이즈 시스템 구현)

## 주의사항 / 규칙
(작성 예시: MonoBehaviour Awake는 자기 초기화 전용)

## 참고 링크 / 파일
(작성 예시: Assets/Scripts/Boss/BossController.cs)
```

이 파일은 사용자가 직접 편집하며, Claude는 절대 수정하지 않는다.

### Step 4: _index.base 생성

obsidian-bases 형식으로 자동 인덱싱 파일 생성.
참고: `references/index-base-template.md`

### Step 5: .obsidian/app.json 생성

Obsidian이 vault를 올바르게 인식하도록 최소 설정 작성.
참고: `references/obsidian-config.md`

### Step 6: CLAUDE.md 업데이트

프로젝트 루트의 `CLAUDE.md`에 vault 참조 추가:

```markdown
## Knowledge Vault
이 프로젝트는 Obsidian 기반 knowledge vault를 사용합니다.
- vault 위치: `./vault/`
- 세션 시작 시 `/vault-load`를 실행해 관련 컨텍스트를 로드하세요.
- 세션 종료 시 `/vault-sync`를 실행해 새 내용을 저장하세요.
- 주기적으로(주 1회 권장 또는 승격 후보 누적 시) `/vault-evolve`를 실행해 vault를 정제·성장시키세요.
  vault-sync가 저장(축적)을, vault-evolve가 합성(패턴 승격·정제·모순 정리)을 담당합니다.
- `graphify-out/graph.json`이 있으면 vault-load와 vault-evolve가 자동으로 Graphify 탐색을 사용합니다.
  없으면 grep 폴백으로 동작합니다. `/graphify .` 실행으로 graph를 생성하세요.

## Coding Conventions
코딩 컨벤션은 항상 아래 파일을 참조합니다.
코드 작성 또는 설계 요청 시 반드시 이 파일의 규칙을 확인하고 준수하세요.

{vault/conventions/coding-style.md 내용을 여기에 인라인으로 삽입}
```

**coding-style.md 인라인 삽입 방법**:
vault-init 실행 시 `vault/conventions/coding-style.md` 내용을 읽어
`CLAUDE.md`의 `Coding Conventions` 섹션에 직접 삽입한다.
파일이 비어있는 경우(todo 상태) 섹션만 생성하고 내용은 생략.

이후 vault-sync가 `coding-style.md`를 업데이트할 때마다
`CLAUDE.md`의 해당 섹션도 함께 동기화한다.

### Step 7: 상태 점검 (스모크 테스트)

vault 생성 후 **CLI 연동이 실제로 동작하는지 검증**한다. "사전 조건"의 판정 결과에 따라 분기:

**CASE A — CLI 사용 가능**: PowerShell 도구로 vault 등록 상태와 검색을 실제 실행한다.
```powershell
# 1) 이 프로젝트 vault가 Obsidian에 등록되어 있는지 (obsidian.json)
$cfg = Get-Content "$env:APPDATA\obsidian\obsidian.json" -Raw | ConvertFrom-Json
$here = (Resolve-Path "./vault").Path
$match = $cfg.vaults.PSObject.Properties | Where-Object { $_.Value.path -eq $here }
# $match 없으면 → 미등록: 사용자에게 "Obsidian에서 vault/ 폴더를 열어 등록해달라" 안내 후 재확인

# 2) 등록명(폴더 basename)으로 실제 검색 — 결과가 나오면 CLI 정상
obsidian vault="vault" search query="convention" limit=1
```
- 검색 결과 출력 → ✅ CLI 정상. 출력의 vault 이름을 결과 리포트에 기록.
- "Vault not found" → vault 이름 오인. `obsidian.json`에서 실제 basename을 다시 확인해 사용.
- 명령이 GUI만 띄우고 응답 없음 → **git-bash로 호출한 것**. PowerShell 도구로 재시도.

**CASE B — CLI 사용 불가**: 폴백을 안내한다. "Obsidian 미실행 또는 CLI 미설치 → 모든 vault 작업은 Read/Write 도구로 `vault/` 파일을 직접 편집합니다." (정상 동작이며 에러 아님)

## 완료 후 출력 형식

```
✅ vault-init 완료

생성된 구조:
  vault/
  ├── session-context.md (세션 고정 컨텍스트 - 직접 편집하세요)
  ├── conventions/ (4개 문서)
  ├── architecture/ (3개 문서)  
  ├── debugging/ (3개 문서)
  ├── decisions/ (1개 템플릿)
  ├── jobs/ (active/ done/)
  ├── archive/ (vault-evolve가 미사용 문서를 이동)
  └── tech-debt/ (1개 문서)

스캔 결과:
  ✅ 감지됨: [감지된 패턴 목록]
  ⚠️  미감지: [템플릿으로 생성된 항목 목록]

CLI 상태 점검 (Step 7):
  [✅ CLI 정상 | ⚠️ 폴백(직접 편집) 모드]
  vault 등록명: "[basename]"   호출: PowerShell 도구 (.com)
  스모크 테스트: [검색 결과 N건 | 미실행(폴백)]

다음 단계:
  1. (미등록 시에만) Obsidian에서 vault/ 폴더를 열어 등록
  2. 작업 시작 시: /vault-job start "작업명" 실행
  3. 작업 재개 시: /vault-job resume 실행
  4. 작업 종료 후: /vault-job done 실행 (vault-sync 자동 호출)
  5. 주기적으로: /vault-evolve 실행 (vault 정제·성장)
```

## 참고 파일

- `references/index-base-template.md` → _index.base 작성법
- `references/obsidian-config.md` → .obsidian 설정 상세
- `references/document-templates.md` → 각 카테고리별 템플릿 상세
