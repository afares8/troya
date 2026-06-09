"""Main entry point for Cascade CLI v2.0."""

import argparse
import os
import sys
from pathlib import Path
from typing import Any

from .agentic import run_agentic
from .agents.db import init_db as init_agents_db, list_agents, list_tasks
from .autonomous import AutonomousAgent
from .agents.orchestrator import Orchestrator
from .benchmark import benchmark_func, compare_benchmarks, format_single as format_benchmark
from .browser import check_playwright, run_browser_test
from .clipboard import copy_to_clipboard
from .completions import install_completions
from .config import ensure_config, list_profiles, load_config, save_config, switch_profile
from .context import ContextManager
from .dashboard import start_dashboard
from .deps_graph import build_graph, format_graph
from .diff import diff_files, format_diff
from .editor import handle_edits_from_response
from .embeddings import EmbeddingIndex
from .explain import explain_class, explain_file, explain_function
from .executor import CommandExecutor
from .fine_tune import FineTuner
from .formatter import format_file, format_result as format_fmt_result, lint_python_file
from .fuzzy import fuzzy_find, format_results as format_fuzzy_results
from .sandbox import format_result as format_sandbox_result, run_sandboxed
from .security import format_report as format_security_report, scan_project
from .self_heal import heal_code, heal_file
from .timetrack import TimeTracker
from .git_review import review_commit
from .git_utils import commit_changes, get_diff, get_log, is_git_repo, print_repo_status
from .indexer import CodeIndex
from .memory import MemoryStore
from .inline_complete import get_inline_suggestion, render_suggestion
from .llm import LLMClient
from .mcp_client import load_mcp_servers
from .persistence import (
    export_to_markdown,
    generate_session_id,
    load_session,
    print_sessions_list,
    save_session,
)
from .bookmarks import BookmarkManager
from .checkpoints import CheckpointManager
from .edit_parser import EditParser
from .github_client import (
    create_branch,
    create_issue,
    create_pr,
    format_pr_list,
    get_repo_info,
    is_gh_available,
    list_prs,
)
from .planner import create_plan, format_plan
from .plugins import load_plugins, list_plugins, run_plugin
from .project_detector import auto_context_files, detect_project, get_project_hint
from .recipes import RecipeRunner, get_recipe, list_recipes
from .scaffold import list_templates, scaffold_from_ai, scaffold_project
from .snippets import SnippetManager
from .quality import analyze_project, format_report
from .self_improve import analyze_self, apply_self_improvements, build_self_context
from .skills import SkillManager
from .tasks import detect_task_runners, format_result as format_task_result, format_runners, run_task
from .web_research import research_topic
from .ui import (
    Colors,
    confirm,
    print_error,
    print_header,
    print_info,
    print_success,
    print_warning,
    render_markdown,
)
from .voice import check_ffmpeg, voice_chat
from .watch import watch_project, suggest_on_change

# prompt_toolkit imports
try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
    from prompt_toolkit.completion import Completer, Completion
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.lexers import PygmentsLexer
    from prompt_toolkit.styles import Style
    PROMPT_TOOLKIT_AVAILABLE = True
except ImportError:
    PROMPT_TOOLKIT_AVAILABLE = False

COMMANDS = {
    "/help": "Show help message",
    "/read": "Read a file into context",
    "/run": "Run a shell command (with confirmation)",
    "/ls": "List directory contents",
    "/cd": "Change working directory",
    "/tree": "Show directory tree",
    "/grep": "Search pattern in project files",
    "/stats": "Show project statistics",
    "/git": "Show git status",
    "/git-log": "Show recent git log",
    "/git-diff": "Show git diff",
    "/commit": "Stage all and commit",
    "/agentic": "Toggle autonomous agentic mode",
    "/plan": "Create a multi-step plan for a task",
    "/watch": "Watch files and suggest actions on changes",
    "/index": "Build code index for intelligent search",
    "/search": "Semantic code search using index",
    "/improve": "Analyze and improve Cascade's own code",
    "/scaffold": "Generate project from template",
    "/templates": "List available project templates",
    "/plugins": "List loaded plugin commands",
    "/detect": "Detect project type and auto-load context",
    "/voice": "Record voice, transcribe, and chat",
    "/browser": "Open URL with Playwright and extract content",
    "/embed": "Build real semantic embeddings index",
    "/mcp": "List MCP connected tool servers",
    "/completions": "Install shell completions (bash/zsh)",
    "/dashboard": "Launch web dashboard in browser",
    "/agents": "Run multi-agent task delegation",
    "/run": "Run Python code in sandboxed environment",
    "/heal": "Auto-detect and fix broken code",
    "/rag": "Search with real semantic embeddings",
    "/finetune": "Prepare dataset for local model fine-tuning",
    "/quality": "Analyze code quality of the project",
    "/scan": "Security scan for secrets and vulnerabilities",
    "/fmt": "Auto-format current file or project",
    "/lint": "Lint current file with ruff/flake8",
    "/fzf": "Fuzzy find files",
    "/copy": "Copy file content to clipboard",
    "/time": "Show time tracking stats",
    "/recipe": "Run a workflow recipe (setup-python, setup-node, deploy-static)",
    "/recipes": "List available recipes",
    "/bookmark": "Save a bookmark for quick access",
    "/bookmarks": "List saved bookmarks",
    "/jump": "Jump to a bookmark",
    "/review": "Review git diff for issues",
    "/deps": "Show dependency graph of project",
    "/memory": "Show learned memory/knowledge base",
    "/explain": "Explain function or file structure",
    "/snippet": "Save a code snippet",
    "/snippets": "List saved code snippets",
    "/diff": "Compare two files",
    "/tasks": "List available task runners (make, npm, etc.)",
    "/run-task": "Run a task (make build, npm test, etc.)",
    "/benchmark": "Benchmark a Python function",
    "/agent": "Run autonomous agent on a task",
    "/research": "Research topic on the web",
    "/github": "GitHub integration (prs, issues, branch)",
    "/skills": "Show learned skills",
    "/checkpoint": "Show checkpoint status",
    "/checkpoints": "List all checkpoints",
    "/clear": "Clear conversation and file context",
    "/context": "Show current context info",
    "/history": "Show command history",
    "/save": "Save conversation to session",
    "/load": "Load a previous session",
    "/sessions": "List saved sessions",
    "/export": "Export conversation to markdown",
    "/profile": "Switch configuration profile",
    "/profiles": "List available profiles",
    "/exit": "Exit Cascade CLI",
    "/quit": "Exit Cascade CLI",
}


