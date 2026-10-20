# vault-rag — Obsidian-based Lightweight RAG for Claude Code

> **No vector DB. No embeddings. Just markdown files.**  
> Claude Code 세션 간 컨텍스트를 유지하는 경량 RAG 시스템 — Unity 솔로 개발자를 위한 지식 베이스.

---

## 왜 만들었나

Claude Code는 세션을 시작할 때마다 기억이 초기화됩니다. 매번 코딩 컨벤션, 아키텍처 결정, 버그 해결 기록을 다시 설명해야 하는 문제를 해결하기 위해 만들었습니다.

전통적인 RAG는 벡터 DB, 임베딩 모델, 청킹 파이프라인이 필요합니다. 이 시스템은 그런 인프라 없이 **Obsidian vault의 마크다운 파일 + Claude Code 스킬 + 훅**만으로 동일한 효과를 냅니다.

> "LLMs with large context windows don't need vector retrieval for small-medium knowledge bases.  
> Structured markdown files work better — no chunking failures, full provenance, human-readable."  
> — Andrej Karpathy의 LLM Wiki 패턴에서 영감

---

## 전통적 RAG vs 이 시스템

| | 전통적 RAG | vault-rag |
|---|---|---|
| 저장소 | Vector DB (Pinecone, Chroma 등) | Obsidian 마크다운 파일 |
| 검색 방식 | 임베딩 유사도 검색 | `grep` + 폴더 구조 추론 |
| 청킹 | 필요 (청크 손실 위험) | 불필요 (파일 단위) |
| 인프라 | 서버/API 필요 | 로컬 파일만 |
| 업데이트 | 재임베딩 필요 | 마크다운 편집으로 즉시 반영 |
| 비용 | 임베딩 API 비용 발생 | 없음 |
| 사람이 읽을 수 있나 | ❌ | ✅ Obsidian에서 바로 열람 |

---

## 시스템 구조

```
.claude/
├── skills/
│   ├── vault-init/     # vault 초기화 (프로젝트 스캔 → 문서 자동 생성)
│   ├── vault-load/     # 인덱스 우선 검색 → 컨텍스트 로드 (+ graphify 그래프 질의, 선택)
│   ├── vault-sync/     # 세션 내용 저장 + 린트 · job 이력 롤오버 · vault git 동기화
│   ├── vault-job/      # 작업 단위 추적 (start / resume / log / scope / done / list)
│   └── vault-evolve/   # 누적 지식 합성 (패턴 승격 · 정제 · 모순 정리)
├── hooks/
│   └── lint_job_live_hook.py    # PostToolUse(Edit|Write): 라이브 job 문서 규칙 위반 시 차단
└── settings.json       # 훅 등록 설정

vault/                  # 사용자 로컬 (프로젝트 repo 에서 제외, 자체 repo 로 관리 가능)
├── conventions/        # 코딩 컨벤션, 네이밍 규칙
├── architecture/       # 아키텍처 결정 기록 (ADR)
├── debugging/          # 버그 해결 기록
├── decisions/          # 설계 결정 이유
├── handoff/            # 다른 에이전트·세션 인계 문서
├── jobs/               # 작업 추적 (한 폴더, frontmatter status 로 완료 표시)
├── tech-debt/          # 기술 부채 목록
└── ...                 # prd, ui-specs, daily, weekly, archive 등 (vault-init 이 생성)
```

루트의 `*.skill` 파일은 같은 스킬을 claude.ai 업로드용으로 압축한 것이며, `.claude/skills/` 에서 재생성합니다.

---

## 동작 흐름

```
세션 시작
  └─ /vault-load [키워드]
       ├─ 인덱스(제목·태그·섹션 목차) 먼저 검색 → 필요한 문서만 로드
       ├─ job 문서는 통째로, 300줄 이상 문서는 섹션 인덱스로 부분 로드
       └─ graphify 그래프가 있으면 이웃 노드까지 확장 (선택)

작업 단위 추적
  └─ /vault-job start | resume | log | scope | done
       └─ 라이브 job 문서는 「교체」 방식 (▶ 하나, 미해결 ✅ 금지)
            → PostToolUse 훅이 lint_job_live 로 즉시 검증

세션 종료
  └─ /vault-sync
       ├─ 컨벤션 결정 / 버그 해결 / 아키텍처 변경 자동 감지
       ├─ 품질 기준 통과한 항목만 저장 (단순 사실, 의견 제외)
       ├─ handoff · job 린트, job 이력 롤오버
       └─ vault 자체 git repo 로 동기화

주기적
  └─ /vault-evolve
       └─ 패턴 승격 · 지식 정제 · 모순 정리 (due 여부는 check_evolve_due 로 판단)
```

---

## 설치

### 요구사항

- Claude Code
- Python 3 (스킬 스크립트·훅)
- Windows + PowerShell 기준으로 작성됨 (스킬의 CLI 호출 예시가 PowerShell 도구 전제)
- Obsidian + Obsidian CLI (선택, 없으면 grep 으로 대체)
- graphify (선택, vault-load 그래프 질의 · `/vault-graph-update`)

### 1. 저장소 클론

```bash
git clone https://github.com/yoon20002000/VaultRAG.git
cd VaultRAG
```

### 2. 스킬 설치

훅이 `.claude/skills/vault-sync/scripts/lint_job_live.py` 를 상대 경로로 찾으므로 **스킬은 프로젝트 `.claude/` 에 설치**하는 것을 권장합니다.

