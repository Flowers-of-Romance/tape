#!/usr/bin/env python3
"""
turn.py — 会話ターンをマークダウンに追記するコアモジュール

CLI非依存。各hookアダプターから呼ばれる。
"""

import io
import json
import os
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

_SESSION_ANIMALS = [
    "\U0001f431", "\U0001f436", "\U0001f98a", "\U0001f438",
    "\U0001f419", "\U0001f989", "\U0001f43b", "\U0001f43a",
    "\U0001f988", "\U0001f427", "\U0001f98e", "\U0001f41d",
    "\U0001f98b", "\U0001f42c", "\U0001f985", "\U0001f422",
]


def load_config():
    config_path = Path(__file__).parent / "config.json"
    if not config_path.exists():
        return {"output_dir": ".", "timezone_offset_hours": 9}
    return json.loads(config_path.read_text(encoding="utf-8"))


def _locked_append(filepath, text):
    """ファイルロック付きappend。複数ウィンドウで同時書き込みしても安全。"""
    lock_path = Path(str(filepath) + ".lock")
    lock_fd = None
    try:
        for _ in range(10):
            try:
                lock_fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                break
            except FileExistsError:
                time.sleep(0.05)
        else:
            with open(filepath, "a", encoding="utf-8") as f:
                f.write(text)
            return

        with open(filepath, "a", encoding="utf-8") as f:
            f.write(text)
    finally:
        if lock_fd is not None:
            os.close(lock_fd)
            try:
                os.remove(str(lock_path))
            except OSError:
                pass


def _pick_user_face(content):
    c = (content or "").lower()
    if any(w in c for w in ["ふざけ", "おかしい", "バグ", "だめ", "ひどい", "最悪", "むかつ", "壊れ", "なんで"]):
        return "\U0001f624"
    if any(w in c for w in ["\uff1f", "?", "わからん", "わからない", "なぜ", "どうして", "どういう"]):
        return "\U0001f914"
    if any(w in c for w in ["ありがと", "さんきゅ", "助かる", "最高", "いいね", "すごい", "やった", "完璧"]):
        return "\U0001f606"
    if any(w in c for w in ["おはよ", "こんにち", "こんばん", "おつかれ", "ただいま", "よろしく"]):
        return "\U0001f60a"
    if any(w in c for w in ["して", "やって", "頼む", "お願い", "変えて", "直して", "作って", "見せて"]):
        return "\U0001f619"
    if any(w in c for w in ["\uff01", "!", "www", "笑", "\uff57", "草"]):
        return "\U0001f61c"
    if len(c) < 10:
        return "\U0001f642"
    return "\U0001f600"


def _is_noise(content):
    if not content:
        return True
    if any(m in content for m in [
        "Background command", "toolu_",
        "completed (exit code", "Read the output file",
    ]):
        return True
    stripped = re.sub(r"<[^>]+>", "", content).strip()
    if not stripped:
        return True
    return False


def _session_animal(session_id):
    short = session_id[:8]
    try:
        idx = int(short, 16) % len(_SESSION_ANIMALS)
    except ValueError:
        idx = hash(short) % len(_SESSION_ANIMALS)
    return _SESSION_ANIMALS[idx], short


def append_turn(session_id, role, content, cwd="", source=""):
    """1ターンをmdに追記する。全アダプターが呼ぶ共通エントリーポイント。"""
    if _is_noise(content):
        return

    config = load_config()
    output_dir = Path(os.path.expandvars(config["output_dir"])).expanduser()
    offset = config.get("timezone_offset_hours", 9)

    local = datetime.now(timezone.utc) + timedelta(hours=offset)
    date_str = local.strftime("%Y-%m-%d")
    time_str = local.strftime("%H:%M")
    md_path = output_dir / f"{date_str}.md"

    output_dir.mkdir(parents=True, exist_ok=True)

    animal, short_sid = _session_animal(session_id)
    icon = f"{_pick_user_face(content)} User" if role == "user" else "\U0001f916 Assistant"
    project_name = Path(cwd).name if cwd else ""
    source_tag = f" ({source})" if source else ""

    if not md_path.exists():
        text = f"---\ntitle: \"{date_str}\"\ntags: [turns]\n---\n\n"
        label = f"## {animal} {time_str}"
        if project_name:
            label += f" [{project_name}]"
        label += f" session:{short_sid}{source_tag}\n"
        text += label
        if cwd:
            text += f"> cwd: {cwd}\n"
        text += f"\n### {icon} {animal} {time_str}\n{content}\n"
        md_path.write_text(text, encoding="utf-8")
    else:
        existing = md_path.read_text(encoding="utf-8")
        entry = ""
        if f"session:{short_sid}" not in existing:
            label = f"\n---\n\n## {animal} {time_str}"
            if project_name:
                label += f" [{project_name}]"
            label += f" session:{short_sid}{source_tag}\n"
            entry += label
            if cwd:
                entry += f"> cwd: {cwd}\n"
        entry += f"\n### {icon} {animal} {time_str}\n{content}\n"
        _locked_append(md_path, entry)


def append_tool_calls(session_id, tool_parts):
    """ツールコールをcalloutとしてmdに追記。"""
    if not tool_parts:
        return

    config = load_config()
    output_dir = Path(os.path.expandvars(config["output_dir"])).expanduser()
    offset = config.get("timezone_offset_hours", 9)

    local = datetime.now(timezone.utc) + timedelta(hours=offset)
    date_str = local.strftime("%Y-%m-%d")
    md_path = output_dir / f"{date_str}.md"

    if not md_path.exists():
        return

    callout_lines = ["> [!info]- \U0001f527 Tool calls"]
    for part in tool_parts:
        for line in part.rstrip("\n").split("\n"):
            callout_lines.append(f"> {line}")
    _locked_append(md_path, "\n" + "\n".join(callout_lines) + "\n")