def setup_wizard() -> None:
    """Interactive configuration setup."""
    print_header("Cascade CLI Setup")

    config = load_config()

    print("Choose your LLM provider:")
    providers = ["openai", "anthropic", "ollama", "groq", "custom"]
    for i, p in enumerate(providers, 1):
        print(f"  {i}. {p}")

    choice = input("\nSelect (1-5) [1]: ").strip() or "1"
    try:
        config["provider"] = providers[int(choice) - 1]
    except (ValueError, IndexError):
        config["provider"] = "openai"

    if config["provider"] == "ollama":
        config["model"] = input("Model name [llama3.1]: ").strip() or "llama3.1"
        config["api_base"] = input("Ollama URL [http://localhost:11434/v1]: ").strip() or "http://localhost:11434/v1"
        config["api_key"] = "ollama"
    elif config["provider"] == "anthropic":
        config["model"] = input("Model [claude-3-5-sonnet-20241022]: ").strip() or "claude-3-5-sonnet-20241022"
        config["api_key"] = input("Anthropic API key: ").strip()
    elif config["provider"] == "groq":
        config["model"] = input("Model [llama-3.1-70b-versatile]: ").strip() or "llama-3.1-70b-versatile"
        config["api_key"] = input("Groq API key: ").strip()
    elif config["provider"] == "custom":
        config["api_base"] = input("API base URL: ").strip()
        config["model"] = input("Model name: ").strip()
        config["api_key"] = input("API key (if required): ").strip()
    else:
        config["model"] = input("Model [gpt-4o]: ").strip() or "gpt-4o"
        config["api_key"] = input("OpenAI API key: ").strip()

    config["max_tokens"] = int(input("Max tokens [4096]: ").strip() or "4096")
    config["temperature"] = float(input("Temperature [0.7]: ").strip() or "0.7")

    save_config(config)
    print_success("Configuration saved!")
    print_info(f"Config file: {Path.home() / '.config' / 'cascade-cli' / 'config.json'}")


def print_help() -> None:
    """Print help message."""
    print(f"""
{Colors.CYAN}{Colors.BOLD}Cascade CLI v2.5 Commands:{Colors.RESET}

  {Colors.YELLOW}File & Directory:{Colors.RESET}
  /read <file>       Read a file into context
  /ls [path]         List directory contents
  /cd <path>         Change working directory
  /tree [path]       Show directory tree
  /stats             Show project statistics

  {Colors.YELLOW}Search & Edit:{Colors.RESET}
  /grep <pattern>    Search pattern in project files
  /search <query>    Semantic code search (requires /index)
  /run <command>     Execute shell command (with confirmation)

  {Colors.YELLOW}Git:{Colors.RESET}
  /git               Show git status
  /git-log [n]       Show recent commits
  /git-diff          Show working tree diff
  /commit <msg>      Stage all and commit

  {Colors.YELLOW}Agentic & AI:{Colors.RESET}
  /agentic           Toggle autonomous mode (AI uses tools automatically)
  /plan <task>       Create a multi-step plan for a task
  /watch             Watch files and suggest actions on changes
  /index             Build code index for intelligent search

  {Colors.YELLOW}Advanced:{Colors.RESET}
  /improve <query>   Analyze Cascade's own code and propose fixes
  /scaffold <tmpl>   Generate project from template (react, fastapi, flask, python-cli)
  /templates         List available scaffold templates
  /detect            Auto-detect project type and load context
  /plugins           List loaded plugin commands

  {Colors.YELLOW}Session:{Colors.RESET}
  /save              Save conversation to session
  /load <id>         Load a previous session
  /sessions          List saved sessions
  /export [path]     Export conversation to markdown

  {Colors.YELLOW}Config:{Colors.RESET}
  /profile <name>    Switch configuration profile
  /profiles          List available profiles
  /setup             Run setup wizard

  {Colors.YELLOW}General:{Colors.RESET}
  /context           Show current context info
  /history           Show executed command history
  /clear             Clear conversation and file context
  /help              Show this message
  /exit              Exit Cascade CLI

{Colors.DIM}Tip: Shift+Enter=multiline, Tab=complete, !=agentic, Ctrl+X=exit{Colors.RESET}
""")


