from __future__ import annotations

import ctypes
import os
from ctypes import POINTER, Structure, byref, c_char_p, c_int, c_long, c_ubyte, c_uint, c_ulong
from dataclasses import dataclass, field

from .base import RuntimeAdapter

TERMINAL_CLASSES = {
    "konsole",
    "kitty",
    "wezterm",
    "alacritty",
    "ghostty",
    "foot",
    "tilix",
    "gnome-terminal",
    "ptyxis",
    "xfce4-terminal",
    "warp",
    "hyper",
    "xterm",
}

XA_WINDOW = 33
XA_ATOM = 4
XA_STRING = 31
PROP_MODE_REPLACE = 0
CLIENT_MESSAGE = 33
SUBSTRUCTURE_NOTIFY_MASK = 1 << 19
SUBSTRUCTURE_REDIRECT_MASK = 1 << 20


class XClientMessageData(Structure):
    _fields_ = [("l", c_long * 5)]


class XClientMessageEvent(Structure):
    _fields_ = [
        ("type", c_int),
        ("serial", c_ulong),
        ("send_event", c_int),
        ("display", ctypes.c_void_p),
        ("window", c_ulong),
        ("message_type", c_ulong),
        ("format", c_int),
        ("data", XClientMessageData),
    ]


class XEvent(Structure):
    _fields_ = [("xclient", XClientMessageEvent), ("pad", c_long * 24)]


