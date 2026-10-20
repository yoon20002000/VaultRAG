# ADR 번호 부여 규칙

## 번호 확인 방법

새 ADR 생성 전에 현재 가장 높은 번호를 확인:

```powershell
# Obsidian CLI 사용 시 (PowerShell 도구, vault="vault")
obsidian vault="vault" search query="adr-" path="decisions" limit=50
```
```bash
# 직접 확인 시 (폴백)
ls vault/decisions/adr-*.md | sort
```

## 파일명 형식

```
adr-NNN-kebab-case-title.md

예시:
adr-001-addressables-adoption.md
adr-002-event-bus-pattern.md
adr-003-save-system-json.md
```

## 번호 규칙

- 3자리 숫자, 001부터 시작
- 중간 번호 건너뛰지 않음
- 이미 존재하는 번호 재사용 금지
- 한번 부여된 번호는 ADR가 deprecated 되어도 변경하지 않음

## frontmatter status 값

| 값 | 의미 |
|----|------|
| `proposed` | 검토 중 |
| `accepted` | 채택됨 |
| `deprecated` | 더 이상 사용 안 함 |
| `superseded` | 다른 ADR로 대체됨 (superseded-by 필드 추가) |
