# Changelog

All notable changes to Troya CLI (formerly Cascade CLI).

## [3.7.2] - 2026-06-08

### Added
- 8 new test files covering security, explain, bookmarks, snippets, memory, skills, edit_parser, checkpoints
- `/voice` and `/browser` command handlers with dependency checking
- `/embed` and `/mcp` command handlers
- GitHub repository published at https://github.com/afares8/troya
- `troya` entry point in setup.py alongside `cascade`
- CHANGELOG.md

### Fixed
- `/scan` regex crash on Python 3.10+ (removed inline `(?i)` flags)
- `/fzf` crash on Python <3.12 (replaced `Path.walk()` with `os.walk()`)
- `/lint` crash when formatter returns no result (`KeyError: 'formatted'`)
- Bookmarks not persisting between commands (relative vs absolute paths)
- `/explain function` argument parsing
- `lang_message` typo in snippets.py causing `NameError`
- `/recipe` crashing in non-interactive mode with `EOFError`
- `/export` using wrong session ID when called without arguments

### Changed
- README completely rewritten with Troya branding and full command reference
- Version bumped to 3.7.2

## [3.7.0] - 2026-06-08

### Added
- Autonomous agent mode (`/agent`) with plan-execute-heal loop
- Persistent checkpoint system (`/checkpoint`, `/checkpoints`)
- Web research module (`/research`)
- GitHub integration (`/github`)
- Advanced edit parser for LLM responses
- Skill learning system (`/skills`)
- Security scanner (`/scan`)
- Auto-formatter (`/fmt`) and linter (`/lint`)
- Fuzzy file finder (`/fzf`)
- Clipboard integration (`/copy`)
- Time tracking (`/time`)
- Recipe system (`/recipe`, `/recipes`)
- Bookmark manager (`/bookmark`, `/bookmarks`, `/jump`)
- Git diff analyzer (`/review`)
- Dependency graph (`/deps`)
- Persistent memory store (`/memory`)
- Code explanation engine (`/explain`)
- Snippet manager (`/snippet`, `/snippets`)
- File diff comparison (`/diff`)
- Task runner integration (`/tasks`, `/run-task`)
- Benchmark suite (`/benchmark`)

## [3.6.0] - Earlier

### Added
- Offline mode support
- Code quality analyzer (`/quality`)
- Self-healing module (`/heal`)
- Fine-tuning dataset generation (`/finetune`)
- RAG search (`/rag`)

## [3.0.0] - Original

### Added
- Multi-provider LLM support (OpenAI, Anthropic, Ollama, Groq)
- Rich terminal UI with prompt_toolkit
- Agentic reasoning mode
- Semantic code search with TF-IDF
- File watcher
- Project scaffolding
- Plugin system
- Web dashboard
- Session persistence
- Git integration
- Safe command execution
