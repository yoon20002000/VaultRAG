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
│   ├── vault-load/     # 세션 시작 시 관련 문서 검색 → 컨텍스트 로드
│   ├── vault-sync/     # 세션 내용 자동 저장 (컨벤션, 버그 해결, 결정사항)
│   └── vault-job/      # 작업 단위 추적 (start / resume / done)
├── hooks/
│   ├── pre-compact.sh           # /compact 전 vault-sync 강제
│   └── session-start-compact.sh # compact 후 컨텍스트 자동 재주입
└── settings.json       # 훅 등록 설정

vault/                  # 사용자 로컬 (git 제외)
├── session-context.md  # 세션마다 주입할 고정 컨텍스트 (직접 작성)
├── conventions/        # 코딩 컨벤션, 네이밍 규칙
├── architecture/       # 아키텍처 결정 기록 (ADR)
├── debugging/          # 버그 해결 기록
├── decisions/          # 설계 결정 이유
├── jobs/               # 작업 추적 (active / done)
└── tech-debt/          # 기술 부채 목록
```

---

## 동작 흐름

```
세션 시작
  └─ /vault-load [키워드]
       ├─ session-context.md 항상 로드 (사용자 정의 고정 컨텍스트)
       └─ 키워드 기반 grep → 관련 문서 최대 4개 추가 로드

코드 설계 요청
  └─ vault/conventions/coding-style.md 자동 참조
       → 규칙 확인 후 코드 생성
       → 규칙 준수 여부 자가 검토

세션 종료
  └─ /vault-sync
       ├─ 컨벤션 결정 / 버그 해결 / 아키텍처 변경 자동 감지
       ├─ 품질 기준 통과한 항목만 저장 (단순 사실, 의견 제외)
       └─ vault/.sync-done 플래그 생성

/compact 입력
  └─ PreCompact 훅
       ├─ .sync-done 있음 → compact 허용
       └─ .sync-done 없음 → 차단 ("vault-sync 먼저 실행하세요")

compact 후 재시작
  └─ SessionStart 훅 (compact matcher)
       └─ session-context.md → Claude 컨텍스트 자동 주입
```

---

## 설치

### 요구사항

- Claude Code
- macOS / Linux (훅 스크립트 bash 기반)
- Obsidian (선택, CLI 없이도 동작)

### 1. 저장소 클론

```bash
git clone https://github.com/YOUR_USERNAME/vault-rag.git
cd vault-rag
```

### 2. 스킬 설치

```bash
# 전역 설치 (모든 프로젝트에서 사용)
cp -r .claude/skills/vault-* ~/.claude/skills/

# 또는 프로젝트별 설치
cp -r .claude/skills/vault-* /your-project/.claude/skills/
```

### 3. 훅 설치

```bash
# 프로젝트 루트에서
cp .claude/hooks/*.sh /your-project/.claude/hooks/
chmod +x /your-project/.claude/hooks/*.sh
```

### 4. settings.json 설정

프로젝트의 `.claude/settings.json`에 아래 `hooks` 블록을 추가합니다.  
이미 settings.json이 있다면 `hooks` 키만 병합하세요.

```json
{
  "hooks": {
    "PreCompact": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/pre-compact.sh",
            "timeout": 10
          }
        ]
      }
    ],
    "SessionStart": [
      {
        "matcher": "compact",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/session-start-compact.sh",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

### 5. vault 초기화

Unity 프로젝트 루트에서 Claude Code를 실행한 뒤:

```
/vault-init
```

Unity 프로젝트를 스캔해 `vault/` 폴더와 초기 문서들을 자동 생성합니다.

### 6. session-context.md 작성

```bash
# vault/session-context.md 를 직접 편집
```

이 파일은 매 세션 시작 시 Claude에 자동으로 주입됩니다.  
원하는 내용을 자유롭게 작성하세요. Claude가 이 파일을 수정하지 않습니다.

```markdown
# Session Context

## 작업 중인 프로젝트
마지막 날을 대비하는 우리의 자세 — 타워 디펜스 게임

## 현재 집중 영역
보스 페이즈 시스템 구현

## 주의사항 / 규칙
- MonoBehaviour Awake는 자기 초기화 전용
- 이벤트는 반드시 EventBus 통해서

## 참고 파일
- Assets/Scripts/Boss/BossController.cs
```

---

## 스킬 상세

### `/vault-load [키워드]`

세션 시작 시 관련 문서를 검색하여 컨텍스트 준비.

```
/vault-load               # session-context.md만 로드
/vault-load 보스 AI FSM   # 키워드 관련 문서 추가 로드
```

**검색 우선순위**: obsidian-cli → grep → 폴더 구조 추론  
**항상 로드**: `session-context.md`  
**추가 로드**: 키워드 매칭 문서 최대 4개

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
/vault-job done      # 완료 (vault-sync 자동 호출)
```

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
```

`claude.ai → Customize → Skills → + → Upload a skill`

> ⚠️ Claude 앱은 훅 시스템을 지원하지 않아 PreCompact 자동 차단 기능은 동작하지 않습니다.

---

## 훅 동작 확인

```bash
# Claude Code 실행 후
/hooks

# 수동 테스트
bash .claude/hooks/pre-compact.sh
echo $?  # vault 없으면 0, sync-done 없으면 2
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
