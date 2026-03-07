# Wayland Input Migration: xdotool to ydotool

## Problem

Starting with Ubuntu 25.04, the default desktop session runs on Wayland with
XWayland providing backward compatibility for X11 applications. However,
Wayland's security model prevents X11 tools from injecting synthetic input
into Wayland-native windows.

`xdotool type` silently fails on Wayland-native windows — it reports success
(exit code 0) but keystrokes are never delivered. This broke dbdude-v2t's
ability to type transcribed text into the focused window.

## Root Cause

- Ubuntu 24.04: Most terminal emulators and apps run as X11 clients (or via
  XWayland). `xdotool` connects to the X server and injects keystrokes, which
  are delivered to the focused window.
- Ubuntu 25.04: Terminal emulators (GNOME Terminal, etc.) run as Wayland-native
  clients. The Wayland compositor isolates clients from each other — X11
  synthetic input events are not forwarded to Wayland-native windows.

### How we confirmed it

```bash
xdotool getactivewindow getwindowname
```

Returns a blank name for Wayland-native windows, confirming xdotool cannot
identify or interact with them, even though `getactivewindow` returns a
window ID.

## Solution

Replace `xdotool` with `ydotool`.

- **ydotool** uses `/dev/uinput` (the Linux kernel input subsystem), which
  operates below both X11 and Wayland. The compositor sees input from ydotool
  as real hardware input.
- Available in Ubuntu repos for both 24.04 and 25.04 (`universe` section).
- Drop-in replacement with nearly identical syntax.

### Install

```bash
sudo apt install ydotool
```

### Syntax difference

```bash
# Old (xdotool)
xdotool type --clearmodifiers -- "Hello world"

# New (ydotool)
ydotool type -- "Hello world"
```

The only difference: ydotool does not have the `--clearmodifiers` flag.

## References

- ydotool GitHub: https://github.com/ReimuNotMoe/ydotool
- xdotool GitHub: https://github.com/jordansissel/xdotool
- Wayland input security model: https://wayland.freedesktop.org/docs/html/
- Ubuntu 25.04 defaults to Wayland with GNOME on Mutter

## Backward Compatibility

To revert to xdotool (e.g., on a system without ydotool), change the
subprocess call in `dbdude-v2t.py` `type_with_xdotool()`:

```python
# ydotool (current - works on X11 and Wayland)
['ydotool', 'type', '--', text]

# xdotool (legacy - X11 only)
['xdotool', 'type', '--clearmodifiers', '--', text]
```
