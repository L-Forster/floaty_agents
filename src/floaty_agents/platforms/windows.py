from __future__ import annotations

from dataclasses import dataclass, field

from .base import RuntimeAdapter

TERMINAL_PROCESS_NAMES = {
    "windowsterminal.exe",
    "wezterm-gui.exe",
    "alacritty.exe",
    "kitty.exe",
    "mintty.exe",
    "conemu64.exe",
    "conemu.exe",
    "hyper.exe",
    "warp.exe",
}


@dataclass
class WindowsAdapter(RuntimeAdapter):
    name: str = "Windows adapter"
    supported: bool = field(init=False)
    reason: str | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        try:
            import ctypes  # noqa: F401
        except ImportError:
            self.supported = False
            self.reason = "ctypes is unavailable"
            return

        self.supported = True

    def toggle(self, opacity: float) -> str:
        if not self.supported:
            return self.describe()

        import ctypes
        from ctypes import wintypes

        try:
            import psutil
        except ImportError:
            return "Windows adapter: missing dependency 'psutil'"

        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return "Windows adapter: no active window detected"

        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

        try:
            process_name = psutil.Process(pid.value).name().lower()
        except Exception:
            process_name = "unknown"

        if process_name not in TERMINAL_PROCESS_NAMES:
            return f"Windows adapter: focused window does not look like a supported terminal ({process_name})"

        GWL_EXSTYLE = -20
        WS_EX_LAYERED = 0x00080000
        WS_EX_TOPMOST = 0x00000008
        HWND_TOPMOST = -1
        HWND_NOTOPMOST = -2
        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_NOACTIVATE = 0x0010
        LWA_ALPHA = 0x00000002

        current_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        hud_enabled = bool(current_style & (WS_EX_LAYERED | WS_EX_TOPMOST))

        if hud_enabled:
            user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, current_style & ~WS_EX_LAYERED)
            user32.SetLayeredWindowAttributes(hwnd, 0, 255, LWA_ALPHA)
            return f"Windows adapter: HUD disabled for {process_name}"

        alpha = int(max(0.15, min(opacity, 1.0)) * 255)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, current_style | WS_EX_LAYERED)
        user32.SetLayeredWindowAttributes(hwnd, 0, alpha, LWA_ALPHA)
        user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
        return f"Windows adapter: HUD enabled at opacity={alpha / 255:.2f} for {process_name}"
