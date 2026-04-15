# macOS FN Key Setup

## Required setting

For V2T to reliably detect the FN key on macOS, you must disable the Globe key emoji shortcut:

**System Settings > Keyboard > "Press 🌐 key to" → "Do Nothing"**

Without this change, macOS intercepts the FN/Globe key at the system level for the emoji picker, causing V2T to miss key release events and get stuck in recording mode.

The emoji picker is still accessible via **Ctrl+Cmd+Space** after this change.

## Why this is necessary

On modern MacBooks, the FN key doubles as the Globe key. When set to "Show Emoji & Symbols," macOS handles the key at the firmware level before any application API can see it. This affects all voice-to-text apps that use the FN key — Wispr Flow has the same requirement.

## External keyboards

When switching between the built-in MacBook keyboard and an external keyboard (e.g., disconnecting a Magic Keyboard), V2T may stop detecting the FN key. Restart the application to recover.
