# Windows: technical installation guide

This is a self-contained source installation reference for **Windows**,
using `windows/`. For the same platform with less implementation detail, see
[the beginner guide](installation-windows-beginners.md). This guide describes repository scripts,
not a separately packaged installer.

## Prerequisites and compatibility

Have a microphone and a Windows account that can install Python. An NVIDIA GPU
is optional; CPU operation is supported. Open PowerShell and enter:

```powershell
python --version
```

Python 3.10+ is the declared minimum. If it is missing, install Python from
[python.org for Windows](https://www.python.org/downloads/windows/) with its
standard Tk support and configure the `python` command according to the installer.
Close and reopen PowerShell, then check again. If the command opens the Store or
cannot be found, finish configuring Python before continuing. Do not assume that
the newest Python release is compatible with every required package.

Allow several GB of disk space plus room for your selected model and optional GPU
stack. Keep network access available for packages and first model load. There is
no repository-wide fully locked dependency set or verified all-Python-version
matrix; the declared minimum alone does not establish compatibility.

## Obtain the source

With Git already installed, clone the public repository:

```powershell
git clone --branch develop https://github.com/bopuppy101/dbdude-v2t.git
cd dbdude-v2t
```

Without Git, open [the repository](https://github.com/bopuppy101/dbdude-v2t), select
`develop`, choose **Code → Download ZIP**, extract the whole archive, and keep it
in a permanent writable location. Do not run inside a ZIP viewer. The extracted
folder may be named `dbdude-v2t-develop`. Commands under setup start at the
repository root containing `README.md`; later commands state their working folder.

In File Explorer, open the extracted project folder, click the address bar,
type `powershell`, and press Enter.

## Python and environment behavior

Windows setup uses `python` on PATH only to create a missing environment, using
`python -m venv --copies`. It prints the version but does not enforce the 3.10
minimum. An existing environment is reused through its explicit Python executable
for all pip operations. Current requirements constrain `PySide6>=6.8.0,<6.9.0`;
verify wheel availability for your Python version. The application also imports
`tkinter`, so the interpreter needs Tk support.

Every setup script creates a platform-local `venv` only when the directory is
absent; it does not repair a partial directory automatically. Installing a new
system Python does not migrate an existing venv. Dependencies have version and
wheel constraints beyond the declared Python minimum. If installation fails,
record the first error and interpreter version before choosing another interpreter.

For a damaged environment, quit the app and preserve the old `venv` under a backup
name before creating a replacement with the intended interpreter and rerunning
setup. Do not delete a working environment first or copy a venv between machines,
OSes, or project locations.

## Setup, permissions, and launch

From the repository root in PowerShell:

```powershell
cd windows
python --version
.\setup.ps1
.\dbdude-v2t.bat
```

For an execution-policy error, from `windows/`:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

Setup creates/reuses `venv`, installs requirements, probes `nvidia-smi`, optionally
installs cuDNN/cuBLAS packages, creates `%USERPROFILE%\logs`, and writes the desktop
shortcut `dbdude-v2t.lnk`. It does not install NVIDIA drivers. The app uses the
tracked `type_text.exe` helper; no separate AutoHotkey installation is invoked by
setup. Keep the helper with the source files.

The script does not explicitly check native-command exit codes after Python/pip
calls. In Windows PowerShell, `$ErrorActionPreference = "Stop"` alone does not make
all such failures terminating. Inspect errors rather than relying on the final
banner. From `windows/`, verify the environment separately:

```powershell
.\venv\Scripts\python.exe --version
.\venv\Scripts\python.exe -m pip check
.\venv\Scripts\python.exe dbdude-v2t.py --model base
```

The application hides its console during startup; use the tray console control
or `%USERPROFILE%\logs\v2t-error.log` for diagnostics. Microphone privacy settings
must permit desktop apps.

## Models and download timing

Setup downloads Python packages, not speech-model weights. The default is
`base` in English when there are no saved settings. Weights are loaded at
**first launch**, using bundled files or the backend cache if available; otherwise
they download from Hugging Face. Changing models may trigger another download.
Keep the connection available through the first successful transcription. A
successful package install alone does not establish offline readiness.

Start with the default. Smaller `tiny`/`base` models favor responsiveness; larger
models need more memory and time and may improve accuracy for some speech.
Use the Configurator to select the microphone, language, and model, then restart
to ensure changes take effect. Test a short sentence before committing to a large
model. Model choices are not a guarantee of every model/language combination.

The app checks `windows/models/faster-whisper-<model>` before asking faster-whisper
to load the model through Hugging Face. The default is `base`, English. Model
loading happens before the recording loop. If the selected model fails, the code
attempts the default `base` model; capture both errors if neither loads.

Use the Configurator and restart for persistent changes. A one-run override from
`windows/` is:

```powershell
.\venv\Scripts\python.exe dbdude-v2t.py --model tiny
```

The app normally loads saved settings directly; a startup Configurator is a legacy
mode enabled with `--configurator`. It hides its console during startup.

## Optional R2T2 model

R2T2 is an experimental alternative to Whisper. First complete the normal install
and successful dictation test. Then quit the app and, from `windows/`, run:

```powershell
.\setup.ps1 -WithR2T2
```

It installs qwen-asr and PyTorch. The script estimates about 4 GB of weights,
downloaded on launch with `r2t2` selected; packages can add several more GB.
An NVIDIA GPU is strongly recommended because CPU inference is slow. Setup chooses
the PyTorch cu128 index with NVIDIA tooling, otherwise the CPU index.
These are estimates, not the total installation size. The model uses NetEase's
Model Use License, separately from the project's GPL; see
[Confucius4-R2T2](https://huggingface.co/netease-youdao/Confucius4-R2T2).

Relaunch the app normally, open its Configurator, select `r2t2`, and restart. Keep the internet available for
the first model load. Installing the extra stack does not select it automatically;
Whisper remains in use until you choose `r2t2`. Return to the normal model in the
Configurator if the experimental model fails. Retain the optional flag when
rerunning setup during an update.

If execution policy blocks the optional setup, use this invocation-scoped command:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1 -WithR2T2
```

## GPU behavior

Setup probes `nvidia-smi` and installs `nvidia-cudnn-cu12` and `nvidia-cublas-cu12`
when detected. It does not install NVIDIA drivers. Runtime Whisper uses
CTranslate2 to select CUDA/float16 if a GPU is visible, otherwise CPU/int8. A
successful setup probe does not prove the runtime libraries work. The saved
`device` setting is an audio input selection, not a GPU selector.

## First successful dictation

1. Launch using the command or shortcut above. Keep the internet available for
   the first model download. Wait for startup; a download pause is not necessarily
   a hang, so inspect output before closing the app.
2. Open Notepad and click inside an empty document.
3. Hold **left Alt + Shift**, say “This is my first test” clearly for a couple of
   seconds, then release the keys. Keep the editor focused.
4. Wait for text to appear at the cursor. Model loading takes place at launch, before normal recording can begin.
5. Try again. Once the model is cached, another download should not be needed
   unless you change models or remove cached files. The final period can be
   omitted by design.

If the test fails, distinguish hotkey detection, audio capture, transcription, and
text insertion using the troubleshooting section below. Do not treat a tray icon
or setup completion banner as proof of a working end-to-end installation.

## Everyday launch and shortcuts

Use the desktop shortcut or `dbdude-v2t.bat` for everyday launch.
Setup is not needed every day. From `windows/`:

```powershell
.\dbdude-v2t.bat
```

Keep the terminal open while using a terminal-based launcher. Quit from the app's
tray/menu bar menu before replacing files. Keep the complete project folder in
its setup location; launchers and environments depend on files there.

## Settings, logs, and backups

Personal settings and customizations are stored in `%USERPROFILE%\.dbdude-v2t\`.
Back up this directory, including settings, mappings/rules and packs where present,
and any files you edited inside the project. Startup/error output is at `%USERPROFILE%\logs\v2t-error.log`. The app hides its
console on startup; use the tray console control when needed. Optional transcription
logs are in `%USERPROFILE%\logs\` and are disabled by default.

Model caches may live outside the project under the backend's cache management;
replacing source files is not the same as clearing cached models. Review log
contents before sharing them: they may contain dictated text.

## Updates and recovery

Quit the app before updating and make the backups described above. Preserve the
old working project until the new version passes the dictation test.

### If you downloaded a ZIP

1. Download the `develop` ZIP again and extract it into a **new** permanent folder.
   Do not overwrite your only working copy.
2. Open a terminal in the new project folder, enter `windows`, and run
   `.\setup.ps1`. If you use R2T2 and this variant supports it, use the optional
   flag shown in this guide. Do not copy the old `venv` into the new folder.
3. Launch the new copy and perform the first-dictation test above. It normally
   reads your existing user settings. Keep backups until you are satisfied.
4. Update any shortcut to the new location. Windows setup recreates its desktop shortcut.

### If you have a Git checkout

From the repository root, inspect the branch and your work:

```powershell
git status --short --branch
git branch --show-current
```

If you have edits or untracked files, preserve and review them first. Once your
work is safely preserved and you intend to update the current branch:

```powershell
git pull --ff-only
cd windows
.\setup.ps1
```

A divergence error needs review, not a forced reset. Never use reset/clean simply
to get an update through. Use the R2T2 setup flag instead when applicable. Setup
reuses the existing venv; this is not a Python interpreter migration.
Relaunch with `.\dbdude-v2t.bat` from `windows/` and repeat the dictation test.

If the updated copy fails, quit it before returning to the retained working copy.
Keep your settings backup too: both copies normally share the same user data.
**Reload Mapping Files** is for mapping-only edits; Python code updates require a
process restart.

## Troubleshooting and diagnostics

| Symptom | Check / next step |
| --- | --- |
| `cd` cannot find the folder | Start at the extracted project root, then enter `windows` once. Quote paths with spaces. |
| Python is missing or too old | Complete prerequisites, reopen your terminal, and check the version again. |
| Package installation error | Record the first error and Python version; package wheels/constraints may exclude your interpreter. |
| Missing/broken venv | Check that setup completed in `windows`. Preserve a damaged environment before recreating it. |
| First-use delay | Check download progress/output and network. Weights load at first launch, not during setup. |
| PowerShell blocks setup | Use the invocation-scoped execution-policy command above; managed policy may require your administrator. |
| Setup prints Complete after a pip error | Inspect the first error; the script does not explicitly stop on every native-command failure. |
| No tray icon | Check hidden icons and `%USERPROFILE%\logs\v2t-error.log`. |
| No audio | Enable microphone access for desktop apps and check the selected input/mute state. |
| Recording works but text is absent | Keep `type_text.exe` beside `dbdude-v2t.py`; test a normal, unelevated editor and inspect errors. |
| CUDA/model load failure | Check the first error and selected model; confirm driver/runtime compatibility before assuming installation succeeded. |

From `windows/`, verify the app environment without installing anything:

```powershell
.\venv\Scripts\python.exe --version
.\venv\Scripts\python.exe -m pip check
```

`pip check` checks package consistency; it does not verify microphone access,
hotkeys, GPU loading, or text insertion.

For help, include OS/version, Python version, the `windows`
variant, exact command and first error, and whether setup, launch, recording,
transcription, or text output failed. Git users can include `git rev-parse HEAD`.
Review logs before sharing; avoid including sensitive dictated text.

## Validation scope

Documentation paths, relative links, Bash syntax, and commands were compared
statically with this variant's setup script, launcher, requirements, and Python
entry point. Installations, model downloads, microphone access, GPU behavior, and
end-to-end operation were not executed as part of that review. Target-machine
validation should include fresh setup, first download, permissions, hotkey press
and release, text insertion, relaunch, and update with user settings preserved.
