# Sleep/wake review findings

Date: October 3, 2026

## Scope and disposition

Reviewed `codex/macos-sleep-wake` at `4573ec39e012a718a9a842b74c33520896a84cd2` against common base `474a44a444d8b1140731bccd4a858d418fd3e051`. All sixteen committed changed files are under `macos/`; no committed Windows or Linux files are changed by this branch. The separately saved installation review and this document are local documentation additions, not part of that pushed commit.

The user requested documentation of these cases and explicitly declined fixes at this stage. **All proposed fixes below remain unimplemented.** This review did not merge, switch branches, commit, push, restart V2T, change permissions, or alter sleep settings. The installation review is preserved separately in [installation-experience-review.md](installation-experience-review.md).

The branch intends to release the microphone during screen sleep, system sleep, screen locking, and inactive user sessions, then recover audio and the Fn listener when the user returns. Its generation tokens, real-callback readiness check, serialized lifecycle operations, and held-output behavior are useful improvements over timer-gap-based recovery.

## Evidence and limits

On October 3, the existing macOS suite passed **73 tests**, and the repository formatting suite passed **one test**. Commands were run with Python's `-B` flag to prevent bytecode writes:

```bash
macos/venv/bin/python -B -m unittest discover -s macos/tests -q
macos/venv/bin/python -B -m unittest discover -s tests -q
```

Two additional cases below were reproduced in memory using the existing [mocked integration adapter](../macos/tests/testintegration.py). These checks did not access real audio, sleep the machine, type into another application, download models, or restart the running app. They establish conditional application behavior, not evidence that the corresponding native failures have happened to the user.

The third finding is a static responsiveness risk; no live latency measurement was performed. The user's belief that this M5 already passed testing is recorded as user-reported evidence, not independently repeated hardware validation. The committed [sleep/wake test results](../macos/docs/sleep-wake-test-results.md) contain real display-sleep, lid-close, and reconnect observations, alongside explicit limits and pending long-duration/docked tests.

## Finding 1: a missing matching wake notification can leave capture suspended

Priority: P2 / future resilience improvement.

Source: [macos/dbdude-v2t.py](../macos/dbdude-v2t.py), `_power_event` and `_sync_power`, lines 487–511 at the reviewed commit; watchdog invocation at lines 520–525.

A sleep notification adds a category to `_power_blockers`. Only the matching wake notification removes it. `_sync_power()` suspends whenever the set is nonempty, even if the current session/display query reports an awake, unlocked user session.

### Reproduction and result

1. Create the mocked application from `IntegrationTests.setUp()`.
2. Supply an audio callback and tick the lifecycle into Ready.
3. Deliver `NSWorkspaceScreensDidSleepNotification`.
4. Set `session_awake()` to return true, but omit the matching screen-wake notification.
5. Call the watchdog twenty times.

Observed result: lifecycle remained `suspended`, with `_power_blockers == {'screen'}`. Repeated current-state checks do not clear the stale notification blocker.

### Risk and future fix

If a matching wake notification is missed, the microphone can remain unavailable until another suitable notification or an application restart. The mock does not establish that macOS has actually dropped a notification on this machine.

A future change could reconcile notification blockers with sufficiently strong current-state evidence after a bounded transition period. It must preserve protection during a real sleep transition, out-of-order notifications, dark wakes, and locked sessions; blindly clearing all blockers on one awake query would weaken that protection. Add a regression test for a missing wake notification and tests for those transition cases. **Not implemented.**

## Finding 2: an output exception loses the transcript being delivered

Priority: P2 / future data-preservation improvement.

Source: [macos/dbdude-v2t.py](../macos/dbdude-v2t.py), `_process_ui_queue`, lines 547–563 at the reviewed commit.

The UI callback removes an item from `output_queue` and then calls `typer.type(char)` without a delivery exception handler. The existing held-dictation path handles suspension/session changes, but not an exception raised while typing.

### Reproduction and result

1. Create the mocked application and move the lifecycle to Ready.
2. Put `('abc', current_epoch)` into `output_queue`.
3. Configure the mock typer to raise `RuntimeError('simulated output failure')`.
4. Call `_process_ui_queue()` and catch the exception in the test harness.

Observed result: the exception escaped the callback; `output_queue` was empty and `held_results` was empty. The transcript was no longer available from either recovery path.

### Risk and future fix

A typing exception can lose a complete result or the remaining suffix of a partly delivered result. This is a confirmed behavior under a simulated output failure; a native typing exception was not induced. This finding does not claim that all forms of transcript loss were newly introduced by this branch—the previous direct-typing path also had limited recovery—but the new held-output mechanism does not cover this case.

A future change could catch errors around each delivery operation, preserve the undelivered suffix, and report that copying/retrying may be needed. For example, retain `text[index:]` on failure rather than allowing the item to disappear. Account for uncertainty about whether the failing character was already emitted to avoid claiming exactly-once delivery. Add tests for failure on the first character and after partial output. **Not implemented.**

