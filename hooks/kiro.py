#!/usr/bin/env python3
"""
Kiro CLI hook adapter.

Kiro hook config:
  "hooks": {
    "PromptSubmit": [{"command": "python /c/turns/hooks/kiro.py"}],
    "AgentComplete": [{"command": "python /c/turns/hooks/kiro.py"}]
  }
"""

import io
import json
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent.parent))
from turn import append_turn


def main():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return
        hook = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return

    event = hook.get("hook_event_name", "")
    session_id = hook.get("session_id", "unknown")
    cwd = hook.get("cwd", "")

    if event == "PromptSubmit":
        prompt = hook.get("prompt", "")
        if prompt.strip():
            append_turn(session_id=session_id, role="user", content=prompt, cwd=cwd, source="kiro")

    elif event == "AgentComplete":
        response = hook.get("response", hook.get("prompt_response", ""))
        if isinstance(response, str) and response.strip():
            append_turn(session_id=session_id, role="assistant", content=response, cwd=cwd, source="kiro")


if __name__ == "__main__":
    main()
