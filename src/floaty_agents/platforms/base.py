from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RuntimeAdapter:
    name: str
    supported: bool
    reason: str | None = None

    def toggle(self, opacity: float) -> str:
        if self.supported:
            return f"{self.name}: toggle not implemented"
        return self.describe()

    def describe(self) -> str:
        status = "supported" if self.supported else "unsupported"
        if self.reason:
            return f"{self.name}: {status} ({self.reason})"
        return f"{self.name}: {status}"
