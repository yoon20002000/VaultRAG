# 승격 규칙 (Promotion Rules)

vault-evolve의 "작업 1: 패턴 승격"에서 사용하는 임계치와 카테고리별 기준.

## 승격 임계치

| 항목 | 기본값 | 설명 |
|------|--------|------|
| 최소 반복 횟수 | **3회** | 같은 패턴/증상이 3건 이상 누적되어야 규칙으로 승격 |
| 신뢰도 부여 | `confidence: medium` | 3건 기반 규칙. 추가 사례 누적 시 vault-evolve가 high로 상향 |
| 출처 보존 | 필수 | 승격 규칙 본문에 원본 사례를 wikilink로 모두 연결 |

`promote_candidate: true` 플래그는 vault-sync가 누적 카운트로 부여한다.
vault-evolve는 이 플래그를 1차 수집 대상으로 삼되, 플래그가 없어도
유사 패턴이 임계치를 넘으면 승격 후보로 직접 그룹핑한다.

## 카테고리별 승격 방향

| 원본 카테고리 | 승격 대상 | 승격 조건 예시 |
|---------------|-----------|----------------|
| `debugging/` | `conventions/` 또는 `architecture/` | 같은 원인의 버그 해결이 반복 → 예방 규칙으로 일반화 |
| `debugging/` (성능) | `conventions/` 성능 규칙 | 동일 최적화가 반복 적용·수치 입증 → 규칙화 |
| `decisions/` (ADR) | `architecture/` | 여러 ADR이 같은 설계 원칙을 가리킴 → 원칙 문서로 통합 |
| `tech-debt/` | `conventions/` | 같은 부채 유형이 반복 → 작성 규칙으로 전환해 재발 방지 |

## 승격하지 않는 경우

- 사례가 1~2건뿐 (임계치 미달) → vault-sync가 카운트만 계속 누적
- 일회성/환경 특이 이슈 (재현 불가) → debugging에 사례로만 보존
- 사례 간 맥락이 상충 → 승격 대신 "모순 정리(작업 3)"로 회부
- 이미 동일 규칙이 conventions/에 존재 → 신규 생성 대신 기존 규칙에 사례 추가

## 승격 후 처리 체크리스트

1. [ ] 규칙 문서 생성/통합 (`conventions/` 등)
2. [ ] 규칙 본문에 출처 사례 wikilink 명시
3. [ ] 원본 사례들에 `promoted_to: [[규칙문서]]` 추가
4. [ ] 규칙 문서 `confidence: medium` 설정, `updated` 갱신
5. [ ] 새 규칙이 `conventions/coding-style.md`면 vault-sync 규약대로 CLAUDE.md 동기화 검토
6. [ ] graphify 갱신 안내 (새 문서 생성 시 필수)
