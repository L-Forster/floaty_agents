from __future__ import annotations

import argparse
import os
import signal
from pathlib import Path
import shutil
import subprocess
import sys

from .config import cache_dir, config_path, load_config
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

    start = subparsers.add_parser("start", help="start the background hotkey listener")
    start.add_argument("--opacity", type=float, default=config.opacity, help="opacity to apply when HUD mode is enabled")
    start.add_argument("--hotkey", default=config.hotkey, help="pynput GlobalHotKeys spec")

    subparsers.add_parser("stop", help="stop the background hotkey listener")

    autostart = subparsers.add_parser("autostart", help="install or remove user autostart")
    autostart_subparsers = autostart.add_subparsers(dest="autostart_command", required=True)
    autostart_install = autostart_subparsers.add_parser("install", help="install autostart entry")
    autostart_install.add_argument("--opacity", type=float, default=config.opacity, help="opacity to apply when HUD mode is enabled")
    autostart_install.add_argument("--hotkey", default=config.hotkey, help="pynput GlobalHotKeys spec")
    autostart_subparsers.add_parser("remove", help="remove autostart entry")

    return parser


def parse_internal_command(argv: list[str]) -> tuple[str, argparse.Namespace] | None:
    config = load_config()
    if not argv:
        return None
    if argv[0] == "toggle":
        parser = argparse.ArgumentParser(prog="floaty toggle", add_help=False)
        parser.add_argument("--opacity", type=float, default=config.opacity)
        return "toggle", parser.parse_args(argv[1:])
    if argv[0] == "__listen":
        parser = argparse.ArgumentParser(prog="floaty __listen", add_help=False)
        parser.add_argument("--opacity", type=float, default=config.opacity)
        parser.add_argument("--hotkey", default=config.hotkey)
        return "__listen", parser.parse_args(argv[1:])
    return None


def run_toggle(opacity: float) -> int:
    adapter = get_runtime_adapter()
    message = adapter.toggle(opacity=opacity)
    print(message)
    return 0 if adapter.supported else 2


def pid_file() -> Path:
    return cache_dir() / "daemon.pid"


def log_file() -> Path:
    return cache_dir() / "daemon.log"


def is_process_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def read_pid() -> int | None:
    path = pid_file()
    if not path.exists():
        return None
    try:
        pid = int(path.read_text().strip())
    except Exception:
        path.unlink(missing_ok=True)
        return None
    if not is_process_running(pid):
        path.unlink(missing_ok=True)
        return None
    return pid


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

    cache_dir().mkdir(parents=True, exist_ok=True)
    pid_path = pid_file()
    pid_path.write_text(f"{os.getpid()}\n")

    def _toggle() -> None:
        print(adapter.toggle(opacity=opacity), flush=True)

    try:
        with keyboard.GlobalHotKeys({hotkey: _toggle}) as listener:
            listener.join()
    finally:
        pid_path.unlink(missing_ok=True)

    return 0


def run_daemon(opacity: float, hotkey: str) -> int:
    if not hotkey:
        print(f"floaty: no hotkey configured; pass --hotkey or set one in {config_path()}", file=sys.stderr)
        return 2

    existing_pid = read_pid()
    if existing_pid is not None:
        print(f"Floaty is already running in the background (pid {existing_pid})")
        return 0

    cache_dir().mkdir(parents=True, exist_ok=True)
    daemon_log = log_file()

    command = [
        floaty_command(),
        "__listen",
        "--opacity",
        f"{opacity:.2f}",
        "--hotkey",
        hotkey,
    ]

    popen_kwargs: dict[str, object] = {
        "stdin": subprocess.DEVNULL,
        "stdout": daemon_log.open("ab"),
        "stderr": subprocess.STDOUT,
        "start_new_session": True,
    }

    if os.name == "nt":
        popen_kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP

    process = subprocess.Popen(command, **popen_kwargs)
    print(f"Started background listener (pid {process.pid})")
    print(f"Hotkey: {hotkey}")
    print(f"Log file: {daemon_log}")
    return 0


def run_stop() -> int:
    pid = read_pid()
    if pid is None:
        print("Floaty is not running")
        return 0

    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        pid_file().unlink(missing_ok=True)
        print("Floaty is not running")
        return 0

    pid_file().unlink(missing_ok=True)
    print(f"Stopped background listener (pid {pid})")
    return 0


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
        f"{floaty_command()} start "
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


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    internal = parse_internal_command(argv)
    if internal is not None:
        command, args = internal
        if command == "__listen":
            return run_listen(args.opacity, args.hotkey)
        return run_toggle(args.opacity)

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command in (None, "start"):
        return run_daemon(getattr(args, "opacity", load_config().opacity), getattr(args, "hotkey", load_config().hotkey))
    if args.command == "stop":
        return run_stop()
    if args.command == "autostart":
        if args.autostart_command == "install":
            return run_autostart_install(args.opacity, args.hotkey)
        if args.autostart_command == "remove":
            return run_autostart_remove()

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
