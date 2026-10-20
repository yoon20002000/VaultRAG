# .obsidian 설정 가이드

vault-init 실행 시 `vault/.obsidian/app.json`을 생성.
이 파일이 있어야 Obsidian이 해당 폴더를 vault로 인식.

## app.json 최소 설정

```json
{
  "legacyEditor": false,
  "livePreview": true,
  "defaultViewMode": "source",
  "foldHeading": true,
  "showLineNumber": true,
  "spellcheck": false,
  "strictLineBreaks": false,
  "showFrontmatter": false
}
```

## community-plugins.json (선택)

팀에서 공통으로 사용하는 플러그인 목록을 git으로 공유할 때:

```json
[]
```

초기에는 빈 배열로 생성. 팀에서 플러그인 추가 시 직접 수정.

## .gitignore 처리

`.obsidian/` 폴더는 git에 포함시켜 팀 간 설정 공유.
단, 아래 항목은 .gitignore에 추가:

```
vault/.obsidian/workspace.json
vault/.obsidian/workspace-mobile.json
vault/.obsidian/cache
```

`workspace.json`은 개인 UI 상태를 저장하므로 git에서 제외.

## vault-init에서 생성할 파일 목록

```
vault/.obsidian/app.json          ← 항상 생성
vault/.obsidian/community-plugins.json  ← 빈 배열로 생성
```

프로젝트 루트 `.gitignore`에 workspace 관련 항목 자동 추가.
