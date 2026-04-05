#!/usr/bin/env python3
"""
Claude Code hook adapter.

settings.json:
  "hooks": {
    "UserPromptSubmit": [{"type": "command", "command": "python /c/turns/hooks/claude.py"}],
    "Stop": [{"type": "command", "command": "python /c/turns/hooks/claude.py"}]
  }
"""

import io
import json
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent.parent))
from turn import append_turn, append_tool_calls


def _extract_assistant_text(message):
    if message.get("type") != "assistant":
        return None
    content_parts = message.get("message", {}).get("content", [])
    if isinstance(content_parts, str):
        return content_parts
    texts = []
    for part in content_parts:
        if isinstance(part, str):
            texts.append(part)
        elif isinstance(part, dict) and part.get("type") == "text":
            texts.append(part.get("text", ""))
    return "\n".join(texts) if texts else None


def _extract_tool_calls(message):
    if message.get("type") != "assistant":
        return []
    content_parts = message.get("message", {}).get("content", [])
    if not isinstance(content_parts, list):
        return []
    calls = []
    for part in content_parts:
        if isinstance(part, dict) and part.get("type") == "tool_use":
            calls.append((part.get("name", ""), part.get("input", {}), part.get("tool_use_id", "")))
    return calls


def _extract_tool_results(message):
    if message.get("type") != "user":
        return {}
    content_parts = message.get("message", {}).get("content", [])
    if not isinstance(content_parts, list):
        return {}
    results = {}
    for part in content_parts:
        if isinstance(part, dict) and part.get("type") == "tool_result":
            tid = part.get("tool_use_id", "")
            content = part.get("content", "")
            if isinstance(content, list):
                content = "\n".join(
                    p.get("text", "") for p in content
                    if isinstance(p, dict) and p.get("type") == "text"
                )
            results[tid] = str(content)
    return results


def _format_tool(name, input_dict, result_text):
    MAX_RESULT = 500
    if name == "Bash":
        cmd = input_dict.get("command", "").replace("\n", " ").strip()
        if len(cmd) > 80:
            cmd = cmd[:77] + "..."
        truncated = result_text.strip()[:MAX_RESULT]
        if len(result_text) > MAX_RESULT:
            truncated += "\n... (truncated)"
        return f"- Bash `{cmd}`\n```\n{truncated}\n```\n"
    elif name in ("Read", "Edit", "Write"):
        path = input_dict.get("file_path", "")
        return f"- {name} `{path}`\n"
    elif name in ("Glob", "Grep"):
        pattern = input_dict.get("pattern", "")
        return f"- {name} `{pattern}`\n"
    else:
        return f"- {name}\n"


def handle_prompt(hook):
    prompt = hook.get("prompt", "")
    if not prompt.strip():
        return
    append_turn(
        session_id=hook.get("session_id", "unknown"),
        role="user",
        content=prompt,
        cwd=hook.get("cwd", ""),
        source="claude",
    )


def handle_stop(hook):
    transcript_path = hook.get("transcript_path", "")
    if not transcript_path or not Path(transcript_path).exists():
        return

    session_id = hook.get("session_id", "unknown")
    cwd = hook.get("cwd", "")

    try:
        lines = Path(transcript_path).read_text(encoding="utf-8").strip().split("\n")
    except Exception:
        return

    messages = []
    for line in lines:
        if not line.strip():
            continue
        try:
            messages.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    # 最後のアシスタントテキストを記録
    for msg in reversed(messages):
        text = _extract_assistant_text(msg)
        if text and text.strip():
            append_turn(session_id=session_id, role="assistant", content=text, cwd=cwd, source="claude")
            break

    # ツールコールを記録
    result_map = {}
    for msg in messages:
        result_map.update(_extract_tool_results(msg))

    md_parts = []
    for msg in messages:
        for name, input_dict, tid in _extract_tool_calls(msg):
            result_text = result_map.get(tid, "")
            md_parts.append(_format_tool(name, input_dict, result_text))

    if md_parts:
        append_tool_calls(session_id, md_parts)


def main():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return
        hook = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return

    event = hook.get("hook_event_name", "")
    if event == "UserPromptSubmit":
        handle_prompt(hook)
    elif event == "Stop":
        handle_stop(hook)


if __name__ == "__main__":
    main()
