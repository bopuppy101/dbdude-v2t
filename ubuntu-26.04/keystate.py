# Copyright (c) 2025-2026 Michael Foster / DBDude Inc. Licensed under the GNU General Public License v3.0 or later (GPL-3.0-or-later).
"""Root-free keyboard state tracking via /dev/input (evdev).

Replaces the `keyboard` library, which refuses to run without root on Linux.
Reading /dev/input/event* only needs the logind ACL that setup.bash's uaccess
udev rule grants the active desktop user. A background thread follows key
press/release events from
every attached keyboard and maintains the set of currently-held keycodes;
is_pressed() answers from that set, so it drops in for keyboard.is_pressed()
in the app's 20ms poll loop.

Pure Python: kernel input events are fixed 24-byte records (struct_input_event),
so no evdev package or compiled extension is required.
"""

import os
import glob
import select
import struct
import sys
import threading
import time

# struct input_event on 64-bit: struct timeval (2x long), __u16 type,
# __u16 code, __s32 value
_EVENT_FORMAT = 'llHHi'
_EVENT_SIZE = struct.calcsize(_EVENT_FORMAT)

_EV_KEY = 0x01

# Keycodes from /usr/include/linux/input-event-codes.h. Each name covers both
# left/right variants, matching the keyboard library's is_pressed() semantics.
_KEY_CODES = {
    'ctrl': {29, 97},    # KEY_LEFTCTRL, KEY_RIGHTCTRL
    'shift': {42, 54},   # KEY_LEFTSHIFT, KEY_RIGHTSHIFT
    'alt': {56, 100},    # KEY_LEFTALT, KEY_RIGHTALT
    'space': {57},       # KEY_SPACE
    'q': {16},           # KEY_Q
}

_pressed = set()          # keycodes currently held down
_lock = threading.Lock()
_devices = {}             # path -> open fd
_started = False


def _keyboard_event_paths():
    """Paths of input devices that are actual keyboards.

    Parses /proc/bus/input/devices: a keyboard advertises key events (EV bit 1)
    and, in its KEY bitmap, ordinary typing keys - Q (bit 16) and LEFTSHIFT
    (bit 42) - which mice and multimedia-button devices do not.
    """
    paths = []
    try:
        with open('/proc/bus/input/devices') as f:
            blocks = f.read().split('\n\n')
    except OSError:
        # Fallback: offer every event device; non-keyboards merely add idle fds.
        return glob.glob('/dev/input/event*')

    for block in blocks:
        handler = None
        is_keyboard = False
        for line in block.splitlines():
            if line.startswith('H: Handlers='):
                for tok in line.split('=', 1)[1].split():
                    if tok.startswith('event'):
                        handler = f"/dev/input/{tok}"
            elif line.startswith('B: KEY='):
                # Hex words, most significant first; last word holds bits 0-63.
                words = line.split('=', 1)[1].split()
                if words:
                    low = int(words[-1], 16)
                    is_keyboard = bool((low >> 16) & 1) and bool((low >> 42) & 1)
        if handler and is_keyboard:
            paths.append(handler)
    return paths


def _open_new_devices():
    """Open any keyboard devices we don't already follow. Returns error or None."""
    err = None
    for path in _keyboard_event_paths():
        if path in _devices:
            continue
        try:
            _devices[path] = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        except OSError as e:
            err = e
    return err


def _reader_loop():
    last_rescan = time.monotonic()
    while True:
        # Rescan periodically so keyboards plugged in mid-session get picked up.
        if time.monotonic() - last_rescan > 2.0:
            _open_new_devices()
            last_rescan = time.monotonic()

        fds = list(_devices.values())
        if not fds:
            time.sleep(0.5)
            continue

        try:
            readable, _, _ = select.select(fds, [], [], 1.0)
        except OSError:
            readable = []

        for fd in readable:
            try:
                data = os.read(fd, _EVENT_SIZE * 64)
            except OSError:
                # Device unplugged: drop it and clear anything it held down.
                for path, dfd in list(_devices.items()):
                    if dfd == fd:
                        del _devices[path]
                        os.close(dfd)
                with _lock:
                    _pressed.clear()
                continue

            for off in range(0, len(data) - _EVENT_SIZE + 1, _EVENT_SIZE):
                _, _, etype, code, value = struct.unpack_from(_EVENT_FORMAT, data, off)
                if etype != _EV_KEY:
                    continue
                with _lock:
                    if value == 0:
                        _pressed.discard(code)
                    else:  # 1 = press, 2 = autorepeat
                        _pressed.add(code)


def start():
    """Open keyboard devices and start the tracking thread.

    Exits with guidance if no keyboard is readable (the usual cause: the
    uaccess udev rule is not installed, or this is not the active desktop
    session, so logind has not granted the ACL).
    """
    global _started
    if _started:
        return
    err = _open_new_devices()
    if not _devices:
        print("ERROR: no readable keyboard devices in /dev/input.", file=sys.stderr)
        if isinstance(err, PermissionError):
            print("       Access is granted to the active desktop session by the udev", file=sys.stderr)
            print("       rule /etc/udev/rules.d/70-input-uaccess.rules. If it is missing,", file=sys.stderr)
            print("       re-run setup.bash; otherwise make sure you are running this from", file=sys.stderr)
            print("       the logged-in desktop, not an SSH or su session.", file=sys.stderr)
        sys.exit(1)
    threading.Thread(target=_reader_loop, daemon=True, name='keystate').start()
    _started = True


def is_pressed(name):
    """True while any keycode mapped to `name` ('alt', 'shift', ...) is held."""
    codes = _KEY_CODES[name]
    with _lock:
        return not _pressed.isdisjoint(codes)
