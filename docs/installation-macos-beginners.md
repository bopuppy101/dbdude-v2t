# macOS (Apple Silicon): installation for beginners

This guide takes you from downloading dbdude-v2t to dictating your first sentence
on **macOS (Apple Silicon)**, using the `macos/` folder. No programming experience is
required. Setup uses a terminal; everyday use has a launcher. All essential steps
are here. The optional [macOS (Apple Silicon) technical guide](installation-macos-technical.md)
explains more about dependencies and script behavior.

## Before you start

Have an internet connection for package installation and the first model download,
a microphone, and several GB of free disk space. Larger models and optional GPU
packages need more space. Download time depends on your connection and choices;
there is no fixed installation time. Recognition runs locally once the selected
model is available.

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

Start in the **project root**, where `README.md` is visible. The `cd macos`
command below enters the platform folder; do not repeat it if already there.

You do not need to create or activate a Python virtual environment. Setup creates
`macos/venv`, a private home for the app's packages. Keep this folder in place.
Setup reuses it on later runs; it does not rebuild it just because Python changed.

```bash
cd macos
bash setup.bash
```

Setup checks Python, creates the app environment, installs packages, sets the
launcher icon when possible, and checks the Fn/Globe key setting. It does not
install Python for you. Wait for **Setup Complete** and check that no package
installation error appeared.

Before dictating, set **System Settings → Keyboard → Press Globe key to → Do
Nothing**. See the [Fn key guide](macos-fn-key-setup.md).

In Finder, open the `macos` folder and double-click `dbdude-v2t.command`.
If opening the script fails, use this command from that same folder:

```bash
bash dbdude-v2t.command
```

Allow Microphone and Accessibility access when requested. If keys or audio do not
work, check **System Settings → Privacy & Security** for those permissions. With
this source installation, the relevant entry may be Terminal or the Python host
rather than an app named dbdude-v2t. Relaunch after changing permissions. The
menu bar icon and Terminal's **Ready** message indicate startup; the first
transcription can still need a model download.

## Models and first download

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
On macOS, model names are built from the selected size/language; start with the default small/English because not every listed combination has a corresponding repository.

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

## Everyday launch

Use `dbdude-v2t.command` in Finder or the command below for everyday launch.
Setup is not needed every day. From `macos/`:

```bash
bash dbdude-v2t.command
```

Keep the terminal open while using a terminal-based launcher. Quit from the app's
tray/menu bar menu before replacing files. Keep the complete project folder in
its setup location; launchers and environments depend on files there.

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

## Settings, logs, and backups

Personal settings and customizations are stored in `~/Library/Application Support/dbdude-v2t/`.
Back up this directory, including settings, mappings/rules and packs where present,
and any files you edited inside the project. Launch output is visible in Terminal and can contain dictated text.

Model caches may live outside the project under the backend's cache management;
replacing source files is not the same as clearing cached models. Review log
contents before sharing them: they may contain dictated text.

## Update safely

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

## Troubleshooting

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

These instructions were checked against the repository's current scripts and
paths. They are not a claim of a fresh installation test on this OS. Complete the
first-dictation test on your computer before relying on the installation.
