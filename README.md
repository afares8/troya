# Troya CLI v3.7.2 — AI Coding Assistant

> Previously Cascade CLI. A terminal-based AI coding assistant inspired by Windsurf/Cascade and Devin AI.

**One CLI. Everything included.**

Troya connects to your own LLM models (OpenAI, Anthropic, Ollama, Groq, or custom endpoints) and provides a rich chat interface with filesystem access, safe command execution, Git integration, file editing with diff preview, project search, session persistence, autonomous agent mode, semantic code search, task planning, file watching, self-improvement, plugin system, project scaffolding, smart project detection, MCP protocol support, multi-agent delegation, embedded web dashboard, shell completions, Docker support, and a comprehensive test suite.

## Features

- **Multi-provider LLM support**: OpenAI, Anthropic Claude, Ollama (local), Groq, or any custom OpenAI-compatible API
- **Rich terminal UI**: Tab autocomplete for commands and file paths, command history, key bindings (Ctrl+X=exit, Ctrl+L=clear)
- **Autonomous agent mode** (`/agent`): Plan-execute-heal loop with checkpoints
- **Task planner** (`/plan`): Decomposes complex requests into multi-step plans
- **Semantic code search** (`/index` + `/search`): TF-IDF based indexing for intelligent context retrieval
- **File watcher** (`/watch`): Monitors file changes and proactively suggests actions
- **Security scanner** (`/scan`): Detects secrets, eval, hardcoded passwords
- **Code quality analyzer** (`/quality`): AST-based quality metrics
- **Auto-format & lint** (`/fmt`, `/lint`): Black, ruff, flake8 integration
- **Self-healing** (`/heal`): Auto-detect and fix broken code
- **Plugin system** (`/plugins`): Dynamically load slash commands from `.py` files
- **Project scaffolding** (`/scaffold`): Generate complete projects from templates
- **Smart project detection** (`/detect`): Auto-detects project type and loads relevant context
- **Fuzzy file finder** (`/fzf`): fzf-like file search
- **Bookmark system** (`/bookmark`): Save code locations for quick navigation
- **Snippet manager** (`/snippet`): Reusable code snippets with tags
- **Memory/knowledge base** (`/memory`): Persistent corrections and preferences
- **Skill learning** (`/skills`): Learn and apply coding patterns
- **Persistent checkpoints** (`/checkpoint`): Save and resume agent state
- **Web research** (`/research`): Search and scrape documentation
- **GitHub integration** (`/github`): PRs, issues, branches via gh CLI
- **Benchmark suite** (`/benchmark`): Performance measurement
- **Task runners** (`/tasks`): make, npm, poetry, cargo, just integration
- **Clipboard integration** (`/copy`): Copy file content to system clipboard
- **Time tracking** (`/time`): Track time per project
- **Recipe system** (`/recipe`): Declarative workflows
- **Shell completions**: Bash and Zsh tab completion scripts
- **Docker support**: Containerized deployment ready
- **Test suite**: 58 pytest tests covering core modules
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
- **Offline mode**: Works without API key for local commands

## Installation

```bash
git clone https://github.com/afares8/troya.git
cd troya
pip install -r requirements.txt
pip install -e .
troya --setup
```

Or run without installing:

```bash
cd troya
pip install -r requirements.txt
python3 -m cascade.main
```

## Quick Start

```bash
# Start with default config
troya

# Override provider/model on the fly
troya --provider groq --model llama-3.1-70b-versatile --api-key gsk-...

# Switch to a preset profile
troya --profile ollama

# Offline mode (no API key needed)
troya --provider offline
```

## Configuration

