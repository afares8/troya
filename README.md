# Cascade CLI v3.0 — The Ultimate Coding Assistant

A terminal-based AI coding assistant inspired by Windsurf/Cascade. **One CLI. Everything included.**

Connects to your own LLM models (OpenAI, Anthropic, Ollama, Groq, or custom endpoints) and provides a rich chat interface with filesystem access, safe command execution, Git integration, file editing with diff preview, project search, session persistence, **agentic reasoning**, **semantic code search**, **task planning**, **file watching**, **self-improvement**, **plugin system**, **project scaffolding**, **smart project detection**, **MCP protocol support**, **multi-agent delegation**, **embedded web dashboard**, **shell completions**, **Docker support**, and a **comprehensive test suite**.

## Features

- **Multi-provider LLM support**: OpenAI, Anthropic Claude, Ollama (local), Groq, or any custom OpenAI-compatible API
- **Rich terminal UI**: Tab autocomplete for commands and file paths, command history, key bindings (Ctrl+X=exit, Ctrl+L=clear)
- **Agentic reasoning** (`/agentic` or prefix `!`): AI autonomously reads files, searches code, runs commands, and writes files to accomplish tasks
- **Task planner** (`/plan`): Decomposes complex requests into multi-step plans with the LLM
- **Semantic code search** (`/index` + `/search`): TF-IDF based indexing for intelligent context retrieval across your codebase
- **File watcher** (`/watch`): Monitors file changes and proactively suggests actions
- **Self-improvement** (`/improve`): AI analyzes its own code and proposes/applies fixes
- **Plugin system** (`/plugins`): Dynamically load slash commands from `.py` files
- **Project scaffolding** (`/scaffold`): Generate complete projects from templates (React, FastAPI, Flask, Python CLI)
- **Smart project detection** (`/detect`): Auto-detects project type and loads relevant context
- **MCP protocol** (`/mcp`): Connect to external tool servers via Model Context Protocol
- **Shell completions**: Bash and Zsh tab completion scripts
- **Docker support**: Containerized deployment ready
- **Test suite**: 16+ pytest tests covering core modules
- **File context**: Read files into conversation context with `/read`
- **File editing with diff**: AI-suggested file changes show a unified diff before you approve them
- **Safe command execution**: Commands classified as safe/dangerous with user confirmation
- **Git integration**: Status, diff, log, and commit directly from the REPL
- **Project search**: `/grep <pattern>` searches across all project files
- **Directory tree**: `/tree` visualizes project structure with file sizes
- **Project stats**: `/stats` shows file counts, sizes, and language breakdown
- **Streaming responses**: Real-time typing with token count and cost estimation
- **Syntax highlighting**: Code blocks rendered with Pygments in the terminal
- **Session persistence**: Save, load, list, and export conversations to Markdown
- **Config profiles**: Quickly switch between provider/model presets
- **Multiline input**: Use `"""` or `'''` delimiters for multiline prompts

## Installation

```bash
cd cascade-cli
pip install -r requirements.txt
python -m cascade.main --setup
```

Or install as a package:

```bash
pip install -e .
cascade --setup
```

## Quick Start

```bash
# Start with default config
cascade

# Override provider/model on the fly
cascade --provider groq --model llama-3.1-70b-versatile --api-key gsk-...

# Switch to a preset profile
cascade --profile ollama
```

## Configuration

### Option 1: Setup Wizard
```bash
cascade --setup
```

### Option 2: Environment Variables
```bash
export CASCADE_PROVIDER=openai
export CASCADE_API_KEY=sk-your-key-here
export CASCADE_MODEL=gpt-4o
```

### Option 3: Config File
Edit `~/.config/cascade-cli/config.json`:
```json
{
  "provider": "openai",
  "model": "gpt-4o",
  "api_key": "sk-...",
  "max_tokens": 4096,
  "temperature": 0.7,
  "profile": "default",
  "profiles": {
    "work": {"provider": "openai", "model": "gpt-4o"},
    "home": {"provider": "ollama", "model": "llama3.1"}
  }
}
```

## Commands Reference

