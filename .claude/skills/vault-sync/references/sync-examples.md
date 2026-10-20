# vault-sync 저장 예시

## ✅ 좋은 저장 예시

### 컨벤션 (구체적 규칙)
```
MonoBehaviour 생명주기 규칙:
- Awake: 자신의 컴포넌트 참조 및 초기화만 (GetComponent 허용)
- Start: 다른 오브젝트 참조 및 의존 초기화
- OnEnable: 이벤트 구독
- OnDisable: 이벤트 구독 해제
```

### 디버깅 (원인 + 해결 + 수치)
```
2025-04-11: 모바일 빌드 FPS 저하
- 증상: 특정 씬 진입 시 60fps → 20fps 드롭
- 원인: UI Canvas 1개에 모든 UI 포함 → 오버드로우 과다
- 해결: Canvas를 HUD / Popup / Overlay 3개로 분리
- 결과: 드로우콜 120 → 72 (40% 감소), FPS 55 안정
```

### ADR (근거 포함)
```
ADR-002: 이벤트 버스 패턴 채택
- 배경: 매니저 간 직접 참조로 인한 순환 의존성 문제 발생
- 결정: ScriptableObject 기반 이벤트 채널 사용
- 이유: 직렬화 가능, Inspector에서 연결 확인 가능, 테스트 용이
- 대안: C# event (Inspector 연결 불가), UnityEvent (성능 이슈)
```

---

## ❌ 나쁜 저장 예시 (저장 후보에서 제외)

### 단순 사실 (규칙이 아님)
```
❌ "오늘 PlayerController에서 Awake 사용했어요"
→ 재사용 가능한 규칙이 아님
```

### 근거 없는 의견
```
❌ "Addressables가 좋을 것 같아요"
→ 왜 좋은지, 채택했는지 불명확
```

### 일회성 이슈
```
❌ "TestScene에서 NullReference 났는데 씬 재로드로 해결됨"
→ 재현 불가, 다른 세션에서 쓸모없음
```

### 너무 광범위
```
❌ "코드를 잘 작성해야 한다"
→ 구체성 없음, 실행 불가능
```

---

## 저장 시 문서 배치 기준

| 내용 유형 | 저장 위치 |
|----------|-----------|
| 팀 합의 코딩 규칙 | conventions/ |
| 씬/프리팹/에셋 규칙 | conventions/ |
| 시스템 설계 방식 | architecture/ |
| 버그 원인 + 해결 | debugging/ |
| 기술 선택 근거 | decisions/ (ADR) |
| 나중에 고쳐야 할 것 | tech-debt/ |
| iOS/Android 특이사항 | debugging/mobile-specific.md |

---

## 성장 신호 예시 (Step 3.5 모순 감지 / 승격 후보 카운트)

### 모순 감지 — 저장 직전 충돌 발견

```
새 결정: "씬 전환은 Command 패턴으로 통일"
기존:    [[decisions/adr-002-eventbus]] "이벤트 버스 채택" (2025-03)

→ Step 4 승인 목록에 ⚠️ 모순 항목으로 노출
→ [s] 기존 superseded 처리 / [b] 공존(조건 명시) / [n] 취소
```

`[s]` 선택 결과:
- 기존 문서: `status: superseded`, `superseded_by: [[새문서]]`
- 새 문서: `supersedes: [[decisions/adr-002-eventbus]]`
- 결정 이력이 frontmatter로 추적됨 (삭제 없음)

### 승격 후보 카운트 — 반복 패턴 누적

```
debugging/performance-fixes.md 에 Canvas 분리 사례가 3번째 저장됨
→ frontmatter promote_count: 3, promote_candidate: true 부여
→ 완료 출력 🌱 성장 신호:
   "📈 승격 후보: Canvas 분리 패턴 3회 누적 → /vault-evolve 검토 권장"
```

여기서는 **카운트와 플래그만** 남긴다. 실제 규칙 승격(합성)은 `/vault-evolve`가 처리.
