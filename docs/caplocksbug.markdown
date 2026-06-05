# Caps Lock Bug (Windows) — Caps Lock key stops working while V2T runs

**Priority:** Low
**Status:** Logged — **do NOT start until the sleep/wake hardening work (all 3 layers) is complete.**
**Platform:** Windows (`windows/dbdude-v2t.py`)
**Logged:** 2026-06-05

## Symptom

While V2T is running, the **Caps Lock key no longer toggles caps**. The user has to
hold **Shift** to get uppercase letters. Caps Lock works normally again once V2T exits.

## Background

Caps Lock used to be a V2T recording control (push-to-talk / possibly a toggle). The
user **no longer wants Caps Lock used by V2T at all**, and wants the physical Caps Lock
key to behave normally (toggle caps) even while V2T runs.

## Likely cause (to verify, not yet confirmed)

V2T registers the Caps Lock key with `suppress=True`:

```python
# dbdude-v2t.py (approx :1539-1541)
if push_to_talk_keys.get('caps_lock', True):
    keyboard.on_press_key('caps lock', on_caps_lock_press, suppress=True)
    keyboard.on_release_key('caps lock', on_caps_lock_release, suppress=True)
```

`suppress=True` consumes the keystroke so Windows never performs the caps-lock toggle.
That is what disables the key.

## Interaction with the recent caps-lock-disable change

On 2026-06-01 / 2026-06-05 we set `caps_lock` to **False** as a push-to-talk key (in
`~/.dbdude-v2t/settings.json` and both code defaults). Because the suppressing hook above
is **gated** by `push_to_talk_keys.get('caps_lock', ...)`, it should **no longer be
registered** when `caps_lock` is False — meaning this bug may **already be fixed** on a
freshly restarted (or rebuilt) V2T.

## First step when we pick this up

1. **Verify whether it still reproduces** on a current build/run where `caps_lock` is
   False. If V2T was an older compiled exe or wasn't restarted, the old suppressing hook
   could still have been active.
2. If it still reproduces, find any other path that hooks Caps Lock with `suppress=True`
   and ensure none is registered when Caps Lock is not an enabled record key.
3. Confirm: with V2T running, Caps Lock toggles caps normally.

## Acceptance criteria

- With V2T running, pressing Caps Lock toggles caps exactly as it does without V2T.
- V2T does not consume or suppress the Caps Lock key in any mode.