### File & Directory
| Command | Description |
|---------|-------------|
| `/read <file>` | Read a file into context |
| `/ls [path]` | List directory contents |
| `/cd <path>` | Change working directory |
| `/tree [path] [depth]` | Show directory tree |
| `/stats` | Show project statistics |

### Search & Edit
| Command | Description |
|---------|-------------|
| `/grep <pattern> [file-pattern]` | Search regex across project files |
| `/search <query>` | Semantic code search using indexed TF-IDF |
| `/index` | Build code index for intelligent search |
| `/run <command>` | Execute shell command (with confirmation) |

### Agentic & AI
| Command | Description |
|---------|-------------|
| `/agentic` | Toggle autonomous mode (AI uses tools automatically) |
| `/plan <task>` | Create a multi-step plan for a task |
| `/watch` | Watch files and suggest actions on changes |
| `! <question>` | One-shot agentic query (autonomous tool use) |

### Git
| Command | Description |
|---------|-------------|
| `/git` | Show git status, branch, and changes |
| `/git-log [n]` | Show recent commits |
| `/git-diff` | Show working tree diff |
| `/commit <message>` | Stage all and commit |

### Session
| Command | Description |
|---------|-------------|
| `/save` | Save conversation to disk |
| `/load <id>` | Load a previous session |
| `/sessions` | List saved sessions |
| `/export [path]` | Export conversation to markdown |

### Config
| Command | Description |
|---------|-------------|
| `/profile <name>` | Switch configuration profile |
| `/profiles` | List available profiles |
| `/setup` | Run setup wizard |

### General
| Command | Description |
|---------|-------------|
| `/context` | Show current context info |
| `/history` | Show executed command history |
| `/clear` | Clear conversation and file context |
| `/help` | Show this message |
| `/exit` | Exit and save session |

## Providers

### OpenAI
```bash
export CASCADE_PROVIDER=openai
export CASCADE_API_KEY=sk-...
export CASCADE_MODEL=gpt-4o
```

### Anthropic Claude
```bash
export CASCADE_PROVIDER=anthropic
export CASCADE_API_KEY=sk-ant-...
export CASCADE_MODEL=claude-3-5-sonnet-20241022
```

### Ollama (Local)
```bash
export CASCADE_PROVIDER=ollama
export CASCADE_API_KEY=ollama
export CASCADE_MODEL=llama3.1
export CASCADE_API_BASE=http://localhost:11434/v1
```

### Groq
```bash
export CASCADE_PROVIDER=groq
export CASCADE_API_KEY=gsk-...
export CASCADE_MODEL=llama-3.1-70b-versatile
```

### Custom Endpoint
```bash
export CASCADE_PROVIDER=custom
export CASCADE_API_KEY=your-key
export CASCADE_MODEL=your-model
export CASCADE_API_BASE=https://your-api.com/v1
```

## Architecture

```
cascade/
├── __init__.py          # Package init
├── __main__.py          # python -m cascade entry point
├── main.py              # Entry point, REPL loop, prompt_toolkit UI
├── agentic.py           # Autonomous reasoning with tool use loop
├── config.py            # Config management with profiles
├── context.py           # Conversation and file context + tree/grep
├── editor.py            # File edit detection, diff preview, apply/reject
├── executor.py          # Safe command execution with classification
├── git_utils.py         # Git status, diff, log, commit helpers
├── indexer.py           # TF-IDF code index for semantic search
├── inline_complete.py   # Copilot-style inline completions
├── llm.py               # LLM client (multi-provider, streaming, token count)
├── persistence.py       # Session save/load/list/export
├── planner.py           # Task decomposition into multi-step plans
├── plugins.py           # Dynamic plugin loading system
├── project_detector.py  # Auto-detect project type and load context
├── scaffold.py          # Project scaffolding templates
├── search.py            # Directory tree, grep search, project stats
├── self_improve.py      # AI analyzes and improves its own code
├── watch.py             # File watcher with proactive suggestions
└── ui.py                # Terminal colors, syntax highlighting, markdown render
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Tab` | Autocomplete slash commands and file paths |
| `Ctrl+X` | Exit Cascade |
| `Ctrl+L` | Clear terminal screen |
| `Shift+Enter` | New line in multiline mode |
| `↑/↓` | Browse command history |

## License

MIT
