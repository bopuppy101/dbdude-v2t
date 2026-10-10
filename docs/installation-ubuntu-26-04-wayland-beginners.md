# Ubuntu 26.04 with Wayland: installation for beginners

This guide takes you from downloading dbdude-v2t to dictating your first sentence
on **Ubuntu 26.04 with Wayland**, using the `ubuntu-26.04/` folder. No programming experience is
required. Setup uses a terminal; everyday use has a launcher. All essential steps
are here. The optional [Ubuntu 26.04 with Wayland technical guide](installation-ubuntu-26-04-wayland-technical.md)
explains more about dependencies and script behavior.

## Before you start

Have an internet connection for package installation and the first model download,
a microphone, and several GB of free disk space. Larger models and optional GPU
packages need more space. Download time depends on your connection and choices;
there is no fixed installation time. Recognition runs locally once the selected
model is available.

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

## Download the project

1. Open the [project on GitHub](https://github.com/bopuppy101/dbdude-v2t).
2. Select the `develop` branch, then **Code → Download ZIP**.
3. Extract the ZIP completely with your file manager. Do not run files from
   inside an archive viewer.
4. Move the extracted folder to a permanent location you own, such as Documents.
   It may be called `dbdude-v2t-develop`. Keep the whole folder together; launchers
   depend on files beside them. Avoid moving it after setup.

No GitHub account or Git installation is needed for this download method.
If someone already cloned the repository for you, use that folder instead.

## Open the correct folder and run setup

Open Terminal. Type `cd ` (including the space), drag the extracted project
folder into the window, and press Enter. Alternatively type
`cd "/full/path/to/dbdude-v2t-develop"`, replacing the example with your actual path.

Start in the **project root**, where `README.md` is visible. The `cd ubuntu-26.04`
command below enters the platform folder; do not repeat it if already there.

You do not need to create or activate a Python virtual environment. Setup creates
`ubuntu-26.04/venv`, a private home for the app's packages. Keep this folder in place.
Setup reuses it on later runs; it does not rebuild it just because Python changed.
When sudo asks for your password, type it and press Enter; no characters appearing is normal.

```bash
cd ubuntu-26.04
bash setup.bash
```

Setup uses sudo to install packages and configure keyboard/text-output device
access. It also configures a `ydotool` background service for your desktop login.
If setup reports that this service failed, use the troubleshooting section before
expecting text output to work.

Launch as your normal desktop user, from the same folder:

```bash
./run-dbdude-v2t.bash
```

The supplied launcher deliberately uses CPU even if setup installed NVIDIA
packages. Start with the default `base` model; technical users can review the
[GPU notes](installation-ubuntu-26-04-wayland-technical.md#gpu-behavior).

## Models and first download

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

## Everyday launch

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

## Optional R2T2 model

This folder does not provide an R2T2 setup option. Use the Whisper models exposed
by this variant; do not pass another platform's R2T2 flag to its setup script.

## Settings, logs, and backups

Personal settings and customizations are stored in `~/.dbdude-v2t/`.
Back up this directory, including settings, mappings/rules and packs where present,
and any files you edited inside the project. Optional transcription logs are in the user's `~/logs` directory and are disabled
by default. Use the tray's Open Logs Folder action or inspect terminal launch
output for startup errors.

Model caches may live outside the project under the backend's cache management;
replacing source files is not the same as clearing cached models. Review log
contents before sharing them: they may contain dictated text.

## Update safely

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

## Troubleshooting

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

These instructions were checked against the repository's current scripts and
paths. They are not a claim of a fresh installation test on this OS. Complete the
first-dictation test on your computer before relying on the installation.
