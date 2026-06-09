"""Plugin system — dynamically load slash commands from .py files."""

import importlib.util
import sys
from pathlib import Path
from typing import Any, Callable

from .ui import Colors, print_error, print_info, print_success

PluginFunc = Callable[..., Any]

PLUGINS: dict[str, PluginFunc] = {}


def load_plugins(plugin_dir: Path | None = None) -> int:
    """Load all plugins from ~/.config/cascade-cli/plugins/*.py."""
    if plugin_dir is None:
        plugin_dir = Path.home() / ".config" / "cascade-cli" / "plugins"
    if not plugin_dir.exists():
        plugin_dir.mkdir(parents=True, exist_ok=True)
        return 0

    count = 0
    for file in sorted(plugin_dir.glob("*.py")):
        if file.name.startswith("_"):
            continue
        try:
            spec = importlib.util.spec_from_file_location(file.stem, file)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                sys.modules[file.stem] = mod
                spec.loader.exec_module(mod)
                # Register functions decorated with @register
                for name in dir(mod):
                    obj = getattr(mod, name)
                    if callable(obj) and hasattr(obj, "_cascade_command"):
                        cmd = obj._cascade_command
                        PLUGINS[cmd] = obj
                        count += 1
        except Exception as e:
            print_error(f"Plugin error in {file.name}: {e}")
    return count


def register_command(name: str, description: str = "") -> Callable:
    """Decorator to register a plugin command."""
    def decorator(func: PluginFunc) -> PluginFunc:
        func._cascade_command = name
        func._cascade_desc = description
        PLUGINS[name] = func
        return func
    return decorator


def run_plugin(cmd: str, arg: str, context, client, executor) -> bool:
    """Run a plugin command if it exists."""
    if cmd not in PLUGINS:
        return False
    try:
        PLUGINS[cmd](arg, context=context, client=client, executor=executor)
        return True
    except Exception as e:
        print_error(f"Plugin error: {e}")
        return True


def list_plugins() -> list[tuple[str, str]]:
    """Return registered plugin commands."""
    return [(cmd, getattr(fn, "_cascade_desc", "")) for cmd, fn in PLUGINS.items()]
