#!/bin/bash
# vault pre-compact hook
# vault-sync가 완료된 경우에만 compact 허용
# vault가 없는 프로젝트에서는 항상 통과

VAULT_DIR="$CLAUDE_PROJECT_DIR/vault"
FLAG="$VAULT_DIR/.sync-done"

# vault 폴더 자체가 없으면 통과 (vault 미사용 프로젝트)
if [ ! -d "$VAULT_DIR" ]; then
    exit 0
fi

# sync 완료 플래그가 있으면 통과, 플래그 삭제
if [ -f "$FLAG" ]; then
    rm "$FLAG"
    exit 0
fi

# 플래그 없으면 차단
echo "vault-sync가 완료되지 않았습니다. /vault-sync 실행 후 다시 /compact 하세요." >&2
exit 2
