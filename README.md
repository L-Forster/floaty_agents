# floaty-agents

HUD-style terminal toggling for coding agents.

`floaty-agents` is a user-space terminal HUD tool for coding-agent workflows. It is meant to make an active terminal feel more like an overlay on your desktop while an agent is working. It does not require root, does not edit system files, and only changes the currently focused terminal window at runtime.

## What it does

- targets terminal windows used for coding agents and shell-driven workflows
- detects the current platform
- detects whether the target window looks like a terminal
- toggles a HUD-like mode:
  - keep-on-top
  - partial transparency where the OS allows it
- optionally runs a global hotkey listener

## Current support

- Linux X11: implemented with raw X11 window properties
- Windows: implemented with Win32 APIs for topmost + transparency
- macOS: scaffolded but not implemented yet
- Wayland: not supported yet

Linux X11 uses the system `libX11` at runtime and does not require `python-xlib`. Linux support is currently best on X11 sessions, not Wayland.

## Roadmap

- improve Linux support beyond X11, with a realistic Wayland strategy where compositors allow it
- expand terminal detection and behavior across more terminal apps
- harden Windows support across more terminal and shell combinations
- implement a real macOS adapter instead of the current scaffold
- improve packaging and release flows for easier install on other machines

## Contributions

Contributions are welcome.

Areas where help is especially useful:

- Wayland compositor-specific support and research
- macOS window management implementation
- Windows compatibility testing
- packaging, installers, and release automation
- tests and reproducible bug reports across distros and terminal apps

## Zero-config behavior

- no desktop config edits
- no terminal profile edits
- no root or system-wide install
- optional user autostart if you want the shortcut available after login
- no files written outside normal Python caches and your current virtualenv

## Quickstart

Fastest repo-local use:

```bash
git clone <repo-url>
cd floaty-agents
./floaty
```

## Install A User Command

If you want `floaty` to work from anywhere without changing system files:

```bash
./scripts/install-user-command.sh
```

That only creates a user-local symlink:

```text
~/.local/bin/floaty
```

Then use:

```bash
floaty
floaty daemon --hotkey '<ctrl>+a'
```

## Python Package Install

```bash
git clone <repo-url>
cd floaty-agents
python -m venv .venv
. .venv/bin/activate
pip install -e .
floaty
```

To start the hotkey listener:

```bash
floaty daemon --hotkey '<ctrl>+a'
```

To start it automatically on login:

```bash
floaty autostart install --hotkey '<ctrl>+a'
```

Default opacity is `0.55`.

There is no default hotkey.

If you want one, set it explicitly in the command or in your user config file.

To create a user config file:

```bash
floaty config init
floaty config show
```

Config file location:

```text
Linux: ~/.config/floaty-agents/config.json
macOS: ~/Library/Application Support/floaty-agents/config.json
Windows: %APPDATA%\floaty-agents\config.json
```

Example:

```json
{
  "opacity": 0.55
}
```

Examples:

```bash
floaty listen --hotkey '<ctrl>+a'
floaty listen --hotkey '<ctrl>+a'
floaty listen --hotkey '<ctrl>+backslash'
floaty --opacity 0.55
```

## Repo-local usage

If you do not want to install the package yet:

```bash
./floaty
./floaty listen --hotkey '<ctrl>+a'
```

## Commands

```bash
floaty
floaty listen --hotkey '<ctrl>+a'
floaty daemon
floaty autostart install --hotkey '<ctrl>+a'
floaty config show
floaty doctor
floaty supports
```

## Detection rules

The focused window is treated as a terminal if its window class or process name matches common terminal apps such as:

- Konsole
- Windows Terminal
- WezTerm
- Alacritty
- Kitty
- Ghostty
- Foot
- Tilix
- GNOME Terminal
- Ptyxis
- Xfce Terminal
- Warp
- Hyper
- xterm

## Design goals

- easy for others to clone and run
- no permanent system mutations
- adapter-based so new platforms can be added cleanly
- honest about support instead of pretending every compositor behaves the same
- user-local installation and autostart only
