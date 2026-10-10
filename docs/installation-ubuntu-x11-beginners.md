# Ubuntu with X11/Xorg: installation for beginners

This guide takes you from downloading dbdude-v2t to dictating your first sentence
on **Ubuntu with X11/Xorg**, using the `ubuntu/` folder. No programming experience is
required. Setup uses a terminal; everyday use has a launcher. All essential steps
are here. The optional [Ubuntu with X11/Xorg technical guide](installation-ubuntu-x11-technical.md)
explains more about dependencies and script behavior.

## Before you start

Have an internet connection for package installation and the first model download,
a microphone, and several GB of free disk space. Larger models and optional GPU
packages need more space. Download time depends on your connection and choices;
there is no fixed installation time. Recognition runs locally once the selected
model is available.

This path uses `xdotool` and requires an X11/Xorg desktop session. It is not a
native Wayland typing path. In a terminal opened from your desktop, check:

```bash
cat /etc/os-release
echo "$XDG_SESSION_TYPE"
python3 --version
```

The session should report `x11`. You need a microphone, sudo access for setup and
launch, and Python 3.10+. If Python is absent, install the distribution packages:

```bash
sudo apt update
sudo apt install python3 python3-venv
```

Do not replace/remove Ubuntu's system Python. Package compatibility also matters;
the version minimum is not an all-version compatibility guarantee.

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

Start in the **project root**, where `README.md` is visible. The `cd ubuntu`
command below enters the platform folder; do not repeat it if already there.

You do not need to create or activate a Python virtual environment. Setup creates
`ubuntu/venv`, a private home for the app's packages. Keep this folder in place.
Setup reuses it on later runs; it does not rebuild it just because Python changed.
When sudo asks for your password, type it and press Enter; no characters appearing is normal.

```bash
cd ubuntu
bash setup.bash
```

Setup installs system packages using `apt`, then creates the app environment and
installs Python packages. It may install CUDA packages if `nvidia-smi` is present.
When sudo asks for your password, type your login password and press Enter;
nothing appearing as you type is normal.

After successful setup, launch from the same folder:

```bash
./run-dbdude-v2t.bash
```

This variant asks for sudo permission at launch because its keyboard reader requires root.
Use its launcher so the audio and display settings are carried through. Do not
use this X11 path for native Wayland applications.

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
Setup is not needed every day. From `ubuntu/`:

```bash
./run-dbdude-v2t.bash
```

Keep the terminal open while using a terminal-based launcher. Quit from the app's
tray/menu bar menu before replacing files. Keep the complete project folder in
its setup location; launchers and environments depend on files there.

For an optional application-menu shortcut, `ubuntu/dbdude-v2t.desktop` is
provided. Replace `CHANGE_THIS_PATH` in its `Exec` and `Icon` fields with your
actual repository path, retaining the `ubuntu` component, then copy it to
`~/.local/share/applications/`. Quote the Exec path if it contains spaces. Setup
does not install this entry automatically. It uses `Terminal=true`; update it if
you move the project. The terminal launcher remains the simplest first test.

## Optional R2T2 model

This folder does not provide an R2T2 setup option. Use the Whisper models exposed
by this variant; do not pass another platform's R2T2 flag to its setup script.

## Settings, logs, and backups

Personal settings and customizations are stored in `~/.dbdude-v2t/` (the launcher resolves the sudo user as `/home/$SUDO_USER/.dbdude-v2t`).
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
2. Open a terminal in the new project folder, enter `ubuntu`, and run
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
cd ubuntu
bash setup.bash
```

A divergence error needs review, not a forced reset. Never use reset/clean simply
to get an update through. Setup reuses the existing venv; this is not a Python interpreter migration. Linux setup also reapplies system integration, so review it before rerunning on a customized machine.
Relaunch with `./run-dbdude-v2t.bash` from `ubuntu/` and repeat the dictation test.

If the updated copy fails, quit it before returning to the retained working copy.
Keep your settings backup too: both copies normally share the same user data.
**Reload Mapping Files** is for mapping-only edits; Python code updates require a
process restart.

## Troubleshooting

| Symptom | Check / next step |
| --- | --- |
| `cd` cannot find the folder | Start at the extracted project root, then enter `ubuntu` once. Quote paths with spaces. |
| Python is missing or too old | Complete prerequisites, reopen your terminal, and check the version again. |
| Package installation error | Record the first error and Python version; package wheels/constraints may exclude your interpreter. |
| Missing/broken venv | Check that setup completed in `ubuntu`. Preserve a damaged environment before recreating it. |
| First-use delay | Check download progress/output and network. Weights load at first launch, not during setup. |
| Session reports Wayland | This folder cannot type into native Wayland applications. Use a supported session/variant rather than treating the installers as interchangeable. |
| Password requested at launch | Expected for this X11 variant: the keyboard reader requires root. Use the supplied launcher. |
| No audio under sudo | Use the launcher, which forwards the desktop user's Pulse/PipeWire connection; check OS input levels and selected device. |
| No text | Focus an X11 editor, check xdotool installation, and confirm the desktop DISPLAY is available. |
| CUDA library error | Use the launcher for library paths and capture the exact runtime error; setup detection alone is insufficient. |

From `ubuntu/`, verify the app environment without installing anything:

```bash
./venv/bin/python3 --version
./venv/bin/python3 -m pip check
```

`pip check` checks package consistency; it does not verify microphone access,
hotkeys, GPU loading, or text insertion.

For help, include OS/version and desktop session, Python version, the `ubuntu`
variant, exact command and first error, and whether setup, launch, recording,
transcription, or text output failed. Git users can include `git rev-parse HEAD`.
Review logs before sharing; avoid including sensitive dictated text.

## Validation scope

These instructions were checked against the repository's current scripts and
paths. They are not a claim of a fresh installation test on this OS. Complete the
first-dictation test on your computer before relying on the installation.
