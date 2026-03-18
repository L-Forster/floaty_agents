from __future__ import annotations

import json
import os
import platform
from dataclasses import dataclass
from pathlib import Path

DEFAULT_OPACITY = 0.55


@dataclass
class FloatyConfig:
    hotkey: str | None = None
    opacity: float = DEFAULT_OPACITY


def app_dir(kind: str) -> Path:
    system = platform.system()

    if system == "Windows":
        base = os.environ.get("APPDATA") if kind == "config" else os.environ.get("LOCALAPPDATA")
        if base:
            return Path(base) / "floaty-agents"
    elif system == "Darwin":
        return Path.home() / "Library" / ("Application Support" if kind == "config" else "Caches") / "floaty-agents"
    else:
        if kind == "config":
            base = os.environ.get("XDG_CONFIG_HOME")
            if base:
                return Path(base) / "floaty-agents"
            return Path.home() / ".config" / "floaty-agents"
        base = os.environ.get("XDG_CACHE_HOME")
        if base:
            return Path(base) / "floaty-agents"
    return Path.home() / ".cache" / "floaty-agents"


def config_dir() -> Path:
    return app_dir("config")


def cache_dir() -> Path:
    return app_dir("cache")


def config_path() -> Path:
    return config_dir() / "config.json"


def load_config() -> FloatyConfig:
    path = config_path()
    if not path.exists():
        return FloatyConfig()

    try:
        data = json.loads(path.read_text())
    except Exception:
        return FloatyConfig()

    hotkey = data.get("hotkey")
    opacity = data.get("opacity", DEFAULT_OPACITY)

    try:
        opacity = float(opacity)
    except (TypeError, ValueError):
        opacity = DEFAULT_OPACITY

    opacity = max(0.15, min(opacity, 1.0))
    if not isinstance(hotkey, str) or not hotkey.strip():
        hotkey = None

    return FloatyConfig(hotkey=hotkey, opacity=opacity)


def write_default_config() -> Path:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(
            json.dumps(
                {
                    "opacity": DEFAULT_OPACITY,
                },
                indent=2,
            )
            + "\n"
        )
    return path
