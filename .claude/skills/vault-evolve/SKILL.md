---
name: vault-evolve
description: >
  vault에 누적된 지식을 합성하고 진화시키는 스킬. 단순 저장을 넘어 패턴 승격,
  지식 정제, 모순 정리를 수행하여 vault가 시간이 지날수록 더 정확하고 압축된
  지식 베이스로 성장하게 만든다. 주기적으로 실행 (주 1회 또는 vault 문서 일정 수 누적 시).
  "vault 정리해줘", "vault-evolve", "지식 합성", "패턴 승격", "vault 리뷰",
  "오래된 문서 정리", "vault 성장시켜줘", "중복 정리", "모순 정리해줘" 등의 요청 시
  반드시 이 스킬을 사용. vault-sync, vault-load, obsidian-cli 스킬과 함께 사용.
---

# vault-evolve

vault를 정적인 아카이브에서 **성장하는 지식 베이스**로 만드는 스킬.
vault-sync가 저장(축적)을 담당한다면, vault-evolve는 합성(synthesis)을 담당한다.

compounding 개념 — cross-reference, 모순 감지, 패턴 합성 — 을 주기적 배치 작업으로 구현한다.

무거운 분석을 수행하므로 매 세션이 아니라 주기적으로 실행한다 (주 1회 권장,
또는 vault-sync가 승격 후보를 일정 수 이상 플래그했을 때).

## Obsidian CLI 호출 규칙 (공통 — 모든 vault 스킬 동일)

- ✅ Obsidian CLI는 **PowerShell 도구로** `obsidian ...` 호출 (`PATHEXT` `.COM` 우선 → `Obsidian.com` CLI로 resolve)
- ❌ Bash 도구(git-bash)로 `obsidian` 호출 금지 → GUI(`Obsidian.exe`)로 새어 명령 무시됨
- vault는 폴더 basename으로 지정: 기본값은 `vault="vault"` (프로젝트 루트의 `vault/` 폴더)
- CLI 미설치/Obsidian 미실행 시 → Read/Write/Grep 도구로 `vault/` 파일 직접 편집 (폴백, 정상)
- 상세 판정 절차: `vault-init/SKILL.md`의 "Obsidian CLI 호출 규칙" 섹션 참조

## 사전 조건 확인

1. `vault/` 폴더 존재 확인 → 없으면 `/vault-init` 먼저 실행 안내 후 종료
2. `graphify-out/graph.json` 존재 확인 (Read 도구로 첫 줄 `limit=1`)
   → 있으면 그래프 기반 분석, 없으면 폴더/Grep 기반 폴백
3. `vault/.evolve-log` 마지막 실행 기록 확인 → 증분 분석 범위 결정 (없으면 전체)

## 실행 모드

세 가지 합성 작업을 순차 실행한다. 특정 작업만 실행하려면 인자로 지정.

```
/vault-evolve            → 세 작업 모두
/vault-evolve promote    → 패턴 승격만
/vault-evolve refine     → 지식 정제만
/vault-evolve resolve    → 모순 정리만
```

---

## 작업 1: 패턴 승격 (Promotion)

반복적으로 나타나는 개별 기록을 **일반 규칙으로 승격**한다.

### 감지

```
1. promote_candidate: true 플래그가 있는 문서 수집 (vault-sync가 표시)
   → frontmatter promote_count로 누적 횟수 확인
2. 추가로 debugging/ 내 유사 증상 그룹핑:
   - 같은 태그 + 유사 키워드 (예: "Canvas", "드로우콜", "리빌드")
   - 임계치(기본 3회) 이상 반복된 패턴 식별
```

승격 임계치·카테고리별 기준은 `references/promotion-rules.md` 참조.

### 승격 처리

유사 사례가 임계치 이상이면, 개별 기록들을 종합해 규칙을 생성한다.
합성 전/후 구체 예시는 `references/evolve-examples.md` 참조.

