# Omarchy (Arch Linux + Hyprland): technical installation guide

This is a self-contained source installation reference for **Omarchy (Arch Linux + Hyprland)**,
using `omarchy/`. For the same platform with less implementation detail, see
[the beginner guide](installation-omarchy-beginners.md). This guide describes repository scripts,
not a separately packaged installer.

## Prerequisites and compatibility

This path targets Omarchy on Arch Linux with the Hyprland Wayland desktop. It is
not a generic installer for all Arch desktops. In your desktop terminal, check:

```bash
cat /etc/os-release
echo "$XDG_SESSION_TYPE"
python3 --version
```

Confirm the intended Arch/Omarchy environment and a Wayland session. You need a
microphone, Python 3.10+, and sudo access for setup. Omarchy normally provides
Python; the app setup script does not install it. If missing, use Arch's normal
system package workflow (avoid a partial system upgrade):

```bash
sudo pacman -Syu python
```

This may update other system packages; review pacman's transaction before accepting.
Do not remove or replace the system Python. Arch's Python includes venv. Run the
app's setup as your own user; it invokes sudo for system changes. Normal app
launch must use your desktop user, not root.

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

Setup checks the `python3` version after package, uinput, udev, and service setup.
It does not install Python itself. Arch's Python provides venv. The script creates
a missing `omarchy/venv`, activates it, upgrades pip, and installs requirements;
existing environments are reused. Dependencies include faster-whisper,
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
cd omarchy
bash setup.bash
./run-dbdude-v2t.bash
```

[Setup](../omarchy/setup.bash) installs `portaudio`, `libpulse`, `qt6-wayland`, and
`ydotool` using `pacman -S --needed --noconfirm`. It loads `uinput` and persists it
in `/etc/modules-load.d/uinput.conf`. It writes two device-access rules:
`/etc/udev/rules.d/70-uinput-uaccess.rules` and
`/etc/udev/rules.d/70-input-uaccess.rules`, then reloads/triggers udev.
It writes `~/.config/systemd/user/ydotool.service.d/retry.conf`, binding the user
service to the graphical session and limiting failed-start retries. It reloads
user systemd, resets failed state, reenables and starts `ydotool.service`, then
performs Python setup. Service start failure prints a warning; setup completion
alone does not prove the daemon is running.
These ACL rules grant active-session access to `/dev/uinput` and input event
devices; they do not add the user to the input group. System files are changed
by setup, so review the script before rerunning it on a customized machine.

The [launcher](../omarchy/run-dbdude-v2t.bash) runs as the desktop user with native
Wayland Qt and CUDA library paths. The tray icon is in Omarchy's tray drawer.
There is no need to edit desktop configuration just to complete installation.

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

The app checks `omarchy/models/faster-whisper-<model>` before using the
Hugging Face backend. The default is `base`, English. Model loading occurs at
startup before normal tray/recording operation.

For a one-run model override, from `omarchy/`:

```bash
./run-dbdude-v2t.bash --model tiny
```

For persistent settings, use the Configurator and restart. If model download fails
before the tray appears, launch the Configurator directly from `omarchy/`:

```bash
./venv/bin/python3 configurator_gui.py
```

Choose an appropriate model/language, then relaunch through the supplied launcher.

## Optional shared Whisper server

To share one Whisper on the GPU with other programs (such as dbdude-talk's
`/talk`), point the Omarchy dialect at a server that answers
`POST /v1/audio/transcriptions`, such as `dbdude-tts serve` from dbdude-talk.
Add `transcribe_url` to `~/.dbdude-v2t/settings.json`:

```json
{ "model": "large-v3-turbo", "language": "en", "transcribe_url": "http://127.0.0.1:8880" }
```

Each clip then goes to the server, and no local Whisper loads at startup (`model`
is not used; the server's model is printed at startup). If the server is
unreachable or fails, the clip is transcribed by a local `small` model on the CPU,
loaded the first time it is needed, and the next clip tries the server again. The
console shows which one was used and how long it took. Remove the key, or set it
to `""`, to load `model` locally as before. `r2t2` ignores it.

## Optional R2T2 model

R2T2 is an experimental alternative to Whisper. First complete the normal install
and successful dictation test. Then quit the app and, from `omarchy/`, run:

```bash
bash setup.bash --with-r2t2
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

You can also launch it for one run from `omarchy/`:

```bash
./run-dbdude-v2t.bash --model r2t2
```

## GPU behavior

Setup checks for `nvidia-smi` and installs `nvidia-cudnn-cu12` and
`nvidia-cublas-cu12` if the command exists. It does not install NVIDIA drivers.
The launcher provides CUDA library paths and leaves the GPU visible by default;
Whisper chooses CUDA/float16 if CTranslate2 detects it, otherwise CPU/int8.
The Configurator's `device` setting selects audio input, not GPU. From `omarchy/`,
a one-run CPU launch is:

```bash
CUDA_VISIBLE_DEVICES="" ./run-dbdude-v2t.bash
```

The launcher inherits this variable. This command changes only that invocation.

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
Setup is not needed every day. From `omarchy/`:

```bash
./run-dbdude-v2t.bash
```

Keep the terminal open while using a terminal-based launcher. Quit from the app's
tray/menu bar menu before replacing files. Keep the complete project folder in
its setup location; launchers and environments depend on files there.

For an optional application-menu shortcut, `omarchy/dbdude-v2t.desktop` is
provided. Replace `CHANGE_THIS_PATH` in its `Exec` and `Icon` fields with your
actual repository path, retaining the `omarchy` component, then copy it to
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
2. Open a terminal in the new project folder, enter `omarchy`, and run
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
cd omarchy
bash setup.bash
```

A divergence error needs review, not a forced reset. Never use reset/clean simply
to get an update through. Use the R2T2 setup flag instead when applicable. Setup
reuses the existing venv; this is not a Python interpreter migration. Linux setup also reapplies system integration, so review it before rerunning on a customized machine.
Relaunch with `./run-dbdude-v2t.bash` from `omarchy/` and repeat the dictation test.

If the updated copy fails, quit it before returning to the retained working copy.
Keep your settings backup too: both copies normally share the same user data.
**Reload Mapping Files** is for mapping-only edits; Python code updates require a
process restart.

## Troubleshooting and diagnostics

| Symptom | Check / next step |
| --- | --- |
| `cd` cannot find the folder | Start at the extracted project root, then enter `omarchy` once. Quote paths with spaces. |
| Python is missing or too old | Complete prerequisites, reopen your terminal, and check the version again. |
| Package installation error | Record the first error and Python version; package wheels/constraints may exclude your interpreter. |
| Missing/broken venv | Check that setup completed in `omarchy`. Preserve a damaged environment before recreating it. |
| First-use delay | Check download progress/output and network. Weights load at first launch, not during setup. |
| No text or hotkeys | Inspect the ydotool user service and active-session device access with the diagnostics below. |
| Missing `/dev/uinput` | Setup loads/persists uinput; inspect the setup error and device state before rerunning privileged steps. |
| Tray icon missing | Check Omarchy's tray drawer; launch as the normal desktop user, not root. |
| NVIDIA/runtime failure | Inspect the exact error; from `omarchy/`, try `CUDA_VISIBLE_DEVICES="" ./run-dbdude-v2t.bash` for a one-run CPU test. |
| No microphone input | Check OS input level, mute state, selected microphone, and the desktop audio session. |

From `omarchy/`, verify the app environment without installing anything:

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

For help, include OS/version and desktop session, Python version, the `omarchy`
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
