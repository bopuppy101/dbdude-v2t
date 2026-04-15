# FN Key Detection on macOS — Approaches Tried

## Summary

Five approaches have been tried across two repos (macos-v2t and dbdude-v2t) for detecting FN key press/release on macOS. All five failed with the same symptom: stuck recordings where the FN release was not detected.

The root cause was not the API — it was macOS intercepting the FN/Globe key for the emoji picker. When "Press Globe key to" is set to "Show Emoji & Symbols" in System Settings, macOS swallows FN key events at the system level before they reach any application API.

**Fix:** System Settings > Keyboard > "Press 🌐 key to" → **"Do Nothing"**

---

## Approaches tried (chronological)

### 1. pynput (macos-v2t, initial)

**API:** `pynput.keyboard.Listener`

**Problem:** Dropped release events after extended use, causing stuck recordings.

**Replaced by:** CGEventTap

---

### 2. CGEventTap (macos-v2t)

**API:** `Quartz.CGEventTapCreate` with `kCGEventTapOptionListenOnly`

**How it works:** Listen-only tap into the Quartz/CoreGraphics event stream. Callback fires on modifier flag changes.

**Problem:** Silently stopped receiving events after minutes of use. macOS also disabled the tap via `kCGEventTapDisabledByTimeout`.

**Attempted fixes:**
- Re-enable on timeout (`CGEventTapEnable`) — still unreliable
- Watchdog timer — still unreliable
- Minimal callback (just sets a flag, no blocking) — still unreliable

**Replaced by:** CGEventSourceFlagsState polling

---

### 3. CGEventSourceFlagsState polling (macos-v2t → dbdude-v2t develop)

**API:** `Quartz.CGEventSourceFlagsState(kCGEventSourceStateHIDSystemState)`

**How it works:** Polls raw modifier flag state every 20ms in a loop.

**Problem:** macOS bug where the API permanently blocks after rapid FN presses. Once triggered, all subsequent calls also block. Requires `pkill -9` to recover. Occurs every 15-30 minutes.

**A threaded timeout workaround** (commit `6dd2d01`) was attempted and reverted (commit `aa50071`) because the underlying block is permanent.

---

### 4. NSEvent global monitor (dbdude-v2t, feature/event-based-transcription)

**API:** `NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(NSEventMaskFlagsChanged, callback)`

**How it works:** AppKit-level callback for modifier flag changes. Hybrid pattern — callback flips a boolean, polling loop reads it.

**Problem:** Monitor silently stopped delivering events. Five consecutive FN presses produced zero callbacks. Happened three times in 10 minutes on the built-in MacBook keyboard.

**Root cause found:** The Globe/FN key was set to "Show Emoji & Symbols" in System Settings. macOS was intercepting the key at the system level and swallowing events before they reached the NSEvent monitor.

---

### 5. NSEvent global monitor + Globe key disabled (current, working)

**API:** Same as #4 — `NSEvent.addGlobalMonitorForEventsMatchingMask_handler_`

**Change:** System Settings > Keyboard > "Press 🌐 key to" → **"Do Nothing"**

**Result:** Stable. No stuck recordings, no missed events. The NSEvent monitor receives all press and release events reliably when macOS is not intercepting the FN key for emoji.

This matches Wispr Flow's approach — they also require users to disable the Globe key emoji shortcut.

---

## Key finding

The API choice (pynput, CGEventTap, CGEventSourceFlagsState, NSEvent) was never the primary problem. The root cause was macOS intercepting the FN/Globe key at the system level for the emoji picker, preventing events from reaching application-level APIs.

It is likely that approaches #1-#3 would also work with the Globe key emoji disabled, but the NSEvent approach (#4/#5) is preferred because:
- It avoids the `CGEventSourceFlagsState` blocking bug
- It doesn't require Accessibility permissions (unlike CGEventTap)
- It uses the same hybrid pattern as the stable Windows version

## External keyboard note

When disconnecting from an external keyboard (e.g., unplugging a Magic Keyboard from a Studio Display), the NSEvent monitor may stop receiving events. Restart the application to recover. This is a rare edge case and not worth fixing at this time.

---

## References
- [Wispr Flow setup guide](https://docs.wisprflow.ai/articles/3152211871-setup-guide) — requires Globe key emoji disabled
- [Ghostty: CGEventTap stops after sleep/wake](https://github.com/ghostty-org/ghostty/discussions/11819)
- [KeePassXC: Replace GlobalEventMonitor with CGEventTap](https://github.com/keepassxreboot/keepassxc/issues/3393)
- [OBS Studio: Rewrite macOS hotkeys implementation](https://github.com/obsproject/obs-studio/pull/3914)
- [macos-v2t repo](https://github.com/bopuppy101/macos-v2t) — old repo with full commit history of approaches #1-#3
