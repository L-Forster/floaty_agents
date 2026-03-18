from __future__ import annotations

from dataclasses import dataclass

from .base import RuntimeAdapter


@dataclass
class MacOSAdapter(RuntimeAdapter):
    name: str = "macOS adapter"
    supported: bool = False
    reason: str | None = "macOS runtime adapter is not implemented yet"
