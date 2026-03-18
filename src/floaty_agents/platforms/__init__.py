from __future__ import annotations

import platform

from .base import RuntimeAdapter
from .linux_x11 import LinuxX11Adapter
from .macos import MacOSAdapter
from .windows import WindowsAdapter


def get_runtime_adapter() -> RuntimeAdapter:
    system = platform.system()

    if system == "Linux":
        return LinuxX11Adapter()
    if system == "Windows":
        return WindowsAdapter()
    if system == "Darwin":
        return MacOSAdapter()

    return RuntimeAdapter(
        name=f"{system or 'Unknown'} adapter",
        supported=False,
        reason="unsupported operating system",
    )
