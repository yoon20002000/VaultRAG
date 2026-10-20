#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PostToolUse(Edit|Write) 훅 — vault/jobs/<job>.md(라이브) 를 고친 직후 lint_job_live 를 돌린다.
ERROR 가 있으면 exit 2 + stderr 로 모델에게 돌려준다. history · 다른 파일은 그냥 통과.
"""

import os
import sys
import json
import subprocess
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

LINT = Path(__file__).resolve().parent.parent / "skills" / "vault-sync" / "scripts" / "lint_job_live.py"


def main():
    try:
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8") or "{}")
    except Exception:
        return 0
    raw = (payload.get("tool_input") or {}).get("file_path") or ""
    p = raw.replace("\\", "/")
    if "/vault/jobs/" not in p or not p.endswith(".md") or p.endswith(".history.md"):
        return 0
    if not Path(raw).is_file():
        return 0
    r = subprocess.run([sys.executable, "-I", str(LINT), raw, "--quiet"],
                       capture_output=True, env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    if r.returncode == 2:
        sys.stderr.write(r.stdout.decode("utf-8", "replace"))
        sys.stderr.write("라이브 job 문서 규칙 위반 — 지금 고칠 것 (vault-sync SKILL 「교체의 구체 동작」).\n")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
