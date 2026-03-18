## HUD-style terminal toggling for coding agents.

`floaty-agents` is a user-space terminal HUD tool for coding-agent workflows. It is meant to make an active terminal feel more like an overlay on your desktop while an agent is working. It does not require root, does not edit system files, and only changes the currently focused terminal window at runtime.
<img width="1920" height="1101" alt="image" src="https://github.com/user-attachments/assets/1649f122-f0da-423b-b4e9-9005cd65abcf" />

## What it does

- targets terminal windows used for coding agents and shell-driven workflows
- detects the current platform
- detects whether the target window looks like a terminal
- toggles a HUD-like mode:
  - keep-on-top
  - partial transparency where the OS allows it
- runs in the background and toggles on a hotkey

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
git clone https://github.com/L-Forster/floaty_agents
cd floaty-agents
./floaty
```

That starts the background listener. Press `Ctrl+;` to toggle the focused terminal.

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
floaty stop
```

## Python Package Install

```bash
git clone https://github.com/L-Forster/floaty_agents
cd floaty-agents
python -m venv .venv
. .venv/bin/activate
pip install -e .
floaty
```

To start it automatically on login:

```bash
floaty autostart install
```

Default opacity is `0.55`.

Default hotkey is `Ctrl+;`.

Examples:

```bash
floaty
floaty stop
floaty autostart install
floaty start --hotkey '<ctrl>+backslash'
```

## Repo-local usage

If you do not want to install the package yet:

```bash
./floaty
./floaty stop
```

## Commands

```bash
floaty
floaty start
floaty stop
floaty autostart install
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
