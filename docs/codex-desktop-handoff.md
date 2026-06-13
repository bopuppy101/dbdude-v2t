# Codex Desktop Handoff

Use this file to restore context in a new Codex Desktop thread.

## Current Goal

We are configuring Codex Desktop on Mike's new Windows laptop so it can work in `C:\git\dbdude-v2t` without repeated approval prompts, and preferably with Git Bash-style commands.

## Workspace

- Repo: `C:\git\dbdude-v2t`
- Git Bash path: `/c/git/dbdude-v2t`
- User strongly prefers Git Bash commands whenever possible.
- Avoid PowerShell-specific commands unless there is no practical alternative.

## Voice-To-Text App Status

The `dbdude-v2t` Windows app is working.

- Launch from Git Bash:

```bash
cd /c/git/dbdude-v2t/windows
./venv/Scripts/python.exe dbdude-v2t.py
```

- User holds `Alt+Shift`, speaks, releases, and text is typed into the focused window.
- It is currently transcribing into Codex Desktop successfully.
- Laptop has Intel Arc GPU, no NVIDIA GPU.
- Current app path uses CPU mode with faster-whisper:

```text
INFO: No NVIDIA GPU detected, using CPU mode (slower)
INFO: Model Loaded. (quantization: int8)
```

- `int8` happens because `windows/dbdude-v2t.py` hardcodes:

```python
if ctranslate2.get_cuda_device_count() > 0:
    device = "cuda"
    compute_type = "float16"
else:
    device = "cpu"
    compute_type = "int8"
```

## Python Setup Notes

- Python 3.12.10 was installed globally via winget.
- Real Python path:

```text
C:\Users\mike\AppData\Local\Programs\Python\Python312\python.exe
```

- The broken venv issue was caused by an earlier repo-local NuGet Python build that did not include `tkinter`.
- Correct fix was to rebuild `windows/venv` from the global Python.org install.

## Codex Config Issue

The user is trying to stop Codex Desktop from prompting for command approvals.

Important file:

```text
C:\Users\mike\.codex\config.toml
```

Git Bash path:

```bash
/c/Users/mike/.codex/config.toml
```

Observed contents include:

```toml
model = "gpt-5.5"
model_reasoning_effort = "medium"
sandbox_mode = "danger-full-access"
approval_policy = "never"

[projects.'c:\git\dbdude-v2t']
trust_level = "trusted"

[windows]
sandbox = "elevated"
```

Codex Desktop UI still shows:

```text
Approval policy
Choose when Codex asks for approval
Unable to save
```

The deprecated hooks warning should be ignored. The user specifically said this is not about deprecated hooks.

Likely areas to check:

- File or directory write permissions on `C:\Users\mike\.codex\config.toml`
- Whether Codex Desktop has a per-thread/per-session permission state overriding the config
- Whether Codex Desktop has a UI bug saving approval policy
- Whether a new thread is needed for config changes to take effect

Known desktop state file:

```text
C:\Users\mike\.codex\.codex-global-state.json
```

Observed desktop state included:

```json
"integratedTerminalShell": "gitBash"
```

So Git Bash is already configured for the integrated terminal, but this old thread still reports the agent shell as PowerShell. That may be session-bound.

## Git Bash Codex Alias

Current `.bashrc` file:

```text
C:\Users\mike\.bashrc
```

Contains an alias intended to launch the Codex Desktop MSIX app:

```bash
alias codex='cmd.exe /c start "" "shell:AppsFolder\OpenAI.Codex_2p2nqsd0c76g0!App"'
```

This is convenience only. It may not affect what shell the Codex agent uses.

## Interrupting Codex Desktop

The user reports there is no visible square/stop button in Codex Desktop.

If Codex is stuck thinking or a tool call will not return, use Git Bash:

```bash
taskkill.exe /IM codex-command-runner.exe /F
```

If that does not release the thread:

```bash
taskkill.exe /IM codex.exe /F
```

If the desktop app itself must be killed:

```bash
taskkill.exe /IM Codex.exe /F
```

Sending a new chat message or pressing `Esc` may not interrupt an active tool call immediately.

## Working Style Preference

- Keep checks short.
- Report back before doing long investigations.
- Do not run long exploratory searches unless explicitly asked.
- Use Git Bash commands in user-facing instructions.
- Do not keep insisting the config is correct if the UI says it cannot save; investigate file permissions and desktop state carefully.