class SlashCommandCompleter(Completer):
    """Custom completer for slash commands and file paths."""

    def __init__(self, cwd: Path):
        self.cwd = cwd

    def get_completions(self, document, complete_event):
        text = document.text
        if text.startswith("/"):
            for cmd, desc in COMMANDS.items():
                if cmd.startswith(text):
                    yield Completion(cmd, start_position=-len(text), display=f"{cmd}  {desc}")

        # File path completion for /read, /cd
        if text.startswith(("/read ", "/cd ", "/tree ")):
            prefix = text.split(" ", 1)[1] if " " in text else ""
            dir_part = self.cwd
            file_part = prefix

            if "/" in prefix:
                dir_part = (self.cwd / prefix).parent
                file_part = prefix.split("/")[-1]

            try:
                for entry in sorted(dir_part.iterdir(), key=lambda e: e.name.lower()):
                    name = entry.name
                    if name.startswith(file_part) or not file_part:
                        display = f"{name}/" if entry.is_dir() else name
                        yield Completion(
                            str(entry.relative_to(self.cwd)) if entry.is_relative_to(self.cwd) else str(entry),
                            start_position=-len(prefix),
                            display=display,
                        )
            except (PermissionError, OSError):
                pass


def build_prompt_session(cwd: Path) -> Any:
    """Build a prompt_toolkit session with autocomplete and history."""
    if not PROMPT_TOOLKIT_AVAILABLE:
        return None

    history_path = Path.home() / ".config" / "cascade-cli" / "history"
    history_path.parent.mkdir(parents=True, exist_ok=True)

    kb = KeyBindings()

    @kb.add("c-x")
    def _(event):
        """Ctrl+X to exit."""
        event.app.exit(result="/exit")

    @kb.add("c-l")
    def _(event):
        """Ctrl+L to clear screen."""
        import shutil
        print("\033[2J\033[H", end="")

    style = Style.from_dict({
        "prompt": "bold cyan",
        "": "",
    })

    session = PromptSession(
        history=FileHistory(str(history_path)),
        auto_suggest=AutoSuggestFromHistory(),
        completer=SlashCommandCompleter(cwd),
        complete_while_typing=True,
        multiline=False,
        key_bindings=kb,
        style=style,
    )
    return session


