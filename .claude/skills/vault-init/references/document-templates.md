# 카테고리별 문서 템플릿

vault-init 실행 시 각 문서의 초기 내용으로 사용.
스캔에서 내용이 감지된 경우 해당 내용으로 대체, 미감지 시 이 템플릿 그대로 사용.

---

## conventions/coding-style.md

```markdown
---
tags: [convention, unity, csharp]
created: {{DATE}}
updated: {{DATE}}
confidence: low
---

# C# 코딩 스타일

## 네이밍 규칙

| 대상 | 규칙 | 예시 |
|------|------|------|
| 클래스 | PascalCase | `PlayerController` |
| 메서드 | PascalCase | `TakeDamage()` |
| 변수 (private) | camelCase + _ 접두사 | `_health` |
| 변수 (public) | camelCase | `health` |
| 상수 | ALL_CAPS | `MAX_HEALTH` |
| 인터페이스 | I + PascalCase | `IDamageable` |

## MonoBehaviour 구조

> [!todo] 작성 필요
> Awake / Start / OnEnable 역할 분리 규칙을 작성하세요.

## 네임스페이스

> [!todo] 작성 필요
> 프로젝트 네임스페이스 구조를 작성하세요.
```

---

## conventions/scene-hierarchy.md

```markdown
---
tags: [convention, unity, scene]
created: {{DATE}}
updated: {{DATE}}
confidence: low
---

# 씬 계층 구조 규칙

## 최상위 오브젝트 구성

> [!todo] 작성 필요
> 씬 루트 오브젝트 구성 규칙을 작성하세요.
> 예: _Managers, _UI, _Gameplay, _Environment 등

## 오브젝트 네이밍

> [!todo] 작성 필요

## 씬 목록

> [!todo] 작성 필요
> 프로젝트의 씬 목록과 각 씬의 역할을 작성하세요.
```

---

## conventions/prefab-rules.md

```markdown
---
tags: [convention, unity, prefab]
created: {{DATE}}
updated: {{DATE}}
confidence: low
---

# 프리팹 규칙

## 네이밍 컨벤션

> [!todo] 작성 필요
> 예: PFB_PlayerCharacter, UI_HealthBar 등

## 폴더 구조

> [!todo] 작성 필요

## Nested Prefab 사용 규칙

> [!todo] 작성 필요
```

---

## conventions/asset-management.md

```markdown
---
tags: [convention, unity, asset, addressables]
created: {{DATE}}
updated: {{DATE}}
confidence: low
---

# 에셋 관리 규칙

## 폴더 구조

> [!todo] 작성 필요
> Assets/ 하위 폴더 구조 규칙

## Addressables 사용 여부

> [!todo] 작성 필요
> Addressables를 사용하는 경우 그룹 구조와 네이밍 규칙 작성

## 에셋 네이밍

> [!todo] 작성 필요
```

---

## architecture/event-system.md

```markdown
---
tags: [architecture, unity, event]
created: {{DATE}}
updated: {{DATE}}
confidence: low
---

# 이벤트 시스템

## 방식 선택

> [!todo] 작성 필요
> UnityEvent / C# event / ScriptableObject 이벤트 / 커스텀 이벤트 버스 중 어떤 방식을 사용하는지 작성

## 사용 예시

> [!todo] 작성 필요

관련 문서: [[game-manager-pattern]]
```

---

## architecture/save-system.md

```markdown
---
tags: [architecture, unity, save]
created: {{DATE}}
updated: {{DATE}}
confidence: low
---

# 세이브 시스템

## 저장 방식

> [!todo] 작성 필요
> PlayerPrefs / JSON / Binary / 클라우드 등

## 저장 데이터 구조

> [!todo] 작성 필요

## 저장 시점

> [!todo] 작성 필요
```

---

## architecture/game-manager-pattern.md

```markdown
---
tags: [architecture, unity, pattern, singleton]
created: {{DATE}}
updated: {{DATE}}
confidence: low
---

# 게임 매니저 패턴

## 싱글톤 사용 방침

> [!todo] 작성 필요
> 싱글톤 허용 여부, 대안 패턴 (ServiceLocator, DI 등) 작성

## 매니저 목록

> [!todo] 작성 필요
> GameManager, AudioManager, UIManager 등 현재 프로젝트의 매니저 목록

관련 문서: [[event-system]]
```

---

## debugging/performance-fixes.md

```markdown
---
tags: [debugging, unity, performance]
created: {{DATE}}
updated: {{DATE}}
confidence: low
---

# 퍼포먼스 최적화 기록

> [!info] 사용법
> 프로파일링을 통해 성능 문제를 해결한 경우 날짜와 함께 기록하세요.

## 기록 형식

\`\`\`
### YYYY-MM-DD: [문제 요약]
- 증상: 
- 원인: 
- 해결: 
- 결과: (수치가 있으면 기재)
\`\`\`
```

---

## debugging/mobile-specific.md

```markdown
---
tags: [debugging, unity, mobile, ios, android]
created: {{DATE}}
updated: {{DATE}}
confidence: low
---

# 모바일 플랫폼 특이사항

## iOS

> [!todo] 작성 필요
> IL2CPP 관련 주의사항, 권한 처리 등

## Android

> [!todo] 작성 필요
> targetSdkVersion, 권한 처리 등

## 공통

> [!todo] 작성 필요
```

---

## tech-debt/refactor-list.md

```markdown
---
tags: [tech-debt, refactor]
created: {{DATE}}
updated: {{DATE}}
---

# 기술 부채 목록

> [!warning] 관리 방법
> vault-sync 실행 시 발견된 기술 부채를 자동으로 추가 제안합니다.
> 완료된 항목은 삭제하지 말고 `~~취소선~~`으로 표시하세요.

## 높은 우선순위

- [ ] 

## 낮은 우선순위

- [ ] 
```

---

## decisions/adr-template.md

```markdown
---
tags: [decision, adr]
created: {{DATE}}
updated: {{DATE}}
status: proposed | accepted | deprecated | superseded
---

# ADR-000: [결정 제목]

## 상태
proposed

## 컨텍스트
어떤 상황에서 이 결정이 필요했는지 설명

## 결정
무엇을 결정했는지

## 이유
왜 이 결정을 내렸는지

## 결과
이 결정으로 인해 예상되는 결과 (긍정/부정)

## 대안
고려했지만 선택하지 않은 대안들
```
