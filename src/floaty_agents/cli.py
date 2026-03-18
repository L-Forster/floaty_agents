from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

from .config import DEFAULT_OPACITY, cache_dir, config_path, load_config, write_default_config
from .platforms import get_runtime_adapter


def ensure_module(module_name: str, package_spec: str) -> bool:
    try:
        __import__(module_name)
        return True
    except ImportError:
        pass

    vendor_dir = cache_dir() / "vendor"
    vendor_dir.mkdir(parents=True, exist_ok=True)

    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--quiet",
                "--target",
                str(vendor_dir),
                package_spec,
            ],
            check=True,
        )
    except Exception:
        return False

    vendor_dir_str = str(vendor_dir)
    if vendor_dir_str not in sys.path:
        sys.path.insert(0, vendor_dir_str)

    try:
        __import__(module_name)
        return True
    except ImportError:
        return False


def build_parser() -> argparse.ArgumentParser:
    config = load_config()
    parser = argparse.ArgumentParser(prog="floaty")
    subparsers = parser.add_subparsers(dest="command")

    toggle = subparsers.add_parser("toggle", help="toggle HUD mode on the focused terminal")
    toggle.add_argument("--opacity", type=float, default=config.opacity, help="opacity to apply when HUD mode is enabled")

    listen = subparsers.add_parser("listen", help="listen for a global hotkey and toggle HUD mode")
    listen.add_argument("--opacity", type=float, default=config.opacity, help="opacity to apply when HUD mode is enabled")
    listen.add_argument("--hotkey", default=config.hotkey, help="pynput GlobalHotKeys spec")

    daemon = subparsers.add_parser("daemon", help="background hotkey listener for login/autostart use")
    daemon.add_argument("--opacity", type=float, default=config.opacity, help="opacity to apply when HUD mode is enabled")
    daemon.add_argument("--hotkey", default=config.hotkey, help="pynput GlobalHotKeys spec")

    autostart = subparsers.add_parser("autostart", help="install or remove user autostart")
    autostart_subparsers = autostart.add_subparsers(dest="autostart_command", required=True)
    autostart_install = autostart_subparsers.add_parser("install", help="install autostart entry")
    autostart_install.add_argument("--opacity", type=float, default=config.opacity, help="opacity to apply when HUD mode is enabled")
    autostart_install.add_argument("--hotkey", default=config.hotkey, help="pynput GlobalHotKeys spec")
    autostart_subparsers.add_parser("remove", help="remove autostart entry")

    config_cmd = subparsers.add_parser("config", help="show or create the user config file")
    config_subparsers = config_cmd.add_subparsers(dest="config_command", required=True)
    config_subparsers.add_parser("show", help="print config file path and current values")
    config_subparsers.add_parser("init", help="create a default config file if missing")

    subparsers.add_parser("doctor", help="show platform detection and support details")
    subparsers.add_parser("supports", help="show support matrix")

    return parser


def run_toggle(opacity: float) -> int:
    adapter = get_runtime_adapter()
    message = adapter.toggle(opacity=opacity)
    print(message)
    return 0 if adapter.supported else 2


def run_listen(opacity: float, hotkey: str) -> int:
    adapter = get_runtime_adapter()
    if not adapter.supported:
        print(adapter.describe())
        return 2

    if not hotkey:
        print(f"floaty: no hotkey configured; pass --hotkey or set one in {config_path()}", file=sys.stderr)
        return 2

    if not ensure_module("pynput", "pynput>=1.7"):
        print("floaty: failed to install/load 'pynput' for hotkey listening", file=sys.stderr)
        return 2

    from pynput import keyboard

    print(adapter.describe())
    print(f"Listening for {hotkey}. Press Ctrl+C to stop.")

    def _toggle() -> None:
        print(adapter.toggle(opacity=opacity), flush=True)

    with keyboard.GlobalHotKeys({hotkey: _toggle}) as listener:
        listener.join()

    return 0


def run_daemon(opacity: float, hotkey: str) -> int:
    return run_listen(opacity, hotkey)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def autostart_dir() -> Path:
    return Path.home() / ".config" / "autostart"


def autostart_file() -> Path:
    return autostart_dir() / "floaty-agents.desktop"


def floaty_command() -> str:
    installed = shutil.which("floaty")
    if installed:
        return installed
    return str(repo_root() / "floaty")


def shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def run_autostart_install(opacity: float, hotkey: str) -> int:
    if not hotkey:
        print(f"floaty: no hotkey configured; pass --hotkey or set one in {config_path()}", file=sys.stderr)
        return 2

    autostart_dir().mkdir(parents=True, exist_ok=True)
    desktop = autostart_file()
    exec_line = (
        f"{floaty_command()} daemon "
        f"--opacity {opacity:.2f} "
        f"--hotkey {shell_quote(hotkey)}"
    )
    desktop.write_text(
        "\n".join(
            [
                "[Desktop Entry]",
                "Type=Application",
                "Version=1.0",
                "Name=Floaty Agents",
                "Comment=Start floaty hotkey listener on login",
                f"Exec={exec_line}",
                "Terminal=false",
                "X-GNOME-Autostart-enabled=true",
            ]
        )
        + "\n"
    )
    print(f"Installed autostart entry: {desktop}")
    return 0


def run_autostart_remove() -> int:
    desktop = autostart_file()
    if desktop.exists():
        desktop.unlink()
        print(f"Removed autostart entry: {desktop}")
    else:
        print(f"Autostart entry not present: {desktop}")
    return 0


def run_config_show() -> int:
    cfg = load_config()
    print(f"path={config_path()}")
    print(f"hotkey={cfg.hotkey or ''}")
    print(f"opacity={cfg.opacity:.2f}")
    return 0


def run_config_init() -> int:
    path = write_default_config()
    print(f"Wrote config: {path}")
    return 0


def run_doctor() -> int:
    adapter = get_runtime_adapter()
    print(adapter.describe())
    return 0 if adapter.supported else 2


def run_supports() -> int:
    print("Linux X11: implemented")
    print("Windows: implemented")
    print("macOS: scaffolded, not implemented")
    print("Wayland: not supported")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command in (None, "toggle"):
        return run_toggle(getattr(args, "opacity", load_config().opacity))
    if args.command == "listen":
        return run_listen(args.opacity, args.hotkey)
    if args.command == "daemon":
        return run_daemon(args.opacity, args.hotkey)
    if args.command == "autostart":
        if args.autostart_command == "install":
            return run_autostart_install(args.opacity, args.hotkey)
        if args.autostart_command == "remove":
            return run_autostart_remove()
    if args.command == "config":
        if args.config_command == "show":
            return run_config_show()
        if args.config_command == "init":
            return run_config_init()
    if args.command == "doctor":
        return run_doctor()
    if args.command == "supports":
        return run_supports()

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
