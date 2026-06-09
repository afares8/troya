"""Shell completion generators for bash and zsh."""

from pathlib import Path

BASH_COMPLETION = '''
_cascade_completion() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    
    opts="--setup --version --provider --model --api-key --profile --help"
    commands="help read run ls cd tree grep stats git git-log git-diff commit agentic plan watch index search improve scaffold templates plugins detect clear context history save load sessions export profile profiles setup exit quit"
    profiles="openai openai-cheap anthropic ollama groq"
    
    if [[ ${cur} == -* ]]; then
        COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
        return 0
    fi
    
    if [[ ${prev} == --profile ]]; then
        COMPREPLY=( $(compgen -W "${profiles}" -- ${cur}) )
        return 0
    fi
    
    if [[ ${prev} == --provider ]]; then
        COMPREPLY=( $(compgen -W "openai anthropic ollama groq custom" -- ${cur}) )
        return 0
    fi
    
    COMPREPLY=( $(compgen -W "${commands}" -- ${cur}) )
    return 0
}

complete -F _cascade_completion cascade
'''

ZSH_COMPLETION = '''
#compdef cascade

_cascade() {
    local curcontext="$curcontext" state line
    typeset -A opt_args

    _arguments -C \\
        "(-h --help)"{-h,--help}"[Show help]" \\
        "--setup[Run setup wizard]" \\
        "--version[Show version]" \\
        "--provider[LLM provider]:provider:(openai anthropic ollama groq custom)" \\
        "--model[Model name]:model:" \\
        "--api-key[API key]:key:" \\
        "--profile[Config profile]:profile:(openai openai-cheap anthropic ollama groq)" \\
        "*:command:_cascade_commands"
}

_cascade_commands() {
    local commands=(
        "help:Show help message"
        "read:Read a file into context"
        "run:Run a shell command"
        "ls:List directory contents"
        "cd:Change working directory"
        "tree:Show directory tree"
        "grep:Search pattern in files"
        "stats:Show project statistics"
        "git:Show git status"
        "git-log:Show git log"
        "git-diff:Show git diff"
        "commit:Stage and commit"
        "agentic:Toggle autonomous mode"
        "plan:Create a task plan"
        "watch:Watch file changes"
        "index:Build code index"
        "search:Semantic code search"
        "improve:Analyze own code"
        "scaffold:Generate from template"
        "templates:List templates"
        "plugins:List plugins"
        "detect:Detect project type"
        "clear:Clear context"
        "context:Show context info"
        "history:Show command history"
        "save:Save session"
        "load:Load session"
        "sessions:List sessions"
        "export:Export to markdown"
        "profile:Switch profile"
        "profiles:List profiles"
        "setup:Run setup wizard"
        "exit:Exit CLI"
    )
    _describe -t commands "cascade command" commands
}

compdef _cascade cascade
'''


def install_completions(shell: str = "bash") -> Path:
    """Install shell completions."""
    if shell == "bash":
        comp_dir = Path.home() / ".bash_completion.d"
        comp_dir.mkdir(parents=True, exist_ok=True)
        path = comp_dir / "cascade"
        path.write_text(BASH_COMPLETION)
        return path
    elif shell == "zsh":
        zsh_dir = Path.home() / ".zsh_completions"
        zsh_dir.mkdir(parents=True, exist_ok=True)
        path = zsh_dir / "_cascade"
        path.write_text(ZSH_COMPLETION)
        return path
    else:
        raise ValueError(f"Unsupported shell: {shell}")