@dataclass
class LinuxX11Adapter(RuntimeAdapter):
    name: str = "Linux X11 adapter"
    supported: bool = field(init=False)
    reason: str | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        if os.environ.get("WAYLAND_DISPLAY"):
            self.supported = False
            self.reason = "Wayland detected; only X11 is supported right now"
            return

        if not os.environ.get("DISPLAY"):
            self.supported = False
            self.reason = "DISPLAY is not set"
            return

        try:
            self._x11 = ctypes.cdll.LoadLibrary("libX11.so.6")
        except OSError:
            self.supported = False
            self.reason = "libX11 is unavailable"
            return

        self._configure_signatures()
        test_display = self._open_display()
        if not test_display:
            self.supported = False
            self.reason = "cannot open the X display; check DISPLAY/XAUTHORITY"
            return

        self._x11.XCloseDisplay(test_display)
        self.supported = True

    def _configure_signatures(self) -> None:
        x11 = self._x11
        x11.XOpenDisplay.argtypes = [c_char_p]
        x11.XOpenDisplay.restype = ctypes.c_void_p
        x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
        x11.XCloseDisplay.restype = c_int
        x11.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
        x11.XDefaultRootWindow.restype = c_ulong
        x11.XInternAtom.argtypes = [ctypes.c_void_p, c_char_p, c_int]
        x11.XInternAtom.restype = c_ulong
        x11.XGetWindowProperty.argtypes = [
            ctypes.c_void_p,
            c_ulong,
            c_ulong,
            c_long,
            c_long,
            c_int,
            c_ulong,
            POINTER(c_ulong),
            POINTER(c_int),
            POINTER(c_ulong),
            POINTER(c_ulong),
            POINTER(POINTER(c_ubyte)),
        ]
        x11.XGetWindowProperty.restype = c_int
        x11.XFree.argtypes = [ctypes.c_void_p]
        x11.XFree.restype = c_int
        x11.XChangeProperty.argtypes = [
            ctypes.c_void_p,
            c_ulong,
            c_ulong,
            c_ulong,
            c_int,
            c_int,
            POINTER(c_ubyte),
            c_int,
        ]
        x11.XChangeProperty.restype = c_int
        x11.XDeleteProperty.argtypes = [ctypes.c_void_p, c_ulong, c_ulong]
        x11.XDeleteProperty.restype = c_int
        x11.XSendEvent.argtypes = [ctypes.c_void_p, c_ulong, c_int, c_long, POINTER(XEvent)]
        x11.XSendEvent.restype = c_int
        x11.XFlush.argtypes = [ctypes.c_void_p]
        x11.XFlush.restype = c_int

    def _open_display(self) -> ctypes.c_void_p | None:
        return self._x11.XOpenDisplay(None)

    def _get_property(self, display: ctypes.c_void_p, window: int, prop: int, req_type: int) -> tuple[int, int, bytes] | None:
        actual_type = c_ulong()
        actual_format = c_int()
        nitems = c_ulong()
        bytes_after = c_ulong()
        prop_return = POINTER(c_ubyte)()

        status = self._x11.XGetWindowProperty(
            display,
            c_ulong(window),
            c_ulong(prop),
            0,
            1024,
            0,
            c_ulong(req_type),
            byref(actual_type),
            byref(actual_format),
            byref(nitems),
            byref(bytes_after),
            byref(prop_return),
        )
        if status != 0 or not prop_return:
            return None

        item_size = max(1, actual_format.value // 8)
        size = int(nitems.value) * item_size
        data = ctypes.string_at(prop_return, size)
        self._x11.XFree(prop_return)
        return actual_type.value, actual_format.value, data

    def _get_active_window(self, display: ctypes.c_void_p, root: int) -> int | None:
        atom = self._x11.XInternAtom(display, b"_NET_ACTIVE_WINDOW", 0)
        prop = self._get_property(display, root, atom, XA_WINDOW)
        if not prop or not prop[2]:
            return None
        width = max(4, prop[1] // 8)
        return int.from_bytes(prop[2][:width], byteorder="little")

    def _get_wm_class(self, display: ctypes.c_void_p, window: int) -> tuple[str, ...]:
        atom = self._x11.XInternAtom(display, b"WM_CLASS", 0)
        prop = self._get_property(display, window, atom, XA_STRING)
        if not prop or not prop[2]:
            return ()
        return tuple(part.lower() for part in prop[2].rstrip(b"\x00").decode(errors="ignore").split("\x00") if part)

    def _get_atoms(self, display: ctypes.c_void_p, window: int, atom_name: bytes) -> set[int]:
        atom = self._x11.XInternAtom(display, atom_name, 0)
        prop = self._get_property(display, window, atom, XA_ATOM)
        if not prop or not prop[2]:
            return set()
        atom_size = ctypes.sizeof(c_ulong)
        return {
            int.from_bytes(prop[2][i : i + atom_size], byteorder="little")
            for i in range(0, len(prop[2]), atom_size)
            if len(prop[2][i : i + atom_size]) == atom_size
        }

    def _get_cardinal(self, display: ctypes.c_void_p, window: int, atom_name: bytes) -> int | None:
        atom = self._x11.XInternAtom(display, atom_name, 0)
        prop = self._get_property(display, window, atom, 0)
        if not prop or not prop[2]:
            return None
        size = min(len(prop[2]), ctypes.sizeof(c_ulong))
        return int.from_bytes(prop[2][:size], byteorder="little")

    def _send_wm_state(self, display: ctypes.c_void_p, root: int, window: int, action: int, state_atom: int) -> None:
        net_wm_state = self._x11.XInternAtom(display, b"_NET_WM_STATE", 0)
        event = XEvent()
        event.xclient.type = CLIENT_MESSAGE
        event.xclient.serial = 0
        event.xclient.send_event = 1
        event.xclient.display = display
        event.xclient.window = window
        event.xclient.message_type = net_wm_state
        event.xclient.format = 32
        event.xclient.data.l[0] = action
        event.xclient.data.l[1] = state_atom
        event.xclient.data.l[2] = 0
        event.xclient.data.l[3] = 1
        event.xclient.data.l[4] = 0
        self._x11.XSendEvent(
            display,
            c_ulong(root),
            0,
            SUBSTRUCTURE_NOTIFY_MASK | SUBSTRUCTURE_REDIRECT_MASK,
            byref(event),
        )

    def toggle(self, opacity: float) -> str:
        if not self.supported:
            return self.describe()

        display = self._open_display()
        if not display:
            return "Linux X11 adapter: cannot open the X display; check DISPLAY/XAUTHORITY"

        try:
            root = self._x11.XDefaultRootWindow(display)
            window = int(os.environ.get("WINDOWID", "0") or "0")
            if not window:
                window = self._get_active_window(display, root)
            if not window:
                return "Linux X11 adapter: no active window detected"

            wm_class = self._get_wm_class(display, window)
            if not any(terminal in value for value in wm_class for terminal in TERMINAL_CLASSES):
                return f"Linux X11 adapter: focused window does not look like a supported terminal ({'/'.join(wm_class) or 'unknown'})"

            state_above = self._x11.XInternAtom(display, b"_NET_WM_STATE_ABOVE", 0)
            current_states = self._get_atoms(display, window, b"_NET_WM_STATE")
            current_opacity = self._get_cardinal(display, window, b"_NET_WM_WINDOW_OPACITY")

            hud_enabled = (state_above in current_states) or (
                current_opacity is not None and current_opacity < int(0xFFFFFFFF * 0.99)
            )

            self._send_wm_state(display, root, window, 0 if hud_enabled else 1, state_above)

            opacity_atom = self._x11.XInternAtom(display, b"_NET_WM_WINDOW_OPACITY", 0)
            if hud_enabled:
                self._x11.XDeleteProperty(display, c_ulong(window), opacity_atom)
                mode = "disabled"
            else:
                target_alpha = max(0.15, min(opacity, 1.0))
                target_raw = c_ulong(int(0xFFFFFFFF * target_alpha))
                self._x11.XChangeProperty(
                    display,
                    c_ulong(window),
                    opacity_atom,
                    c_ulong(6),
                    32,
                    PROP_MODE_REPLACE,
                    ctypes.cast(byref(target_raw), POINTER(c_ubyte)),
                    1,
                )
                mode = f"enabled at opacity={target_alpha:.2f}"

            self._x11.XFlush(display)
            return f"Linux X11 adapter: HUD {mode} for {'/'.join(wm_class)}"
        finally:
            self._x11.XCloseDisplay(display)
