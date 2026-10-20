# _index.base 작성 가이드

vault-init 실행 시 아래 템플릿을 기반으로 `vault/_index.base`를 생성.

## 기본 템플릿

```yaml
filters:
  and:
    - 'file.ext == "md"'
    - not:
        file.inFolder("_templates")
formulas:
  category: >
    if(file.inFolder("conventions"), "📐 컨벤션",
    if(file.inFolder("architecture"), "🏗️ 아키텍처",
    if(file.inFolder("debugging"), "🐛 디버깅",
    if(file.inFolder("decisions"), "📋 결정",
    if(file.inFolder("tech-debt"), "🔧 기술부채", "기타")))))
  is_empty: 'file.size < 200'
properties:
  formula.category:
    displayName: "카테고리"
  formula.is_empty:
    displayName: "작성 필요"
  updated:
    displayName: "최종 수정"
  confidence:
    displayName: "신뢰도"
views:
  - type: table
    name: "전체 문서"
    order:
      - formula.category
      - file.name
      - confidence
      - updated
      - formula.is_empty
    groupBy:
      property: formula.category
      direction: ASC
  - type: table
    name: "작성 필요"
    filters:
      and:
        - 'formula.is_empty == true'
    order:
      - formula.category
      - file.name
  - type: table
    name: "최근 수정"
    order:
      - file.mtime
    limit: 10
```

## 사용 목적

- `전체 문서` 뷰: vault 전체 현황 파악
- `작성 필요` 뷰: 아직 채워지지 않은 템플릿 문서 추적
- `최근 수정` 뷰: 최근에 업데이트된 문서 빠르게 확인

vault-sync 실행 시 문서가 추가/수정되면 이 .base 파일이 자동으로 반영됨.
별도 _index.md 수동 관리 불필요.