승격 시:
- `conventions/`(또는 적절한 카테고리)에 규칙 생성 또는 기존 규칙에 통합
- 원본 문서들 frontmatter에 `promoted_to: [[conventions/규칙문서]]` 표시
- **원본은 삭제하지 않음** (사례 근거로 보존, wikilink로 연결)
- 새 규칙 `confidence: medium` (사례 3건 기반), 출처 사례를 본문에 wikilink로 명시

### 승격 전 사용자 확인 (승인 게이트)

규칙 생성은 영향이 크므로 승격안을 제시하고 승인받는다. 자동 진행하지 않는다.

```
📈 패턴 승격 제안
────────────────────────────────────────
debugging/ 에 Canvas 성능 패턴 3건 누적 감지

승격안: conventions/ui-canvas-rules.md 생성
  "자주 갱신되는 UI와 정적 UI는 Canvas를 분리한다"
  근거 3건: [[2025-03-01-canvas]] [[2025-04-11-canvas]] [[2025-05-20-canvas]]

[1] 승격 진행  [2] 수정 후 승격  [3] 건너뛰기
────────────────────────────────────────
```

---

## 작업 2: 지식 정제 (Refinement)

자주 쓰이는 지식은 다듬고, 안 쓰이는 지식은 정리한다.

### God nodes 리뷰

graph.json 유무와 관계없이 `python .claude/skills/vault-evolve/scripts/inbound_links.py --top 5` 로 상위 문서를 뽑는다. graph.json 이 있으면 참고로만 본다.

```powershell
python .claude/skills/vault-evolve/scripts/inbound_links.py --top 5
```

> 출력에 `jobs/` 문서가 포함되면 정제 대상에서 제외한다 (작업 추적용 임시 문서).
> 정제 대상은 `conventions/` `architecture/` `debugging/` `decisions/` 의 핵심 문서다.

각 핵심 문서에 대해:
- 내용이 최신인가? (`updated` 날짜가 오래됐으면 검토 플래그)
- 중복 서술이 있는가? → 압축
- `confidence`가 사례 수/참조 수에 비해 낮은가? → 상향 검토
- 끊긴 wikilink가 있는가? → 복구

God nodes는 vault-load가 가장 많이 로드하는 문서이므로, 여기를 정제하면 로드 효율이 직접 개선된다.

**정제(압축/링크 복구/confidence 상향)는 영향이 작아 승인 없이 자동 처리 가능.**
단, 핵심 규칙의 의미가 바뀌는 수정은 승인을 받는다.

### 미사용 문서 아카이브

```
판단 기준 (모두 충족 시 아카이브 후보):
- `updated` 가 90일 이상 경과
- `inbound_links.py --zero` 에 나옴 (다른 지식 문서가 한 번도 가리키지 않음)
- `confidence: low`
- active job 의 scope_vault 에 없음 (vault/jobs/ 라이브 문서 전수 grep)
```

이전 기준(6개월 · 그래프 고립 노드)은 vault 나이와 같아 한 번도 걸리지 않았다 (.evolve-log 전 실행 archive=0).

```
처리:
→ vault/archive/ 로 이동 (삭제 아님)
→ frontmatter에 archived: YYYY-MM-DD, archive_reason 기록
→ 복구 가능하게 유지
```

아카이브는 이동이므로 자동 처리 가능하나, 일괄 이동 목록을 출력해 사용자가 확인할 수 있게 한다.

### 정제 결과 출력

```
🧹 지식 정제 결과
────────────────────────────────────────
God nodes 리뷰 (상위 5개):
  ✏️  architecture/event-system.md → 중복 서술 2곳 압축
  ✏️  conventions/coding-style.md → confidence medium→high (참조 12회)
  🔗 architecture/save-system.md → 끊긴 wikilink 1개 복구

아카이브 (2건):
  📦 debugging/2024-11-temp-fix.md → 7개월 미사용, 고립 노드
  📦 decisions/adr-001-draft.md → superseded, 참조 0
────────────────────────────────────────
```

---

## 작업 3: 모순 정리 (Resolution)

