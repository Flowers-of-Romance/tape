#!/usr/bin/env python3
"""
OpenAI互換APIラッパー — Ollama, LM Studio, llama.cpp 等に対応

使い方:
    from hooks.openai_compat import chat

    # Ollama
    reply = chat("gemma2", [{"role": "user", "content": "hello"}],
                 base_url="http://localhost:11434/v1")

    # LM Studio
    reply = chat("local-model", messages, base_url="http://localhost:1234/v1")

    # llama.cpp
    reply = chat("default", messages, base_url="http://localhost:8080/v1")

    # デフォルトはOllama
    reply = chat("gemma2", messages)
"""

import io
import json
import sys
import uuid
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent.parent))
from turn import append_turn

DEFAULT_BASE_URL = "http://localhost:11434/v1"


def chat(model, messages, base_url=DEFAULT_BASE_URL, session_id=None, source=None):
    """OpenAI互換APIでチャットし、会話をmdに記録する。"""
    if session_id is None:
        session_id = uuid.uuid4().hex[:16]

    if source is None:
        if "11434" in base_url:
            source = "ollama"
        elif "1234" in base_url:
            source = "lmstudio"
        elif "8080" in base_url:
            source = "llama.cpp"
        else:
            source = "local"

    # ユーザー発言を記録
    user_msg = messages[-1].get("content", "") if messages else ""
    if user_msg:
        append_turn(session_id, "user", user_msg, source=source)

    # API呼び出し
    url = f"{base_url.rstrip('/')}/chat/completions"
    payload = json.dumps({"model": model, "messages": messages, "stream": False}).encode()
    req = Request(url, data=payload, headers={"Content-Type": "application/json"})

    try:
        with urlopen(req) as resp:
            data = json.loads(resp.read().decode())
    except URLError as e:
        print(f"[turns] API error: {e}", file=sys.stderr)
        raise

    reply = data["choices"][0]["message"]["content"]

    # アシスタント応答を記録
    append_turn(session_id, "assistant", reply, source=source)

    return reply


def main():
    """CLIとして直接使う: python openai_compat.py "質問" [--model X] [--url URL]"""
    import argparse
    parser = argparse.ArgumentParser(description="OpenAI互換LLMにチャットしてmdに記録")
    parser.add_argument("prompt", help="質問")
    parser.add_argument("--model", default="gemma2", help="モデル名 (default: gemma2)")
    parser.add_argument("--url", default=DEFAULT_BASE_URL, help="API base URL")
    parser.add_argument("--session", default=None, help="セッションID")
    args = parser.parse_args()

    reply = chat(
        model=args.model,
        messages=[{"role": "user", "content": args.prompt}],
        base_url=args.url,
        session_id=args.session,
    )
    print(reply)


if __name__ == "__main__":
    main()