### Option 1: Setup Wizard
```bash
troya --setup
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
| `/fzf <query>` | Fuzzy find files |

### Search & Edit
| Command | Description |
|---------|-------------|
| `/grep <pattern> [file-pattern]` | Search regex across project files |
| `/search <query>` | Semantic code search using indexed TF-IDF |
| `/index` | Build code index for intelligent search |
| `/embed` | Build real semantic embeddings index |
| `/run <command>` | Execute shell command (with confirmation) |
| `/copy <file>` | Copy file content to clipboard |

### Agentic & AI
| Command | Description |
|---------|-------------|
| `/agentic` | Toggle autonomous mode |
| `/agent <task>` | Run autonomous agent on a task |
| `/plan <task>` | Create a multi-step plan for a task |
| `/agents <task>` | Multi-agent task delegation |
| `/watch` | Watch files and suggest actions |
| `! <question>` | One-shot agentic query |

### Code Quality & Security
| Command | Description |
|---------|-------------|
| `/scan` | Security scan for secrets and vulnerabilities |
| `/quality` | Analyze code quality with AST metrics |
| `/fmt <file>` | Auto-format with black/ruff |
| `/lint <file>` | Lint with ruff/flake8 |
| `/heal <file>` | Auto-detect and fix broken code |

### Explain & Navigate
| Command | Description |
|---------|-------------|
| `/explain file <file>` | Explain file structure |
| `/explain function <name> <file>` | Explain a function |
| `/bookmark <name> [file] [line]` | Save a bookmark |
| `/bookmarks` | List bookmarks |
| `/jump <name>` | Jump to bookmark |

### Snippets & Memory
| Command | Description |
|---------|-------------|
| `/snippet <name> <language>` | Save a code snippet |
| `/snippets` | List snippets |
| `/memory` | Show learned memory |
| `/skills` | Show learned skills |
| `/checkpoint <task>` | Create checkpoint |
| `/checkpoints` | List checkpoints |

### External Tools
| Command | Description | Requirements |
|---------|-------------|-------------|
| `/research <topic>` | Research on the web | internet |
| `/github <subcommand>` | GitHub integration | `gh` CLI |
| `/browser <url>` | Open URL with Playwright | `playwright` |
| `/voice` | Record voice and chat | `ffmpeg` |
| `/rag <query>` | Semantic search with embeddings | `sentence-transformers` |
| `/embed` | Build embeddings index | `sentence-transformers` |

### Git
| Command | Description |
|---------|-------------|
| `/git` | Show git status |
| `/git-log [n]` | Show recent commits |
| `/git-diff` | Show working tree diff |
| `/review [commit]` | Review git diff for issues |
| `/commit <message>` | Stage all and commit |
| `/deps` | Show dependency graph |

### Tasks & Benchmarks
| Command | Description |
|---------|-------------|
| `/tasks` | List available task runners |
| `/run-task <task>` | Run a task (make build, npm test) |
| `/benchmark <func>` | Benchmark a Python function |
| `/time` | Show time tracking stats |
| `/recipe <name>` | Run a workflow recipe |
| `/recipes` | List available recipes |

### Session & Config
| Command | Description |
|---------|-------------|
| `/save [name]` | Save conversation |
| `/load <id>` | Load a session |
| `/sessions` | List saved sessions |
| `/export [path]` | Export to markdown |
| `/profile <name>` | Switch config profile |
| `/profiles` | List profiles |
| `/setup` | Run setup wizard |

### General
| Command | Description |
|---------|-------------|
| `/context` | Show current context info |
| `/history` | Show command history |
| `/clear` | Clear context |
| `/help` | Show help |
| `/dashboard` | Launch web dashboard |
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

### Offline Mode
```bash
export CASCADE_PROVIDER=offline
```

## Architecture

```
cascade/
├── __init__.py           # Package init & version
├── __main__.py           # python -m cascade entry point
├── main.py               # Entry point, REPL loop, prompt_toolkit UI
├── agentic.py            # Autonomous reasoning with tool use
├── autonomous.py         # Autonomous agent with checkpoints
├── benchmarks.py         # Performance benchmarking
├── bookmarks.py          # Code bookmark system
├── browser.py            # Playwright browser integration
├── checkpoints.py        # Persistent checkpoint system
├── clipboard.py          # System clipboard integration
├── completions.py        # Shell tab completions
├── config.py             # Config management with profiles
├── context.py            # Conversation and file context
├── dashboard.py          # Embedded FastAPI web dashboard
├── deps_graph.py         # Dependency graph analyzer
├── diff.py               # File diff comparison
├── edit_parser.py        # Advanced LLM edit parsing
├── editor.py             # File edit detection and diff preview
├── embeddings.py         # Semantic embeddings index
├── executor.py           # Safe command execution
├── explain.py            # Code explanation engine
├── formatter.py          # Auto-formatting (black, ruff)
├── fuzzy.py              # Fuzzy file finder
├── github_client.py      # GitHub integration via gh CLI
├── git_review.py         # Git diff review
├── git_utils.py          # Git status, diff, log, commit
├── indexer.py            # TF-IDF code index
├── inline_complete.py    # Copilot-style inline completions
├── llm.py                # LLM client (multi-provider)
├── memory.py             # Persistent memory store
├── mcp_client.py         # MCP protocol client
├── planner.py            # Task decomposition
├── plugins.py            # Dynamic plugin loading
├── project_detector.py   # Auto-detect project type
├── quality.py            # AST-based quality analyzer
├── recipes.py            # Declarative workflow recipes
├── sandbox.py            # Safe Python code execution
├── scaffold.py           # Project scaffolding templates
├── search.py             # Directory tree, grep, stats
├── security.py           # Security scanner
├── self_heal.py          # Auto-fix broken code
├── skills.py             # Skill learning system
├── snippets.py           # Code snippet manager
├── tasks.py              # Task runner integration
├── timetrack.py          # Time tracking
├── ui.py                 # Terminal colors, syntax highlighting
├── voice.py              # Voice recording and transcription
├── watch.py              # File watcher
└── web_research.py       # Web search and scraping

tests/
├── test_bookmarks.py
├── test_checkpoints.py
├── test_edit_parser.py
├── test_explain.py
├── test_indexer.py
├── test_memory.py
├── test_sandbox.py
├── test_scaffold.py
├── test_search.py
├── test_security.py
├── test_self_heal.py
├── test_skills.py
└── test_snippets.py
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Tab` | Autocomplete slash commands and file paths |
| `Ctrl+X` | Exit CLI |
| `Ctrl+L` | Clear terminal screen |
| `Shift+Enter` | New line in multiline mode |
| `↑/↓` | Browse command history |

## License

MIT