vault-sync가 즉시 잡지 못한 **누적된 모순**을 일괄 정리한다.

### 감지

```
1. status: superseded 인데 아직 본문에 활성 서술로 남은 문서
2. 같은 주제에 상반된 결정이 공존하는 경우 (vault-sync에서 [b] 공존 선택분 재검토)
3. conventions/ 내 서로 어긋나는 규칙 쌍
   예: A문서 "_camelCase", B문서 "m_ 접두사"
```

graph.json이 있으면 같은 카테고리 노드 클러스터를 비교하여 상충 서술을 찾는다.
없으면 같은 폴더 내 문서를 Grep으로 대조한다.

### 정리 처리 (승인 게이트)

```
모순 쌍 발견 시:
→ 최신 결정 / 높은 confidence / 더 많은 참조를 가진 쪽을 우선(canonical)으로 제안
→ 사용자 확인 후:
   - 우선 결정을 canonical로 유지
   - 다른 쪽을 status: superseded + superseded_by 링크
   - 양쪽 다 유효한 맥락이면 "조건부 적용"으로 명시 (예: "신규 코드는 A, 레거시는 B")
```

### 정리 결과 출력

```
🔀 모순 정리 결과
────────────────────────────────────────
[1] 해결됨: coding-style 네이밍 규칙
    canonical: [[conventions/naming-camelcase]] (참조 8회, 2025-05)
    superseded: [[conventions/naming-mprefix]] (참조 1회, 2024-12)

[2] 조건부 유지: 직렬화 방식
    "신규: MessagePack / 레거시 세이브: 기존 방식"
    → architecture/serialization.md 에 조건 명시
────────────────────────────────────────
```

---

## 최종 출력 및 로그

세 작업 완료 후 종합 리포트와 evolve 로그를 남긴다.

```
🌱 vault-evolve 완료 — vault가 성장했습니다

📈 승격:   1건 (debugging 3건 → conventions 규칙 1개)
🧹 정제:   God nodes 3개 개선, 아카이브 2건
🔀 모순:   1건 해결, 1건 조건부 유지

vault 상태:
  활성 문서: 78 → 76 (아카이브 2)
  규칙 문서: 12 → 13 (승격 1)
────────────────────────────────────────
다음 evolve 권장: 약 1주 후 또는 승격 후보 3건 누적 시
```

```powershell
# evolve 로그 갱신 (PowerShell 도구) — Date.now류 금지, 오늘 날짜는 <env> Today's date 사용
Add-Content -Path "vault/.evolve-log" -Value "<YYYY-MM-DD>: promote=1 refine=3 archive=2 resolve=1" -Encoding utf8
```

### graphify 갱신 안내

이번 evolve로 **새 규칙 문서가 생성**되었거나 **문서가 아카이브로 이동**된 경우,
graph.json 구조가 바뀌므로 갱신을 안내한다 (vault-sync의 graphify 안내 기준과 동일).

```
🔄 graphify 갱신 필요 여부
  [필수] conventions/ui-canvas-rules.md 신규 생성 / archive 이동 2건
         → /graphify vault --update 를 지금 실행하세요.
         (미실행 시 vault-load가 새 규칙을 찾지 못하거나, 아카이브 문서를 계속 탐색합니다)
```

## 안전 원칙

- **삭제하지 않는다.** 아카이브는 이동, 모순은 superseded 표시. 모두 복구 가능.
- **규칙 생성·모순 해결은 사용자 승인을 받는다.** 정제(압축, 링크 복구, confidence 상향)는 자동 가능.
- **원본 근거를 보존한다.** 승격된 규칙은 항상 출처 사례를 wikilink로 연결.
- vault-evolve는 vault를 압축하지만, 압축 과정에서 **결정의 이력(왜 그렇게 됐는지)은 잃지 않는다.**

## 참고 파일

- `references/promotion-rules.md` → 승격 임계치 및 카테고리별 기준
- `references/evolve-examples.md` → 합성 전/후 예시
