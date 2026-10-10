# Ubuntu 26.04 with Wayland: technical installation guide

This is a self-contained source installation reference for **Ubuntu 26.04 with Wayland**,
using `ubuntu-26.04/`. For the same platform with less implementation detail, see
[the beginner guide](installation-ubuntu-26-04-wayland-beginners.md). This guide describes repository scripts,
not a separately packaged installer.

## Prerequisites and compatibility

This path is for the Ubuntu 26.04 Wayland desktop and uses `ydotool`. Open a
terminal in your logged-in desktop and check:

```bash
cat /etc/os-release
echo "$XDG_SESSION_TYPE"
python3 --version
```

Confirm Ubuntu 26.04 and `wayland`. You need a microphone, sudo access for setup,
and Python 3.10+. If Python is missing, install distribution packages:

```bash
sudo apt update
sudo apt install python3 python3-venv
```

Do not remove/replace Ubuntu's system Python. Run setup as your normal user; the
script requests sudo for the system changes it needs. Normal launch does not use
sudo. Other Ubuntu/session combinations require separate validation.

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

Setup uses `python3`, checking the 3.10 minimum after system-package, udev, and
service operations. It installs `python3-venv`, creates a missing
`ubuntu-26.04/venv`, activates it, upgrades pip, and installs requirements.
Existing environments are reused. Dependencies include faster-whisper,
CTranslate2, sounddevice, scipy, and PySide6 without a complete version lockfile.

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

```bash
cd ubuntu-26.04
bash setup.bash
./run-dbdude-v2t.bash
```

[Setup](../ubuntu-26.04/setup.bash) installs `portaudio19-dev`, `ydotool`,
`pulseaudio-utils`, `python3-venv`, and `libxcb-cursor0`. It writes
`/etc/udev/rules.d/70-uinput-uaccess.rules` and `70-input-uaccess.rules`, reloads
and triggers udev, and configures the `ydotool.service` user drop-in at
`~/.config/systemd/user/ydotool.service.d/retry.conf`. It reenables and starts the
service and then performs Python setup. Service start failure prints a warning;
that warning is not proof text output is functional.

The [launcher](../ubuntu-26.04/run-dbdude-v2t.bash) sets `QT_QPA_PLATFORM=wayland`,
sets CUDA library paths, and runs as the desktop user. It also sets
`CUDA_VISIBLE_DEVICES=""`, forcing CPU mode. This setup script does not explicitly
load/persist the uinput module. Diagnose missing devices or
service units on the actual target system rather than assuming setup provisioned them.

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

The app checks `ubuntu-26.04/models/faster-whisper-<model>` before using the
Hugging Face backend. The default is `base`, English. Model loading occurs at
startup before normal tray/recording operation.

For a one-run model override, from `ubuntu-26.04/`:

```bash
./run-dbdude-v2t.bash --model tiny
```

For persistent settings, use the Configurator and restart. If model download fails
before the tray appears, launch the Configurator directly from `ubuntu-26.04/`:

```bash
./venv/bin/python3 configurator_gui.py
```

Choose an appropriate model/language, then relaunch through the supplied launcher.

## Optional R2T2 model

This folder does not provide an R2T2 setup option. Use the Whisper models exposed
by this variant; do not pass another platform's R2T2 flag to its setup script.

## GPU behavior

Setup installs NVIDIA runtime packages when `nvidia-smi` exists, but the supplied
launcher explicitly sets `CUDA_VISIBLE_DEVICES=""`. Normal launch therefore uses
CPU even on an NVIDIA machine. This is deliberate current script behavior;
installing more CUDA packages will not change it. Runtime code otherwise prefers
CUDA when visible, so bypassing the launcher changes behavior and omits its native
Wayland and library-path setup. The Configurator's `device` setting selects audio,
not GPU. Start with `base` or `tiny` on CPU.

## First successful dictation

1. Launch using the command or shortcut above. Keep the internet available for
   the first model download. Wait for startup; a download pause is not necessarily
   a hang, so inspect output before closing the app.
2. Open a plain text editor and click inside an empty document.
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

Use the command below from your platform folder for everyday launch.
Setup is not needed every day. From `ubuntu-26.04/`:

```bash
./run-dbdude-v2t.bash
```

