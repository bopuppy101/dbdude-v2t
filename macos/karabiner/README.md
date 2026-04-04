# Right Option → FN Remap for DBDude V2T

This optional Karabiner-Elements rule lets you trigger V2T with the **Right Option** key in addition to the FN key. The FN key continues to work as before.

## Install

```bash
cd macos/karabiner
./install.sh
```

The script will:
1. Offer to install Karabiner-Elements via Homebrew if it's not already installed
2. After installing, you must open Karabiner-Elements and work through the **permissions gauntlet** (see below)
3. Re-run `./install.sh` — it writes the rule directly into `karabiner.json` and Karabiner picks it up automatically. No manual UI steps needed.

## macOS Permissions Setup

Karabiner-Elements is a kernel-level keyboard interceptor. macOS requires you to enable **multiple permissions** before it will function. Expect to visit 4-6 different panels in System Settings.

When you first open Karabiner-Elements, it will repeatedly prompt you to enable things. **Follow every prompt** — it guides you through each one and shows you where to go in System Settings. The permissions include (but may not be limited to):

- **Accessibility** (System Settings > Privacy & Security > Accessibility)
- **Input Monitoring** (System Settings > Privacy & Security > Input Monitoring)
- **System Extensions** (System Settings > General > Login Items & Extensions)
- **Login Items** (System Settings > General > Login Items & Extensions)

There may be additional prompts depending on your macOS version. Keep following them until Karabiner stops complaining. It knows what it needs and will tell you what's missing.

**Be aware:** this is a powerful utility with low-level access to your keyboard input. The extensive permissions are there for good reason.

## Uninstall

```bash
cd macos/karabiner
./uninstall.sh
```

This removes the rule from `karabiner.json`. Right Option goes back to normal immediately.

## Karabiner-Elements UI Notes

The Karabiner-Elements app has a **hidden left sidebar panel** that is collapsed by default. You must click the expand icon to reveal it. This is not obvious.

That hidden panel is where **Complex Modifications** lives — which is where you can view, enable, or disable rules like ours. Without expanding the panel, you won't see Complex Modifications at all.

The install/uninstall scripts bypass the UI entirely by writing directly to `~/.config/karabiner/karabiner.json`, so you don't need the UI unless you want to manually toggle rules on or off.
