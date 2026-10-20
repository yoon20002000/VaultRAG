# 합성 전/후 예시 (Evolve Examples)

vault-evolve 세 작업의 구체적 전/후 예시. 실제 처리 시 형식 참고용.

---

## 예시 1: 패턴 승격 (Promotion)

### Before — debugging/에 유사 사례 3건 누적

```markdown
# debugging/performance-fixes.md (발췌)

## 2025-03-01 Canvas 통합으로 드로우콜 증가
모든 UI를 한 Canvas에 넣었더니 작은 갱신에도 전체 리빌드 발생.

## 2025-04-11 UI Canvas 분리 → 드로우콜 40% 감소
HP바처럼 자주 갱신되는 요소를 별도 Canvas로 분리.

## 2025-05-20 동적 UI를 별도 Canvas로 → 리빌드 비용 감소
인벤토리 슬롯 갱신 시 정적 UI까지 리빌드되던 문제 해결.
```

frontmatter: `promote_candidate: true`, `promote_count: 3`

### After — conventions/에 규칙 승격

```markdown
---
tags: [convention, unity, ui, performance]
created: <오늘날짜>
updated: <오늘날짜>
confidence: medium
---

# UI Canvas 분리 규칙

자주 갱신되는 UI와 정적 UI는 Canvas를 분리한다.
한 Canvas 내 요소가 하나라도 변하면 해당 Canvas 전체가 리빌드되기 때문.

**근거**: 드로우콜 40% 감소, 리빌드 비용 감소 (사례 3건 기반)

출처: [[debugging/performance-fixes#2025-03-01]]
[[debugging/performance-fixes#2025-04-11]]
[[debugging/performance-fixes#2025-05-20]]
```

원본 3개 사례에는 `promoted_to: [[conventions/ui-canvas-rules]]` 추가.
원본은 삭제하지 않고 근거로 보존한다.

---

## 예시 2: 지식 정제 (Refinement)

### God nodes 압축 — Before

```markdown
# architecture/event-system.md (중복 서술)

EventBus는 발행/구독 패턴이다. 발행자는 구독자를 모른다.
...(중략)...
EventBus는 pub/sub 구조로 발행자와 구독자가 서로를 알지 못한다.
```

### After — 중복 압축, confidence 상향

```markdown
# architecture/event-system.md

EventBus는 발행/구독(pub/sub) 패턴이다. 발행자와 구독자는 서로를 알지 못한다.
```

frontmatter `confidence: medium → high` (참조 12회로 검증됨), `updated` 갱신.
→ **자동 처리 가능** (의미 변화 없는 압축·링크 복구).

### 아카이브 — Before/After

```
Before: debugging/2024-11-temp-fix.md (7개월 미사용, 참조 0, confidence: low)
After:  vault/archive/2024-11-temp-fix.md
        frontmatter += archived: <오늘날짜>, archive_reason: "7개월 미사용, 고립 노드"
```

삭제가 아니라 이동. 필요 시 archive/에서 복구 가능.

---

## 예시 3: 모순 정리 (Resolution)

### Before — 상충하는 네이밍 규칙 2건 공존

```markdown
# conventions/naming-camelcase.md (2025-05, 참조 8회)
private 필드는 _camelCase 사용.

# conventions/naming-mprefix.md (2024-12, 참조 1회)
private 필드는 m_ 접두사 사용.
```

### After — canonical 확정 + superseded

```markdown
# conventions/naming-camelcase.md  (canonical 유지)
private 필드는 _camelCase 사용.
supersedes: [[conventions/naming-mprefix]]

# conventions/naming-mprefix.md
---
status: superseded
superseded_by: [[conventions/naming-camelcase]]
---
> [!warning] 이 규칙은 [[conventions/naming-camelcase]]로 대체되었습니다.
```

판단 근거: 최신(2025-05) + 높은 참조(8회) 쪽을 canonical로.
**사용자 승인 후** 처리. 양쪽 다 유효한 맥락이면 superseded 대신 조건부 적용으로 명시한다.
