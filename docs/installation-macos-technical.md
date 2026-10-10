# macOS (Apple Silicon): technical installation guide

This is a self-contained source installation reference for **macOS (Apple Silicon)**,
using `macos/`. For the same platform with less implementation detail, see
[the beginner guide](installation-macos-beginners.md). This guide describes repository scripts,
not a separately packaged installer.

## Prerequisites and compatibility

Use a Mac with an Apple Silicon (M-series) chip. Check **Apple menu → About This Mac**.
The MLX speech engine in this folder targets Apple Silicon; this guide does not
provide an Intel Mac installation path. Have a microphone and permission to allow
Microphone and Accessibility access.

Open Terminal from Applications → Utilities and enter:

```bash
python3 --version
```

Python 3.10+ is the declared minimum. If Python is missing or too old, install it
from [python.org for macOS](https://www.python.org/downloads/macos/), then reopen
Terminal. Setup checks `python3.14`, `python3.13`, `python3.12`, `python3.11`,
`python3.10`, then `python3`, so it can find a newer version even if the unversioned
command points to Apple's older Python. Package compatibility also matters; the
minimum is not a promise that every newest release works.

Allow several GB of disk space plus room for your selected model and optional GPU
stack. Keep network access available for packages and first model load. There is
no repository-wide fully locked dependency set or verified all-Python-version
matrix; the declared minimum alone does not establish compatibility.

## Obtain the source

With Git already installed, clone the public repository:

```bash
git clone --branch develop https://github.com/bopuppy101/dbdude-v2t.git
cd dbdude-v2t
```

Without Git, open [the repository](https://github.com/bopuppy101/dbdude-v2t), select
`develop`, choose **Code → Download ZIP**, extract the whole archive, and keep it
in a permanent writable location. Do not run inside a ZIP viewer. The extracted
folder may be named `dbdude-v2t-develop`. Commands under setup start at the
repository root containing `README.md`; later commands state their working folder.

Open Terminal. Type `cd ` (including the space), drag the extracted project
folder into the window, and press Enter. Alternatively type
`cd "/full/path/to/dbdude-v2t-develop"`, replacing the example with your actual path.

## Python and environment behavior

Setup searches versioned Python commands in descending order from 3.14 to 3.10,
then `python3`, accepting Python 3 with minor version at least 10. It is not pinned
to 3.12. It checks for Python even when a venv exists, but reuses the venv rather
than migrating its interpreter. Current requirements include `mlx-whisper>=0.4.0`,
`pyobjc-framework-Quartz>=12.0`, and `PySide6>=6.6.0`. Historical notes about older
PyObjC versions do not describe these requirements.

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

From the repository root:

```bash
cd macos
bash setup.bash
bash dbdude-v2t.command
```

Setup also attempts to set the `.command` icon and reads `AppleFnUsageType`, warning
unless it is `3`. Set **System Settings → Keyboard → Press Globe key to → Do
Nothing**; see [Fn setup](macos-fn-key-setup.md). Grant Microphone and Accessibility
permissions to the relevant source-launch host. Relaunch after permission changes.

The Finder launcher is `dbdude-v2t.command`. It activates the venv and runs Python,
and currently force-stops matching `dbdude-v2t.py` processes before starting.
For a direct launch from `macos/`, after quitting other instances:

```bash
./venv/bin/python3 dbdude-v2t.py
```

For explicit interpreter selection when no venv exists, this example uses an
already installed Python 3.12 (substitute your verified compatible interpreter):

```bash
python3.12 -m venv venv
./venv/bin/python3 -m pip install --upgrade pip
./venv/bin/python3 -m pip install -r requirements.txt
bash setup.bash
```

This is an advanced alternative; normal setup already creates the environment.
The final setup invocation retains the existing environment and performs launcher
integration. The main audio path uses AVAudioEngine; `sounddevice` remains for
Configurator device listing. See the [audio implementation](../macos/docs/av-audio-engine-implementation.md).

## Models and download timing

Setup downloads Python packages, not speech-model weights. The default is
`small` in English when there are no saved settings. Weights are loaded at
**first transcription**, using bundled files or the backend cache if available; otherwise
they download from Hugging Face. Changing models may trigger another download.
Keep the connection available through the first successful transcription. A
successful package install alone does not establish offline readiness.

Start with the default. Smaller `tiny`/`base` models favor responsiveness; larger
models need more memory and time and may improve accuracy for some speech.
Use the Configurator to select the microphone, language, and model, then restart
to ensure changes take effect. Test a short sentence before committing to a large
model. Model choices are not a guarantee of every model/language combination.

For English, the source app checks `macos/models/whisper-<model>.en-mlx`; for other
languages it checks `macos/models/whisper-<model>-mlx`. A packaged app checks
Resources instead. Without a bundled model it calls mlx-whisper with the selected
Hugging Face repository. The default is `small` in English.

Change models/language through the Configurator and restart. This entry point does
not implement the Windows/Linux `--model` argument. It constructs `.en-mlx`
repository names mechanically: a model shown in the list is not proof that every
model/language combination exists. Start with the default before experimenting.

## Optional R2T2 model

R2T2 is an experimental alternative to Whisper. First complete the normal install
and successful dictation test. Then quit the app and, from `macos/`, run:

```bash
bash setup.bash --with-r2t2
```

It installs mlx-audio for a community 4-bit MLX conversion. The script estimates
about 1.5 GB of weights, downloaded on the first transcription with `r2t2` selected.
These are estimates, not the total installation size. The model uses NetEase's
Model Use License, separately from the project's GPL; see
[Confucius4-R2T2](https://huggingface.co/netease-youdao/Confucius4-R2T2).

Relaunch the app normally, open its Configurator, select `r2t2`, and restart. Keep the internet available for
the first model load. Installing the extra stack does not select it automatically;
Whisper remains in use until you choose `r2t2`. Return to the normal model in the
Configurator if the experimental model fails. Retain the optional flag when
rerunning setup during an update.

## GPU behavior

This variant uses MLX/Metal on Apple Silicon, not CUDA. Installing CUDA packages
will not enable an Intel Mac fallback. The main capture path is AVAudioEngine;
`sounddevice` remains for Configurator device listing.

## First successful dictation

1. Launch using the command or shortcut above. Keep the internet available for
   the first model download. Wait for startup; a download pause is not necessarily
   a hang, so inspect output before closing the app.
2. Open TextEdit in plain-text mode and click inside an empty document.
3. Hold **Fn/Globe**, say “This is my first test” clearly for a couple of
   seconds, then release the keys. Keep the editor focused.
4. Wait for text to appear at the cursor. The first recording triggers the model load/download, so this first result may take longer.
5. Try again. Once the model is cached, another download should not be needed
   unless you change models or remove cached files. The final period can be
   omitted by design.

If the test fails, distinguish hotkey detection, audio capture, transcription, and
text insertion using the troubleshooting section below. Do not treat a tray icon
or setup completion banner as proof of a working end-to-end installation.

## Everyday launch and shortcuts

Use `dbdude-v2t.command` in Finder or the command below for everyday launch.
Setup is not needed every day. From `macos/`:

```bash
bash dbdude-v2t.command
```

Keep the terminal open while using a terminal-based launcher. Quit from the app's
tray/menu bar menu before replacing files. Keep the complete project folder in
its setup location; launchers and environments depend on files there.

## Settings, logs, and backups

Personal settings and customizations are stored in `~/Library/Application Support/dbdude-v2t/`.
Back up this directory, including settings, mappings/rules and packs where present,
and any files you edited inside the project. Launch output is visible in Terminal and can contain dictated text.

Model caches may live outside the project under the backend's cache management;
replacing source files is not the same as clearing cached models. Review log
contents before sharing them: they may contain dictated text.

## Updates and recovery

Quit the app before updating and make the backups described above. Preserve the
old working project until the new version passes the dictation test.

### If you downloaded a ZIP

1. Download the `develop` ZIP again and extract it into a **new** permanent folder.
   Do not overwrite your only working copy.
2. Open a terminal in the new project folder, enter `macos`, and run
   `bash setup.bash`. If you use R2T2 and this variant supports it, use the optional
   flag shown in this guide. Do not copy the old `venv` into the new folder.
3. Launch the new copy and perform the first-dictation test above. It normally
   reads your existing user settings. Keep backups until you are satisfied.
4. Update any shortcut to the new location. Keep the old folder in place if you need to return to it.

### If you have a Git checkout

From the repository root, inspect the branch and your work:

```bash
git status --short --branch
git branch --show-current
```

If you have edits or untracked files, preserve and review them first. Once your
work is safely preserved and you intend to update the current branch:

```bash
git pull --ff-only
cd macos
bash setup.bash
```

A divergence error needs review, not a forced reset. Never use reset/clean simply
to get an update through. Use the R2T2 setup flag instead when applicable. Setup
reuses the existing venv; this is not a Python interpreter migration.
Relaunch with `bash dbdude-v2t.command` from `macos/` and repeat the dictation test.

If the updated copy fails, quit it before returning to the retained working copy.
Keep your settings backup too: both copies normally share the same user data.
**Reload Mapping Files** is for mapping-only edits; Python code updates require a
process restart.

## Troubleshooting and diagnostics

| Symptom | Check / next step |
| --- | --- |
| `cd` cannot find the folder | Start at the extracted project root, then enter `macos` once. Quote paths with spaces. |
| Python is missing or too old | Complete prerequisites, reopen your terminal, and check the version again. |
| Package installation error | Record the first error and Python version; package wheels/constraints may exclude your interpreter. |
| Missing/broken venv | Check that setup completed in `macos`. Preserve a damaged environment before recreating it. |
| First-use delay | Check download progress/output and network. Weights load at first transcription, not during setup. |
| Fn opens emoji or recording stays active | Set Globe/Fn to Do Nothing in Keyboard settings, check Accessibility, and relaunch. |
| No audio | Check Microphone permission for the source-launch host, OS input level, mute switch, and selected input device. |
| Recording works but nothing is typed | Focus a plain text editor and check Accessibility for Terminal/Python as applicable. |
| Model repository error | Check the chosen model and language. Return to the default `small`/English or another verified model combination. |
| Launcher fails after moving the project | Use the folder where setup ran; environments are not portable. Set up a new environment after relocating. |

From `macos/`, verify the app environment without installing anything:

```bash
./venv/bin/python3 --version
./venv/bin/python3 -m pip check
```

`pip check` checks package consistency; it does not verify microphone access,
hotkeys, GPU loading, or text insertion.

For help, include OS/version, Python version, the `macos`
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
