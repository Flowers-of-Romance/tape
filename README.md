# tape

全LLM会話をmarkdownに記録する。それだけ。

## 対応

| ツール | 方式 |
|---|---|
| Claude Code | hook |
| Gemini CLI | hook |
| Kiro | hook |
| Ollama | OpenAI互換APIラッパー |
| LM Studio | OpenAI互換APIラッパー |
| llama.cpp | OpenAI互換APIラッパー |

## セットアップ

### 1. config.json を編集

```json
{
  "output_dir": "~/Documents/Obsidian Vault/0110_ClaudeTurns",
  "timezone_offset_hours": 9
}
```

### 2. hookを登録

**Claude Code** (`~/.claude/settings.json`):
```json
{
  "hooks": {
    "UserPromptSubmit": [{"type": "command", "command": "python /c/turns/hooks/claude.py"}],
    "Stop": [{"type": "command", "command": "python /c/turns/hooks/claude.py"}]
  }
}
```

**Gemini CLI** (`.gemini/settings.json`):
```json
{
  "hooks": {
    "BeforeAgent": [{"hooks": [{"type": "command", "command": "python /c/turns/hooks/gemini.py"}]}],
    "AfterAgent": [{"hooks": [{"type": "command", "command": "python /c/turns/hooks/gemini.py"}]}]
  }
}
```

**Kiro**:
```json
{
  "hooks": {
    "PromptSubmit": [{"command": "python /c/turns/hooks/kiro.py"}],
    "AgentComplete": [{"command": "python /c/turns/hooks/kiro.py"}]
  }
}
```

### 3. ローカルLLM（hookなし）

Pythonから直接呼ぶ:

```python
from hooks.openai_compat import chat

# Ollama
chat("gemma2", [{"role": "user", "content": "hello"}])

# LM Studio
chat("local-model", messages, base_url="http://localhost:1234/v1")

# llama.cpp
chat("default", messages, base_url="http://localhost:8080/v1")
```

CLIから:

```bash
python hooks/openai_compat.py "こんにちは" --model gemma2
python hooks/openai_compat.py "hello" --url http://localhost:1234/v1
```

## 出力

日付別markdown (`YYYY-MM-DD.md`):

```markdown
---
title: "2026-04-06"
tags: [turns]
---

## 🐱 14:30 [project-name] session:abc12345 (claude)
> cwd: /c/memory

### 😊 User 🐱 14:30
こんにちは

### 🤖 Assistant 🐱 14:30
やあ
```

## 構成

```
tape/
├── turn.py              # コア（md追記ロジック）
├── config.json          # 出力先・タイムゾーン
├── hooks/
│   ├── claude.py        # Claude Code adapter
│   ├── gemini.py        # Gemini CLI adapter
│   ├── kiro.py          # Kiro adapter
│   └── openai_compat.py # Ollama / LM Studio / llama.cpp
└── README.md
```