def get_user_input(session: Any, cwd: Path) -> str:
    """Get user input, using prompt_toolkit if available."""
    if session:
        try:
            return session.prompt(
                [("class:prompt", "You: ")],
                wrap_lines=True,
                enable_suspend=True,
            ).strip()
        except (EOFError, KeyboardInterrupt):
            return "/exit"
    else:
        try:
            return input(f"{Colors.GREEN}{Colors.BOLD}You:{Colors.RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            return "/exit"


class OfflineLLMClient:
    """Stub LLM client for offline mode — returns helpful messages instead of AI responses."""

    def __init__(self, config: dict):
        self.config = config
        self.offline = True

    def count_tokens(self, messages: list) -> int:
        return sum(len(m.get("content", "")) // 4 for m in messages)

    def chat(self, messages: list) -> str:
        return (
            "🔌 Offline mode — LLM not available.\n\n"
            "Commands that work without LLM:\n"
            "  /run, /templates, /detect, /tree, /stats, /grep\n"
            "  /dashboard, /help, /clear, /save, /load\n\n"
            "To chat with AI, configure an LLM provider:\n"
            "  cascade --setup\n"
            "  Or set env vars: OPENAI_API_KEY, etc."
        )

    def close(self) -> None:
        pass


def repl(config: dict) -> None:
    """Run the interactive REPL loop. Works offline for local commands."""
    offline_mode = False
    client = None

    if not config.get("api_key"):
        print_warning("No API key configured. Running in OFFLINE mode.")
        print_info("Local commands work: /run, /templates, /detect, /tree, /stats, /dashboard")
        print_info("Configure LLM: cascade --setup or set OPENAI_API_KEY")
        print()
        client = OfflineLLMClient(config)
        offline_mode = True
    else:
        try:
            client = LLMClient(config)
        except (ValueError, Exception) as e:
            print_warning(f"LLM connection failed: {e}")
            print_info("Falling back to OFFLINE mode.")
            client = OfflineLLMClient(config)
            offline_mode = True

    context = ContextManager(
        system_prompt=config.get("system_prompt", ""),
        max_files=config.get("max_context_files", 20),
    )
    executor = CommandExecutor(auto_confirm=config.get("auto_confirm", False))
    session_id = generate_session_id()

    # Load plugins
    plugin_count = load_plugins()

    # Auto-detect project type and load context
    ptype, _ = detect_project(context.cwd)
    auto_hint = get_project_hint(context.cwd)
    auto_files = auto_context_files(context.cwd, max_files=3)
    for path in auto_files:
        context.read_file(path)

    # Build prompt session
    pt_session = build_prompt_session(context.cwd) if PROMPT_TOOLKIT_AVAILABLE else None

    print_header("🚀 Cascade CLI v3.0")
    if offline_mode:
        print_warning("⚡ OFFLINE MODE — Local commands only")
    print_info(f"Provider: {config.get('provider', 'offline' if offline_mode else 'unknown')}")
    print_info(f"Model: {config.get('model', 'n/a')}")
    print_info(f"Profile: {config.get('profile', 'default')}")
    print_info(f"Directory: {Path.cwd()}")
    if auto_hint:
        print_info(f"Project: {auto_hint}")
    if plugin_count:
        print_info(f"Plugins: {plugin_count} loaded")
    if PROMPT_TOOLKIT_AVAILABLE:
        print_info("Rich terminal: enabled (Tab=complete, Shift+Enter=multiline, Ctrl+X=exit)")
    else:
        print_warning("prompt_toolkit not installed. Install for autocomplete and multiline.")
    print()
    print("Type /help for commands, or just start chatting.")
    print()

    while True:
        user_input = get_user_input(pt_session, context.cwd)

        if not user_input:
            continue

        # Handle multiline paste / explicit newline requests
        if user_input.startswith("\"\"\"") or user_input.startswith("'''"):
            # Multiline mode trigger
            delimiter = user_input[:3]
            lines = [user_input[3:]]
            print_info("Multiline mode (end with same delimiter)")
            while True:
                line = get_user_input(pt_session, context.cwd)
                if line.strip() == delimiter:
                    break
                lines.append(line)
            user_input = "\n".join(lines)

        # Handle slash commands
        if user_input.startswith("/"):
            parts = user_input[1:].split(maxsplit=1)
            cmd = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else ""

            if cmd in ("exit", "quit", "q"):
                # Save session before exit
                save_session(session_id, context.messages, context.files, {"config": config})
                print_info(f"Session saved: {session_id}")
                print_info("Goodbye!")
                break

            elif cmd == "help" or cmd == "h":
                print_help()

            elif cmd == "read" or cmd == "r":
                if not arg:
                    print_error("Usage: /read <file>")
                    continue
                context.read_file(arg)

            elif cmd == "run" or cmd == "exec":
                if not arg:
                    print_error("Usage: /run <command>")
                    continue
                executor.execute(arg, cwd=context.cwd)

            elif cmd == "ls" or cmd == "dir":
                listing = context.list_directory(arg or ".")
                print(listing)

            elif cmd == "cd":
                if not arg:
                    print_error("Usage: /cd <path>")
                    continue
                if context.change_directory(arg):
                    # Update completer cwd
                    if pt_session and hasattr(pt_session, 'completer'):
                        pt_session.completer.cwd = context.cwd

            elif cmd == "tree":
                tree_path = arg or "."
                depth = 3
                if " " in tree_path:
                    tree_path, depth_str = tree_path.rsplit(" ", 1)
                    try:
                        depth = int(depth_str)
                    except ValueError:
                        pass
                context.show_tree(tree_path, max_depth=depth)

            elif cmd == "grep":
                if not arg:
                    print_error("Usage: /grep <pattern> [file-pattern]")
                    continue
                pat_parts = arg.split(" ", 1)
                pattern = pat_parts[0]
                file_pat = pat_parts[1] if len(pat_parts) > 1 else "*"
                context.grep(pattern, file_pat)

            elif cmd == "stats":
                context.show_stats()

            elif cmd == "git":
                print_repo_status(context.cwd)

            elif cmd == "git-log":
                n = int(arg) if arg and arg.isdigit() else 5
                log = get_log(n, context.cwd)
                print(log)

            elif cmd == "git-diff":
                diff = get_diff(context.cwd, staged=False)
                print(diff or "No changes.")

            elif cmd == "commit":
                if not arg:
                    print_error("Usage: /commit <message>")
                    continue
                commit_changes(arg, context.cwd)

            elif cmd == "clear" or cmd == "cls":
                context.clear()

            elif cmd == "context" or cmd == "ctx":
                context.show_context()

            elif cmd == "history" or cmd == "hist":
                if executor.history:
                    print(f"{Colors.CYAN}Command history:{Colors.RESET}")
                    for i, h in enumerate(executor.history[-10:], 1):
                        status = "✓" if h["success"] else "✗"
                        print(f"  {status} {h['command']}")
                else:
                    print_info("No commands executed yet.")

            elif cmd == "save":
                save_session(session_id, context.messages, context.files, {"config": config})
                print_success(f"Session saved: {session_id}")

            elif cmd == "load":
                if not arg:
                    print_error("Usage: /load <session-id>")
                    continue
                loaded = load_session(arg)
                if loaded:
                    context.messages = loaded.get("messages", [])
                    context.files = loaded.get("files", {})
                    print_success(f"Loaded session {arg} ({len(context.messages)} messages)")
                else:
                    print_error(f"Session not found: {arg}")

            elif cmd == "sessions":
                print_sessions_list()

            elif cmd == "export":
                out_path = Path(arg) if arg else None
                export_to_markdown(session_id, out_path)

            elif cmd == "profile":
                if not arg:
                    print_error("Usage: /profile <name>")
                    continue
                if switch_profile(config, arg):
                    print_success(f"Switched to profile: {arg}")
                    # Reload config to get new settings
                    config = load_config()
                    print_info(f"Now using: {config.get('provider')} / {config.get('model')}")
                else:
                    profiles = list_profiles(config)
                    print_error(f"Unknown profile '{arg}'. Available: {', '.join(profiles.keys())}")

            elif cmd == "profiles":
                profiles = list_profiles(config)
                current = config.get("profile", "default")
                print(f"{Colors.CYAN}Available profiles:{Colors.RESET}")
                for name, p in profiles.items():
                    marker = f" {Colors.GREEN}<- current{Colors.RESET}" if name == current else ""
                    print(f"  {Colors.YELLOW}{name}{Colors.RESET}: {p.get('provider', '?')} / {p.get('model', '?')}{marker}")

            elif cmd == "setup":
                setup_wizard()

            elif cmd == "agentic":
                agentic_mode = not getattr(repl, "agentic_mode", False)
                repl.agentic_mode = agentic_mode
                if agentic_mode:
                    print_success("Agentic mode ON — AI will autonomously use tools")
                else:
                    print_info("Agentic mode OFF")

            elif cmd == "plan":
                if not arg:
                    print_error("Usage: /plan <task description>")
                    continue
                plan = create_plan(client, arg)
                print(format_plan(plan))

            elif cmd == "watch":
                if not arg:
                    print_info("Watching for file changes... (Ctrl+C to stop)")
                    watch_project(context.cwd, lambda changes: suggest_on_change(client, context, changes))
                else:
                    print_error("Usage: /watch")

            elif cmd == "index":
                if not getattr(repl, "code_index", None):
                    repl.code_index = CodeIndex(context.cwd)
                repl.code_index.build()
                print_success("Code index built")

            elif cmd == "search":
                if not arg:
                    print_error("Usage: /search <query>")
                    continue
                idx = getattr(repl, "code_index", None)
                if not idx or not idx.loaded:
                    print_warning("No index. Run /index first.")
                    continue
                results = idx.search(arg, top_k=5)
                if not results:
                    print_info("No relevant files found.")
                    continue
                print(f"{Colors.CYAN}Top matches for '{arg}':{Colors.RESET}")
                for path, score in results:
                    print(f"  {Colors.YELLOW}{path}{Colors.RESET} ({score:.2f})")
                    snippet = idx.get_snippet(path, arg)
                    if snippet:
                        print(f"    {Colors.DIM}{snippet[:200].replace(chr(10), ' ')}{Colors.RESET}")

            elif cmd == "improve":
                if not arg:
                    print_error("Usage: /improve <what to improve>")
                    continue
                result = analyze_self(client, arg)
                print(f"\n{Colors.MAGENTA}{Colors.BOLD}Self-Analysis:{Colors.RESET}\n{result}\n")
                if confirm("Apply any suggested file edits?", default=False):
                    package_dir = Path(__file__).parent
                    applied = apply_self_improvements(result, package_dir)
                    if applied:
                        print_success(f"Applied {applied} self-improvement(s)")
                    else:
                        print_info("No applicable edits found")

            elif cmd == "scaffold":
                if not arg:
                    print_error("Usage: /scaffold <template> [name]")
                    print_info("Templates: " + ", ".join(list_templates()))
                    continue
                parts = arg.split(" ", 1)
                template = parts[0]
                name = parts[1] if len(parts) > 1 else "my_project"
                scaffold_project(template, name, context.cwd)

            elif cmd == "templates":
                print(f"{Colors.CYAN}Available templates:{Colors.RESET}")
                for t in list_templates():
                    print(f"  {Colors.YELLOW}{t}{Colors.RESET}")

            elif cmd == "plugins":
                plugins = list_plugins()
                if plugins:
                    print(f"{Colors.CYAN}Loaded plugins:{Colors.RESET}")
                    for cmd_name, desc in plugins:
                        print(f"  {Colors.YELLOW}/{cmd_name}{Colors.RESET}  {desc}")
                else:
                    print_info("No plugins loaded. Drop .py files in ~/.config/cascade-cli/plugins/")

            elif cmd == "detect":
                ptype, meta = detect_project(context.cwd)
                hint = get_project_hint(context.cwd)
                print_success(f"Detected: {ptype}")
                if hint:
                    print_info(hint)
                auto_files = auto_context_files(context.cwd, max_files=5)
                if auto_files:
                    print_info(f"Auto-loaded {len(auto_files)} context file(s):")
                    for path in auto_files:
                        context.read_file(path)

            elif cmd == "voice":
                if not check_ffmpeg():
                    print_error("ffmpeg not found. Install it to use voice features.")
                    continue
                print_header("🎤 Voice Mode")
                print_info("Voice recording requires interactive mode.")

            elif cmd == "browser":
                if not arg:
                    print_error("Usage: /browser <url>")
                    print_info("Example: /browser https://example.com")
                    continue
                if not check_playwright():
                    print_error("Playwright not installed. Run: pip install playwright")
                    continue
                print_header("🌐 Browser Mode")
                try:
                    content = run_browser_test(arg)
                    if content:
                        print(content[:2000])
                    else:
                        print_error("No content extracted")
                except Exception as e:
                    print_error(f"Browser error: {e}")

            elif cmd == "embed":
                print_header("🔍 Semantic Embeddings")
                print_info("Building embeddings index...")
                try:
                    index = EmbeddingIndex(context.cwd)
                    index.build()
                    print_success("Embeddings index built")
                except Exception as e:
                    print_error(f"Failed to build embeddings: {e}")

            elif cmd == "mcp":
                print_header("🔌 MCP Servers")
                try:
                    servers = load_mcp_servers(config)
                    if servers:
                        print(f"{Colors.CYAN}Connected MCP servers:{Colors.RESET}")
                        for client in servers:
                            print(f"  {Colors.YELLOW}{client.cmd}{Colors.RESET}")
                    else:
                        print_info("No MCP servers configured")
                except Exception as e:
                    print_error(f"Failed to load MCP servers: {e}")

            elif cmd == "dashboard":
                start_dashboard()

            elif cmd == "agents":
                if not arg:
                    print_error("Usage: /agents <task description>")
                    continue
                print_header("🤖 Multi-Agent Mode")
                orch = getattr(repl, "orchestrator", None)
                if not orch:
                    init_agents_db()
                    orch = Orchestrator(config)
                    orch.create_agent("alice", "coder")
                    orch.create_agent("bob", "researcher")
                    orch.create_agent("carol", "reviewer")
                    repl.orchestrator = orch
                import asyncio
                result = asyncio.run(orch.delegate(arg, arg))
                print_success(f"Completed by {result.get('agent', 'unknown')}")
                print(result.get("result", "")[:500])

            elif cmd == "run":
                if not arg:
                    print_error("Usage: /run <python code> or /run to enter multiline mode")
                    continue
                code = arg.replace("\\n", "\n")
                print_info("Running in sandbox...")
                result = run_sandboxed(code)
                print(format_sandbox_result(result))

            elif cmd == "heal":
                if not arg:
                    print_error("Usage: /heal <filepath> or /heal <python code>")
                    continue
                target = Path(arg)
                if target.exists() and target.is_file():
                    result = heal_file(target, client)
                else:
                    result = heal_code(arg, client)
                if result["fixed"]:
                    print_success("Code fixed!")
                    if result.get("fixed_code"):
                        print(f"{Colors.CYAN}Fixed code:{Colors.RESET}")
                        print(result["fixed_code"][:1000])
                else:
                    print_error("Could not auto-fix. Check error below.")
                    if result.get("error"):
                        print(result["error"])

            elif cmd == "rag":
                if not arg:
                    print_error("Usage: /rag <query>")
                    continue
                idx = EmbeddingIndex(context.cwd)
                if not idx.loaded:
                    print_info("No embeddings found. Building index first...")
                    idx.build(max_files=100)
                results = idx.search(arg, top_k=5)
                if results:
                    print(f"{Colors.CYAN}Semantic search results:{Colors.RESET}")
                    for path, score in results:
                        print(f"  {Colors.YELLOW}{path}{Colors.RESET} (score: {score:.3f})")
                else:
                    print_info("No results found. Try building index with /embed first.")

            elif cmd == "finetune":
                print_header("🧠 Fine-Tuning Preparation")
                ft = FineTuner(model_name="unsloth/llama-3-8b")
                dataset_path = Path(arg) if arg else context.cwd
                ft.prepare_from_project(dataset_path)
                print_success(f"Dataset prepared at {ft.output_dir}")
                print_info("To train: install unsloth and run the generated training script")

            elif cmd == "quality":
                print_header("🔍 Code Quality Analysis")
                report = analyze_project(context.cwd)
                print(format_report(report))

            elif cmd == "scan":
                print_header("🔒 Security Scan")
                report = scan_project(context.cwd)
                print(format_security_report(report))

            elif cmd == "fmt":
                target = Path(arg) if arg else context.cwd
                if target.is_file():
                    result = format_file(target)
                    print(format_fmt_result(result))
                else:
                    print_info("Formatting all Python files...")
                    for pyfile in target.rglob("*.py"):
                        if "__pycache__" not in str(pyfile):
                            result = format_file(pyfile)
                            if result["formatted"]:
                                print(f"  {Colors.GREEN}✓{Colors.RESET} {pyfile.name}")

            elif cmd == "lint":
                target = Path(arg) if arg else context.cwd
                if target.is_file():
                    result = lint_python_file(target)
                    print(format_fmt_result(result))
                else:
                    print_error("Usage: /lint <file>")

            elif cmd == "fzf":
                query = arg if arg else ""
                results = fuzzy_find(query, context.cwd)
                print(format_fuzzy_results(results, context.cwd))

            elif cmd == "copy":
                target = Path(arg) if arg else None
                if target and target.is_file():
                    content = target.read_text()
                    if copy_to_clipboard(content):
                        print_success(f"Copied {len(content)} chars to clipboard")
                    else:
                        print_error("Could not copy to clipboard")
                else:
                    print_error("Usage: /copy <file>")

            elif cmd == "time":
                tracker = getattr(repl, "tracker", None)
                if not tracker:
                    tracker = TimeTracker()
                    tracker.start_session(context.cwd)
                    repl.tracker = tracker
                stats = tracker.get_stats(context.cwd)
                print(tracker.format_stats(stats))

            elif cmd == "recipes":
                print(f"{Colors.CYAN}Available recipes:{Colors.RESET}")
                for name, desc in list_recipes():
                    print(f"  {Colors.YELLOW}{name}{Colors.RESET}  {desc}")

            elif cmd == "recipe":
                if not arg:
                    print_error("Usage: /recipe <name>")
                    print_info("Available: setup-python, setup-node, deploy-static, release-python")
                    continue
                recipe = get_recipe(arg)
                if not recipe:
                    print_error(f"Recipe '{arg}' not found")
                    continue
                runner = RecipeRunner(context.cwd)
                result = runner.run(recipe)
                if result["success"]:
                    print_success(f"Recipe completed: {result['steps_run']} steps")
                else:
                    print_error("Recipe failed. Check output above.")

            elif cmd == "bookmark":
                if not arg:
                    print_error("Usage: /bookmark <name> [file] [line]")
                    continue
                parts = arg.split()
                name = parts[0]
                filepath = Path(parts[1]) if len(parts) > 1 else None
                line = int(parts[2]) if len(parts) > 2 else 0
                bm = BookmarkManager()
                if filepath and filepath.exists():
                    bm.add(name, filepath.resolve(), line)
                else:
                    # Bookmark current context file
                    current_file = None
                    for f in context.files:
                        current_file = Path(f)
                        break
                    if current_file:
                        bm.add(name, current_file.resolve(), line)
                    else:
                        print_error("No file specified or in context")

            elif cmd == "bookmarks":
                bm = BookmarkManager()
                print(bm.format_list(context.cwd))

            elif cmd == "jump":
                if not arg:
                    print_error("Usage: /jump <bookmark_name>")
                    continue
                bm = BookmarkManager()
                location = bm.jump(arg)
                if location:
                    filepath = Path(location["file"])
                    if filepath.exists():
                        context.read_file(filepath)
                        print_success(f"Jumped to {filepath}:{location['line']}")
                    else:
                        print_error(f"File not found: {filepath}")
                else:
                    print_error(f"Bookmark '{arg}' not found")

            elif cmd == "review":
                print_header("🔍 Git Diff Review")
                commit = arg if arg else None
                print(review_commit(commit))

            elif cmd == "deps":
                print_header("🔗 Dependency Graph")
                graph = build_graph(context.cwd)
                print(format_graph(graph, context.cwd))

            elif cmd == "memory":
                store = MemoryStore()
                print(store.format_memory())

            elif cmd == "explain":
                if not arg:
                    print_error("Usage: /explain <function_name> or /explain file <filename>")
                    continue
                parts = arg.split()
                if parts[0] == "file" and len(parts) > 1:
                    target = Path(parts[1])
                    if target.exists():
                        print(explain_file(target))
                    else:
                        print_error(f"File not found: {target}")
                elif parts[0] in ("function", "class") and len(parts) >= 3:
                    # /explain function <name> <file>
                    name = parts[1]
                    target = Path(parts[2])
                    if target.exists():
                        if parts[0] == "function":
                            print(explain_function(target, name))
                        else:
                            print(explain_class(target, name))
                    else:
                        print_error(f"File not found: {target}")
                elif len(parts) >= 2:
                    # /explain <file> <function_or_class>
                    target = Path(parts[0])
                    name = parts[1]
                    if target.exists():
                        print(explain_function(target, name))
                    else:
                        print_error(f"File not found: {target}")
                else:
                    # Try to explain function in current context
                    current_file = None
                    for f in context.files:
                        current_file = Path(f)
                        break
                    if current_file and current_file.exists():
                        print(explain_function(current_file, arg))
                    else:
                        print_error("No file in context. Usage: /explain <file> <function>")

            elif cmd == "snippet":
                if not arg:
                    print_error("Usage: /snippet <name> <language>")
                    continue
                parts = arg.split(maxsplit=2)
                name = parts[0]
                lang = parts[1] if len(parts) > 1 else "python"
                code = parts[2] if len(parts) > 2 else ""
                if not code:
                    print_info("Enter code (Ctrl+D or EOF to finish):")
                    lines = []
                    try:
                        while True:
                            line = input()
                            lines.append(line)
                    except EOFError:
                        pass
                    code = "\n".join(lines)
                sm = SnippetManager()
                sm.add(name, code, lang)

            elif cmd == "snippets":
                sm = SnippetManager()
                query = arg if arg else ""
                if query:
                    results = sm.search(query)
                    if results:
                        for name, snippet in results:
                            print(sm.format_snippet(name))
                    else:
                        print_info("No matching snippets")
                else:
                    print(sm.format_list())

            elif cmd == "diff":
                if not arg:
                    print_error("Usage: /diff <file_a> <file_b>")
                    continue
                parts = arg.split()
                if len(parts) < 2:
                    print_error("Usage: /diff <file_a> <file_b>")
                    continue
                file_a = Path(parts[0])
                file_b = Path(parts[1])
                if file_a.exists() and file_b.exists():
                    diff = diff_files(file_a, file_b)
                    print(format_diff(diff))
                else:
                    print_error("One or both files not found")

            elif cmd == "tasks":
                runners = detect_task_runners(context.cwd)
                print(format_runners(runners))

            elif cmd == "run-task":
                if not arg:
                    print_error("Usage: /run-task <runner> <task>")
                    print_info("Example: /run-task make build")
                    continue
                parts = arg.split(maxsplit=1)
                if len(parts) < 2:
                    print_error("Usage: /run-task <runner> <task>")
                    continue
                runner = parts[0]
                task = parts[1]
                result = run_task(runner, task, context.cwd)
                print(format_task_result(result))

            elif cmd == "benchmark":
                if not arg:
                    print_error("Usage: /benchmark <python_file> <function_name>")
                    continue
                parts = arg.split()
                if len(parts) < 2:
                    print_error("Usage: /benchmark <python_file> <function_name>")
                    continue
                target = Path(parts[0])
                func_name = parts[1]
                if not target.exists():
                    print_error(f"File not found: {target}")
                    continue
                try:
                    code = target.read_text()
                    namespace = {}
                    exec(code, namespace)
                    func = namespace.get(func_name)
                    if not func or not callable(func):
                        print_error(f"Function '{func_name}' not found")
                        continue
                    print_info(f"Benchmarking {func_name}()...")
                    result = benchmark_func(func, iterations=10000)
                    print(format_benchmark(result, func_name))
                except Exception as e:
                    print_error(f"Benchmark error: {e}")

            elif cmd == "agent":
                if not arg:
                    print_error("Usage: /agent <objective>")
                    print_info("Example: /agent 'Add JWT authentication to the API'")
                    continue
                if getattr(client, "is_offline", False):
                    print_error("Autonomous agent requires LLM. Configure API key first.")
                    continue
                agent = AutonomousAgent(client, context, executor)
                agent.run(arg)

            elif cmd == "research":
                if not arg:
                    print_error("Usage: /research <topic>")
                    print_info("Example: /research 'FastAPI JWT best practices'")
                    continue
                print(research_topic(arg))

            elif cmd == "github":
                if not arg:
                    if is_gh_available():
                        info = get_repo_info(context.cwd)
                        if info:
                            print(f"{Colors.CYAN}Repo: {info.get('name')}{Colors.RESET}")
                            print(f"  URL: {info.get('url')}")
                            prs = list_prs(context.cwd)
                            print(format_pr_list(prs))
                        else:
                            print_error("Not in a GitHub repo")
                    else:
                        print_error("GitHub CLI (gh) not installed or not authenticated")
                    continue
                parts = arg.split(maxsplit=1)
                subcmd = parts[0]
                rest = parts[1] if len(parts) > 1 else ""
                if subcmd == "pr":
                    if not rest:
                        prs = list_prs(context.cwd)
                        print(format_pr_list(prs))
                    else:
                        result = create_pr(rest, cwd=context.cwd)
                        if result["success"]:
                            print_success(f"PR created: {result.get('url', '')}")
                        else:
                            print_error(f"Failed: {result.get('error', 'unknown')}")
                elif subcmd == "branch":
                    if rest:
                        result = create_branch(rest, context.cwd)
                        if result["success"]:
                            print_success(f"Branch created: {result['branch']}")
                        else:
                            print_error(f"Failed: {result.get('error', '')}")
                    else:
                        print_error("Usage: /github branch <name>")
                elif subcmd == "issue":
                    if rest:
                        result = create_issue(rest, cwd=context.cwd)
                        if result["success"]:
                            print_success(f"Issue created: {result.get('url', '')}")
                        else:
                            print_error(f"Failed: {result.get('error', '')}")
                    else:
                        print_error("Usage: /github issue <title>")
                else:
                    print_error("Usage: /github [pr|branch|issue]")

            elif cmd == "skills":
                sm = SkillManager()
                print(sm.format_skills())

            elif cmd == "checkpoint":
                if not arg:
                    print_error("Usage: /checkpoint <task_id>")
                    continue
                cp = CheckpointManager.load_checkpoint(arg)
                if cp:
                    print(cp.format_summary())
                else:
                    print_error(f"Checkpoint '{arg}' not found")

            elif cmd == "checkpoints":
                checkpoints = CheckpointManager.list_checkpoints()
                if checkpoints:
                    print(f"{Colors.CYAN}Checkpoints:{Colors.RESET}")
                    for task_id, objective, updated in checkpoints:
                        print(f"  {Colors.YELLOW}{task_id}{Colors.RESET} — {objective}")
                else:
                    print_info("No checkpoints found")

            else:
                # Try plugins first
                if run_plugin(cmd, arg, context, client, executor):
                    continue
                print_error(f"Unknown command: /{cmd}. Type /help for available commands.")

            continue

        # Agentic mode trigger via '!' prefix
        agentic_mode = getattr(repl, "agentic_mode", False)
        if agentic_mode or user_input.startswith("!"):
            if user_input.startswith("!"):
                user_input = user_input[1:].strip()
            answer = run_agentic(client, context, executor, user_input)
            print(f"\n{Colors.MAGENTA}{Colors.BOLD}Cascade:{Colors.RESET}\n{answer}\n")
            continue

        # Normal chat input
        messages = context.get_messages(user_input)
        input_tokens = client.count_tokens(messages)
        if input_tokens > 1000:
            print(f"{Colors.DIM}(~{input_tokens} input tokens){Colors.RESET}")

        try:
            response = client.chat(messages)
        except Exception as e:
            print_error(f"LLM request failed: {e}")
            continue

        if response:
            context.add_message("user", user_input)
            context.add_message("assistant", response)

            # Render with syntax highlighting
            rendered = render_markdown(response)
            if rendered != response:
                print(f"\n{Colors.MAGENTA}{Colors.BOLD}Cascade:{Colors.RESET}\n", end="")
                print(rendered)
                print()

            # Check if AI suggested file edits
            edits_applied = handle_edits_from_response(response, context.cwd)
            if edits_applied:
                print_success(f"Applied {edits_applied} file edit(s)")

            # Check if AI suggested a command
            if not edits_applied:
                suggested_cmd = executor.parse_command_from_response(response)
                if suggested_cmd:
                    print()
                    if confirm(f"Run suggested command: {suggested_cmd}", default=False):
                        executor.execute(suggested_cmd, cwd=context.cwd)

    client.close()


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="cascade",
        description="Cascade CLI v2.0 - A terminal-based AI coding assistant",
    )
    parser.add_argument("--setup", action="store_true", help="Run setup wizard")
    parser.add_argument("--version", action="store_true", help="Show version")
    parser.add_argument("--provider", help="Override LLM provider")
    parser.add_argument("--model", help="Override model name")
    parser.add_argument("--api-key", help="Override API key")
    parser.add_argument("--profile", help="Switch to a profile")
    args = parser.parse_args()

    if args.version:
        from cascade import __version__
        print(f"Cascade CLI v{__version__}")
        sys.exit(0)

    if args.setup:
        setup_wizard()
        sys.exit(0)

    config = load_config()

    if args.profile:
        if switch_profile(config, args.profile):
            config = load_config()
        else:
            print_error(f"Unknown profile: {args.profile}")
            sys.exit(1)

    if args.provider:
        config["provider"] = args.provider
    if args.model:
        config["model"] = args.model
    if args.api_key:
        config["api_key"] = args.api_key

    # If no API key, enter offline mode (don't force setup)
    if not config.get("api_key"):
        print_warning("No API key found. Run `cascade --setup` to configure an LLM.")
        print_info("Entering offline mode — local commands available.")

    repl(config)


if __name__ == "__main__":
    main()