Keep the terminal open while using a terminal-based launcher. Quit from the app's
tray/menu bar menu before replacing files. Keep the complete project folder in
its setup location; launchers and environments depend on files there.

For an optional application-menu shortcut, `ubuntu-26.04/dbdude-v2t.desktop` is
provided. Replace `CHANGE_THIS_PATH` in its `Exec` and `Icon` fields with your
actual repository path, retaining the `ubuntu-26.04` component, then copy it to
`~/.local/share/applications/`. Quote the Exec path if it contains spaces. Setup
does not install this entry automatically. It uses `Terminal=true`; update it if
you move the project. The terminal launcher remains the simplest first test.

## Settings, logs, and backups

Personal settings and customizations are stored in `~/.dbdude-v2t/`.
Back up this directory, including settings, mappings/rules and packs where present,
and any files you edited inside the project. Optional transcription logs are in the user's `~/logs` directory and are disabled
by default. Use the tray's Open Logs Folder action or inspect terminal launch
output for startup errors.

Model caches may live outside the project under the backend's cache management;
replacing source files is not the same as clearing cached models. Review log
contents before sharing them: they may contain dictated text.

## Updates and recovery

Quit the app before updating and make the backups described above. Preserve the
old working project until the new version passes the dictation test.

### If you downloaded a ZIP

1. Download the `develop` ZIP again and extract it into a **new** permanent folder.
   Do not overwrite your only working copy.
2. Open a terminal in the new project folder, enter `ubuntu-26.04`, and run
   `bash setup.bash`. Do not copy the old `venv` into the new folder.
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
cd ubuntu-26.04
bash setup.bash
```

A divergence error needs review, not a forced reset. Never use reset/clean simply
to get an update through. Setup reuses the existing venv; this is not a Python interpreter migration. Linux setup also reapplies system integration, so review it before rerunning on a customized machine.
Relaunch with `./run-dbdude-v2t.bash` from `ubuntu-26.04/` and repeat the dictation test.

If the updated copy fails, quit it before returning to the retained working copy.
Keep your settings backup too: both copies normally share the same user data.
**Reload Mapping Files** is for mapping-only edits; Python code updates require a
process restart.

## Troubleshooting and diagnostics

| Symptom | Check / next step |
| --- | --- |
| `cd` cannot find the folder | Start at the extracted project root, then enter `ubuntu-26.04` once. Quote paths with spaces. |
| Python is missing or too old | Complete prerequisites, reopen your terminal, and check the version again. |
| Package installation error | Record the first error and Python version; package wheels/constraints may exclude your interpreter. |
| Missing/broken venv | Check that setup completed in `ubuntu-26.04`. Preserve a damaged environment before recreating it. |
| First-use delay | Check download progress/output and network. Weights load at first launch, not during setup. |
| No text or hotkeys | Check the ydotool user service, input-device access, and session using the commands below. |
| Setup warns service failed | Setup can continue after this warning. Resolve the user-service/device failure before expecting typing to work. |
| Tray missing after using sudo | Quit that instance and use the normal-user launcher from the desktop session. |
| NVIDIA installed but app uses CPU | Expected: this variant's launcher deliberately hides the GPU. |
| No microphone input | Check OS input level, mute state, selected microphone, and the desktop audio session. |

From `ubuntu-26.04/`, verify the app environment without installing anything:

```bash
./venv/bin/python3 --version
./venv/bin/python3 -m pip check
```

`pip check` checks package consistency; it does not verify microphone access,
hotkeys, GPU loading, or text insertion.

From your logged-in desktop, inspect the text-output service and input devices:

```bash
systemctl --user status ydotool.service --no-pager
journalctl --user -u ydotool.service -n 50 --no-pager
ls -l /dev/uinput /dev/input/event*
```

If installed, `getfacl /dev/uinput /dev/input/event*` shows device ACLs. The setup
expects the distribution package to supply a suitable `ydotool.service` user unit;
if missing, inspect that package/unit rather than assuming it was created. Missing
unit, missing device, failed service, and missing ACL are different failures.
Setup may finish despite a service warning. Do not run the app as root to work
around it: the tray, audio, and permissions depend on the active desktop session.

For help, include OS/version and desktop session, Python version, the `ubuntu-26.04`
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