```powershell
# 프로젝트별 설치 (권장)
Copy-Item -Recurse .claude\skills\vault-* C:\your-project\.claude\skills\

# 또는 전역 설치 (훅을 쓰지 않을 때)
Copy-Item -Recurse .claude\skills\vault-* $HOME\.claude\skills\
```

### 3. 훅 설치

```powershell
Copy-Item .claude\hooks\lint_job_live_hook.py C:\your-project\.claude\hooks\
```

### 4. settings.json 설정

프로젝트의 `.claude/settings.json`에 아래 `hooks` 블록을 추가합니다.  
이미 settings.json이 있다면 `hooks` 키만 병합하세요.

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "python -I \"C:/your-project/.claude/hooks/lint_job_live_hook.py\"",
            "timeout": 15
          }
        ]
      }
    ]
  }
}
```

> 이전 버전의 `PreCompact`(`.sync-done` 차단) · `SessionStart`(compact) 훅은 폐지되었습니다. 기존 settings.json 에 남아 있다면 제거하세요.

### 5. vault 초기화

Unity 프로젝트 루트에서 Claude Code를 실행한 뒤:

```
/vault-init
```

Unity 프로젝트를 스캔해 `vault/` 폴더와 초기 문서들을 자동 생성합니다.

---

## 스킬 상세

### `/vault-load [키워드]`

세션 시작 시 관련 문서를 검색하여 컨텍스트 준비.

```
/vault-load 보스 AI FSM   # 키워드 관련 문서 로드
```

**검색**: 인덱스 우선 (`vault_search.py`, `build_section_index.py`) → graphify 이웃 확장(선택)  
**로드 단위**: job 문서는 통째, 300줄 이상 문서는 섹션 단위

### `/vault-sync`

세션에서 발생한 의미 있는 내용을 vault에 자동 저장.

저장 대상:
- 새로 합의된 코딩 컨벤션
- 해결된 버그 (원인 + 해결법)
- 아키텍처 결정 (근거 포함)
- 기술 부채 발견

저장 제외 (자동 필터):
- 단순 사실 서술 ("Awake에서 초기화했어요")
- 의견 ("이게 좋을 것 같아요")
- 일회성 이슈

### `/vault-job start "작업명"`

작업 단위 추적 시작. vault-load/sync와 연동되어 작업별 진행 기록을 관리합니다.

```
/vault-job start "BossController FSM 구현"
/vault-job resume    # 이어서 작업
/vault-job log       # 진행 기록
/vault-job scope     # 작업 범위 관련 문서 정리
/vault-job done      # 완료 (vault-sync 자동 호출)
/vault-job list
```

job 문서는 이동하지 않고 frontmatter `status` 로 완료를 표시합니다.

### `/vault-evolve`

vault 에 쌓인 지식을 합성합니다. 반복된 패턴을 컨벤션으로 승격하고, 중복·낡은 서술을 정제하고, 서로 모순되는 문서를 정리합니다. 주 1회 또는 문서가 일정 수 누적됐을 때 실행하세요.

---

## vault 저장 구조 예시

```markdown
<!-- vault/conventions/coding-style.md -->
---
tags: [convention, unity, naming]
updated: 2026-04-14
confidence: high
---

## MonoBehaviour 초기화 규칙
- Awake: 자기 자신의 컴포넌트 초기화만
- Start: 다른 오브젝트 참조 초기화
```

```markdown
<!-- vault/debugging/performance-fixes.md -->
## 2026-04-14: UI Canvas 분리
- 문제: 전체 UI가 매 프레임 리빌드
- 원인: 동적 UI와 정적 UI가 같은 Canvas
- 해결: Canvas 분리 → 드로우콜 40% 감소
```

---

## Claude 앱에서도 사용하기

각 스킬을 ZIP으로 패키징하면 claude.ai에서도 업로드해 사용할 수 있습니다.

```bash
cd .claude/skills
zip -r vault-load.zip vault-load/
zip -r vault-sync.zip vault-sync/
zip -r vault-init.zip vault-init/
zip -r vault-job.zip vault-job/
zip -r vault-evolve.zip vault-evolve/
```

`claude.ai → Customize → Skills → + → Upload a skill`

> ⚠️ Claude 앱은 훅 시스템을 지원하지 않아 PreCompact 자동 차단 기능은 동작하지 않습니다.

---

## 훅 동작 확인

```powershell
# Claude Code 실행 후
/hooks

# 수동 테스트 — 라이브 job 문서 린트 (규칙 위반 시 exit 2)
python .claude\skills\vault-sync\scripts\lint_job_live.py vault\jobs\<job>.md
```

---

## Unity 특화 기능

현재 vault-init은 Unity 프로젝트에 최적화되어 있습니다.

- `Assets/Scripts/` 스캔 → 네이밍 패턴 자동 추출
- `Packages/manifest.json` 읽기 → 패키지 목록 기록
- `ProjectSettings/` 분석 → 플랫폼/렌더 파이프라인 감지
- Unity 특화 폴더 구조: MonoBehaviour 패턴, ScriptableObject 규칙 등

Unity 외 프로젝트에서도 vault-load / vault-sync / vault-job은 범용적으로 사용 가능합니다.

---

## 라이선스

MIT License

---

## 참고 / 영감

- [Andrej Karpathy — LLM Knowledge Base (LLM Wiki pattern)](https://x.com/karpathy)
- [Claude Code Agent Skills 공식 문서](https://code.claude.com/docs/en/skills)
- [agentskills.io open standard](https://agentskills.io)
