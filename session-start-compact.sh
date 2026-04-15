#!/bin/bash
# vault session-start hook (compact matcher)
# compact 이후 세션 재시작 시 session-context.md를 Claude 컨텍스트에 주입
# SessionStart의 stdout은 Claude 컨텍스트에 직접 주입됨

VAULT_DIR="$CLAUDE_PROJECT_DIR/vault"
SESSION_CONTEXT="$VAULT_DIR/session-context.md"

# vault 폴더 없으면 무시
if [ ! -d "$VAULT_DIR" ]; then
    exit 0
fi

echo "⚠️  컨텍스트 압축 후 세션이 재시작되었습니다."
echo ""

# session-context.md가 있으면 내용 주입
if [ -f "$SESSION_CONTEXT" ]; then
    echo "📌 vault/session-context.md 에서 고정 컨텍스트를 로드합니다:"
    echo ""
    cat "$SESSION_CONTEXT"
    echo ""
    echo "추가 컨텍스트가 필요하면 /vault-load [키워드] 를 실행하세요."
else
    echo "vault/session-context.md 가 없습니다."
    echo "vault/session-context.md 를 직접 작성하면 매 세션 시작 시 자동으로 로드됩니다."
fi

exit 0