## Finding 3: synchronous transcript delivery can delay Fn and power handling

Priority: responsiveness risk; not measured on the live app.

Source: [macos/dbdude-v2t.py](../macos/dbdude-v2t.py), control timer at lines 476–477, `_control_tick` at lines 513–518, and the full-result delivery loop at lines 547–560.

This branch moves recording control onto the main event loop. The same loop delivers every character of each queued transcript before returning. It also performs a native session/display check for each character. Consequently, a long or slow delivery occupies the loop that dispatches Fn control timers, UI activity, and power notifications.

Per-character `session_awake()` checks provide meaningful protection if the session locks during delivery. They do not themselves dispatch pending Fn events or control timers. Potential consequences include delayed recording start/stop, missed short press/release interactions, or delayed lifecycle work while a large result is being emitted.

A future improvement could send bounded output batches and yield between them, retaining the existing epoch and session checks. Test Fn press/release, screen locking, and sleep transitions during large or deliberately slow output. No performance benchmark or native reproduction was performed, and **no fix was implemented**.

## Reproduction harness for the two confirmed mock cases

Run from the repository root using the existing environment. This harness loads the repository's mocked integration test adapter, not the live application. It does not modify source files.

```bash
macos/venv/bin/python -B - <<'PY'
import sys
sys.path.insert(0, 'macos/tests')
from testintegration import IntegrationTests

reports = []
t = IntegrationTests()
t.setUp()
try:
    m = t.m
    m.lifecycle.callback(m.lifecycle.generation)
    m.lifecycle.tick()
    t.app._power_event('NSWorkspaceScreensDidSleepNotification')
    m.session_awake.return_value = True
    for _ in range(20):
        t.app._sleepwake_watchdog(None)
    reports.append(('missing wake', m.lifecycle.state,
                    sorted(t.app._power_blockers)))
finally:
    t.tearDown()

t = IntegrationTests()
t.setUp()
try:
    m = t.m
    m.lifecycle.callback(m.lifecycle.generation)
    m.lifecycle.tick()
    m.output_queue.put(('abc', m.lifecycle.epoch))
    m.typer.type.side_effect = RuntimeError('simulated output failure')
    try:
        t.app._process_ui_queue(None)
    except RuntimeError:
        pass
    reports.append(('typing failure', m.output_queue.empty(),
                    list(m.held_results)))
finally:
    t.tearDown()

for report in reports:
    print(report)
PY
```

Observed outputs:

```text
('missing wake', 'suspended', ['screen'])
('typing failure', True, [])
```

## Merge conflicts are separate from these findings

At review time, local `develop` was still `474a44a`, while GitHub `develop` was `211d53b0b717a24318337115ff975025378018da`, eight commits beyond that common base. The sleep/wake branch has one separate commit beyond the same base. Remote `develop` also contains other-platform work, including Omarchy support; those are changes already on the destination branch, not Windows/Linux changes introduced by the sleep/wake branch.

Both branches modify the same macOS `transcription_worker`. A three-way `git merge-file --stdout --diff3` check of the common-base file, local branch file, and exact remote-develop file produced two conflict regions. The check used temporary scratch files removed afterward and did not change the checkout, index, or Git refs.

The only overlapping source path requiring manual textual conflict resolution in the inspected snapshots is **`macos/dbdude-v2t.py`**:

1. **Beginning transcription:** sleep/wake adds an epoch validity check and monotonic timing. Develop restructures this same area so the Whisper model identifier is only computed in the Whisper path.
2. **Model/result handling:** develop adds `if model == R2T2_MODEL_NAME` and extracts either the R2T2 result or Whisper result. Sleep/wake changes timing/result-adjacent lines and moves final output through the epoch-protected output queue.

Relevant versions: [local sleep/wake worker](../macos/dbdude-v2t.py) at lines 406–441, and [remote develop worker at the inspected commit](https://github.com/bopuppy101/dbdude-v2t/blob/211d53b0b717a24318337115ff975025378018da/macos/dbdude-v2t.py#L457).

Minimal proposed conflict resolution, without addressing the findings above:

- Keep the sleep/wake queue tuple `(audio, recording_duration, epoch)` and its `lifecycle.can_deliver(epoch)` guard.
- Keep monotonic start and elapsed timing.
- Keep develop's R2T2-versus-Whisper selection and model-specific raw-text extraction.
- Apply shared text formatting to `raw`, then retain the sleep/wake branch's `output_queue.put((text, epoch))` path and logging controls.
- Preserve automatically merged additions, including R2T2 setup/configuration and all unrelated destination-branch changes. Do not select the entire file from only one side.
- Recheck the combined worker and existing suites. A conflict-free resolution is not proof that R2T2 or hardware behavior was tested successfully.

This plan integrates existing behavior from both branches; it does **not** implement the missing-notification reconciliation, output-error preservation, or output batching discussed above. No merge or code change was performed while documenting it.
