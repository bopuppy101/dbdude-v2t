# Windows: installation for beginners

This guide takes you from downloading dbdude-v2t to dictating your first sentence
on **Windows**, using the `windows/` folder. No programming experience is
required. Setup uses a terminal; everyday use has a launcher. All essential steps
are here. The optional [Windows technical guide](installation-windows-technical.md)
explains more about dependencies and script behavior.

## Before you start

Have an internet connection for package installation and the first model download,
a microphone, and several GB of free disk space. Larger models and optional GPU
packages need more space. Download time depends on your connection and choices;
there is no fixed installation time. Recognition runs locally once the selected
model is available.

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

## Download the project

1. Open the [project on GitHub](https://github.com/bopuppy101/dbdude-v2t).
2. Select the `develop` branch, then **Code → Download ZIP**.
3. Extract the ZIP completely. On Windows, use **Extract All**. Do not run files
   from inside the ZIP viewer.
4. Move the extracted folder to a permanent location you own, such as Documents.
   It may be called `dbdude-v2t-develop`. Keep the whole folder together; launchers
   depend on files beside them. Avoid moving it after setup.

No GitHub account or Git installation is needed for this download method.
If someone already cloned the repository for you, use that folder instead.

## Open the correct folder and run setup

In File Explorer, open the extracted project folder, click the address bar,
type `powershell`, and press Enter.

Start in the **project root**, where `README.md` is visible. The `cd windows`
command below enters the platform folder; do not repeat it if already there.

You do not need to create or activate a Python virtual environment. Setup creates
`windows/venv`, a private home for the app's packages. Keep this folder in place.
Setup reuses it on later runs; it does not rebuild it just because Python changed.

```powershell
cd windows
.\setup.ps1
```

If PowerShell reports that scripts cannot run, use this command in the same folder:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

This applies to that PowerShell invocation; it does not permanently change the
machine's execution policy. Managed computers may need help from their administrator.

Setup creates the app environment, installs packages, checks for NVIDIA tooling,
and creates a **dbdude-v2t desktop shortcut**. Check the output for installation
errors even if it prints **Setup Complete**. Double-click that shortcut to launch,
or open `windows` and double-click `dbdude-v2t.bat`.

The first launch loads/downloads the default model. Wait for it to finish. Look
for the tray icon, including in Windows' hidden-icons area. If recording fails,
check Windows microphone privacy settings and grant microphone permission for
desktop apps.
The repository already includes the `type_text.exe` helper used to type text;
keep it beside `dbdude-v2t.py`.

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

## Everyday launch

Use the desktop shortcut or `dbdude-v2t.bat` for everyday launch.
Setup is not needed every day. From `windows/`:

```powershell
.\dbdude-v2t.bat
```

Keep the terminal open while using a terminal-based launcher. Quit from the app's
tray/menu bar menu before replacing files. Keep the complete project folder in
its setup location; launchers and environments depend on files there.

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

## Settings, logs, and backups

Personal settings and customizations are stored in `%USERPROFILE%\.dbdude-v2t\`.
Back up this directory, including settings, mappings/rules and packs where present,
and any files you edited inside the project. Startup/error output is at `%USERPROFILE%\logs\v2t-error.log`. The app hides its
console on startup; use the tray console control when needed. Optional transcription
logs are in `%USERPROFILE%\logs\` and are disabled by default.

Model caches may live outside the project under the backend's cache management;
replacing source files is not the same as clearing cached models. Review log
contents before sharing them: they may contain dictated text.

## Update safely

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

## Troubleshooting

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

These instructions were checked against the repository's current scripts and
paths. They are not a claim of a fresh installation test on this OS. Complete the
first-dictation test on your computer before relying on the installation.
