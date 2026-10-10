# Installation experience review

Date: October 3, 2026

## Assessment

The repository has useful setup scripts, but its documented installation experience assumes a technical user. The scripts already create Python virtual environments and install dependencies; beginners should not need to understand or manage those details. Documentation can improve the current source-installation experience immediately. A normal download-and-open experience requires packaging and installer engineering as well.

The recommended direction is two clear audiences: an approachable installation and everyday-use guide, and a separate technical setup and maintenance reference. The beginner path should lead to a successful first dictation, including permissions and speech-model preparation, before introducing advanced choices.

## Review scope and repository state

This is a static review of documentation, setup scripts, launchers, requirements, and relevant application code. No setup scripts, installers, application tests, model downloads, or dependency installations were run. Platform behavior described below is what the inspected implementation intends to do; it is not certification that installation succeeds on a fresh machine.

The initial inspection was on `m5.local`, in `/Users/mike/git/dbdude-v2t`, on branch `codex/macos-sleep-wake`, at commit `474a44a444d8b1140731bccd4a858d418fd3e051` ("Keep Ubuntu 26.04 CPU mode and desktop typing service setup"). There were three modified tracked files and thirteen untracked files. No upstream was shown for that branch. The requested safe pull was skipped, not attempted, because the checkout was dirty. No fetch, stash, reset, merge, commit, or push was performed by the reviewer.

After the user reported pushing the branch, a fresh check showed a clean checkout at `4573ec39e012a718a9a842b74c33520896a84cd2` ("Handles sleep wake"), tracking `origin/codex/macos-sleep-wake`. A read-only GitHub branch query independently confirmed that remote branch points to the same commit. The latest commit includes the previously reviewed macOS changes and related files. This verifies the branch was pushed; it does not establish code quality or successful installation testing. Creating this document adds one untracked documentation file after that clean-state check.

The user identifies `develop` as their normal working and intended integration branch, and describes merging this branch into `develop` as a future step. No branch switch or merge was performed. The branch is intended to make the application recover seamlessly across monitor sleep, computer sleep, and related power states. The user reports believing they already tested this successfully on this M5; that is user-reported testing, with uncertainty preserved, not independently reproduced testing or cross-platform validation.

Origin is `git@github.com:bopuppy101/dbdude-v2t.git`. Authorized GitHub metadata reads confirmed public visibility and `develop` as the default branch. The GitHub releases collection was empty at review time. The later branch query showed remote `develop` at `211d53b0b717a24318337115ff975025378018da`; its contents were not reviewed. This assessment concerns the named local branch, not an assertion that the default branch has identical contents. No applicable `AGENTS.md` or checkout `.agents/skills` instructions were found.

The website linked by the README could not be accessed through the web-reading tool. Whether it distributes installers separately remains unverified.

## Current installation paths

| Platform | Mechanism present in this checkout | Main limitations for beginners |
| --- | --- | --- |
| macOS / Apple Silicon | Bash setup finds Python, creates a venv, installs dependencies, sets a launcher icon, and checks the Globe/Fn setting. A `.command` file launches the app. Transcription uses MLX. | Python must already be installed. Terminal is required for setup. Permissions and keyboard configuration are not presented as a complete first-run walkthrough. No Intel-specific path or architecture preflight was found. |
| Windows | PowerShell setup creates a venv, installs dependencies, optionally installs CUDA packages, and creates a desktop shortcut. A `.bat` file launches the app; a compiled AutoHotkey typing helper is included. | Requires Python on PATH and understanding where to run PowerShell. Execution-policy errors are possible. Python's version is printed rather than checked against the stated minimum. |
| Ubuntu / X11-oriented path | `apt` installs system dependencies; Bash creates a venv. `xdotool` types text. The launcher runs the application through sudo. | Privilege prompts, manual desktop-file path changes, and assumptions about the graphical session. This is not a general Wayland path. |
| Ubuntu 26.04 / Wayland-oriented path | A separate folder uses `ydotool`, udev input-access rules, and a systemd user service. The application runs as the desktop user. | Omitted from the main installation guide. Requires system configuration during setup. The launcher explicitly forces CPU mode even though setup may install CUDA packages. |
| Other Linux distributions | No dedicated installation path was found for Debian/Mint, Fedora, Arch, or openSUSE. | These should remain unverified until packages, Python dependencies, desktop integration, input access, and service behavior are tested. |

Sources: [main README](../README.md), [macOS setup](../macos/setup.bash), [macOS launcher](../macos/dbdude-v2t.command), [Windows setup](../windows/setup.ps1), [Windows launcher](../windows/dbdude-v2t.bat), [Ubuntu setup](../ubuntu/setup.bash), [Ubuntu launcher](../ubuntu/run-dbdude-v2t.bash), [Ubuntu 26.04 setup](../ubuntu-26.04/setup.bash), and [Ubuntu 26.04 launcher](../ubuntu-26.04/run-dbdude-v2t.bash).

The table describes available code paths, not a validated support matrix. Minimum OS versions, processor architectures, memory requirements, and supported desktop environments need explicit verification before publication.

## Documentation inconsistencies and beginner friction

### Obtaining and launching the application

The [main README](../README.md) begins installation with Python version checks and commands such as `cd windows` or `cd macos`. It assumes the reader already has the repository and understands directories and shells. A complete guide should explain where to obtain a specific release, where to extract or install it, which file to open, what success looks like, and how to launch it again tomorrow.

The [macOS README](../macos/README.md) contains only a setup command. The Windows setup script creates a desktop shortcut, a useful capability that should be the primary launch instruction. Linux desktop entries still contain `CHANGE_THIS_PATH` placeholders: [Ubuntu desktop entry](../ubuntu/dbdude-v2t.desktop) and [26.04 desktop entry](../ubuntu-26.04/dbdude-v2t.desktop).

The macOS launcher checks for a venv, then force-kills matching `dbdude-v2t.py` processes before launching. That is an implementation behavior worth revisiting for a polished launcher; a beginner should not need to know how to manage processes.

### Python and virtual environments

Creating and activating a venv is already automated by setup and launch scripts. Beginner instructions can describe this as installing the application's private runtime and dependencies, with technical details moved to the technical guide. However, documentation cannot hide the existing requirement to install Python first. Eliminating that requirement needs a packaged runtime or an installer that manages it.

The [macOS Python/model guide](../macos/docs/macos-model-and-python-venv-setup.md) says builds are pinned to Python 3.12 and discusses PyObjC compatibility history. Actual [setup](../macos/setup.bash) searches 3.14, 3.13, 3.12, 3.11, and 3.10 in that order, while [requirements](../macos/requirements.txt) specify `pyobjc-framework-Quartz>=12.0`. This is an internal documentation/implementation mismatch; the historical upstream compatibility claims were not independently revalidated. The guide also refers to private "Claude memory," which is not a usable public prerequisite or explanation.

The broad "Python 3.10 or later" statement is not a tested compatibility matrix. Most dependency versions are unpinned or only lower-bounded, while Windows constrains PySide6 to a narrower range. Choose and test runtime/dependency combinations, then keep setup, packaging, and documentation aligned. The scripts reuse an existing venv without a documented repair or migration process.

Sources: [Windows requirements](../windows/requirements.txt), [Ubuntu requirements](../ubuntu/requirements.txt), and [26.04 requirements](../ubuntu-26.04/requirements.txt).

### macOS permissions and first use

Explain Microphone and Accessibility permissions with screenshots and the actual application/process name the user will see for each supported launch method. Explain why each is needed and how to recover if permission was denied. Include the required Globe/Fn setting in the main first-run flow, rather than expecting discovery of a separate technical note.

The existing [Fn setup guide](macos-fn-key-setup.md) provides a useful starting point. The [quarantine note](../macos/docs/xattr-cr-fix-to-remove-quarantine-flag-to-allow-script-to-run-exe.md) is only a fragment, not an approachable distribution or troubleshooting guide. A packaged release should have a deliberate signing/notarization and first-launch experience rather than making command-line quarantine handling the normal path.

## Transcription models: actual behavior and proposed explanation

The README says installation downloads a Hugging Face Whisper model. The setup scripts install Python packages but do not explicitly download model weights. Actual behavior is:

| Platform | Current default | When model loading/download is triggered | Local model lookup |
| --- | --- | --- | --- |
| macOS | `small`, English | On the first transcription using the selected model | `models/whisper-<model>.en-mlx` for English, or `models/whisper-<model>-mlx` otherwise, under the script directory or bundled Resources directory |
| Windows | `base`, English | During voice-to-text startup/model initialization | `models/faster-whisper-<model>` under the application directory |
| Ubuntu and Ubuntu 26.04 | `base` | During application startup | `models/faster-whisper-<model>` beside the application script |

If the local directory is absent, the application calls the relevant library with a model identifier; downloading and cached reuse are delegated to that library. The repository does not explicitly configure a shared model-cache location or expose a model-management workflow. Do not present a guessed cache location as an application guarantee; verify actual locations and environment overrides for each supported package.

Sources: [macOS runtime: `get_model_name` and `transcription_worker`](../macos/dbdude-v2t.py), [macOS configurator](../macos/configurator_gui.py), [Windows runtime: `run_voice2text` and `try_load_model`](../windows/dbdude-v2t.py), [Ubuntu runtime](../ubuntu/dbdude-v2t.py), and [26.04 runtime](../ubuntu-26.04/dbdude-v2t.py).

A beginner explanation could say: "The speech model is a set of recognition files stored on your computer. If your installer does not include it, the app downloads it before it can transcribe. Once those files are available, transcription runs locally." Explain that changing models may require another download, and distinguish initial downloading from later model loading/warm-up. Give measured download size, disk use, and hardware guidance for tested choices.

Important caveats:

- macOS constructs an English `.en` repository name for every selectable model size. Validate each advertised size/language mapping instead of assuming all constructed identifiers exist. Use an explicit verified model catalog in a future implementation.
- Windows attempts to fall back to `base` if another model fails, but a source checkout does not itself guarantee a bundled base model. The comment saying it is always available with an installer is not evidence for source installs.
- Ubuntu exits when model loading fails. Windows reports a model-loading error; macOS loads inside its transcription worker. These need understandable download/network/disk/model-error states.
- Linux saves a language setting but the inspected transcription call passes `language=None`. macOS uses language to choose English-only versus multilingual model identifiers. Do not imply identical language-setting behavior across platforms.
- Defaults differ for a reason worth explaining, but no hardware benchmark was performed in this review.

Recommended initial defaults, pending validation, are the existing `small` English model on Apple Silicon and `base` on Windows/Linux. Present these as "Recommended," use the system microphone, and keep transcription logging off. Offer larger models under advanced choices with measured speed/accuracy/resource tradeoffs. For other languages, provide a verified multilingual path.

CPU mode should remain a usable supported path. Treat GPU acceleration as optional and test failure handling. The 26.04 launcher's forced CPU choice is explicitly justified in comments by a particular machine's competing model-server VRAM needs; it should be a documented setting or policy rather than a surprising universal default.

## Packaging, releases, and distribution

[Windows help](../windows/help/help.html) instructs users to run `v2t-setup-2026.exe`, describes a Program Files installation, and says the base model is included. The checkout contains bundled-app detection for macOS and Nuitka/PyInstaller-style paths on Windows, but no corresponding installer/build configurations were found. GitHub had no published releases when checked. These observations do not prove that no installer exists elsewhere; the website distribution path remains unverified.

Before directing beginners to an installer, establish its authoritative download location, version, platform/architecture, included runtime, included model, update behavior, and build provenance. Keep source setup and packaged-install instructions separate. For maintainers, add reproducible packaging configuration and a release checklist, with fresh-machine validation rather than relying on a developer's existing environment.

Potential engineering deliverables include a macOS application distributed through an appropriate signed/notarized package, a Windows installer with a private runtime and the required typing helper, and tested Linux installation packages or a guided bootstrapper. Selecting a Linux package format alone does not solve global hotkeys, text injection, audio sessions, or input-device permissions.

## Linux distribution and desktop-session distinctions

The [26.04 migration document](../ubuntu-26.04/docs/wayland-input-migration.md) still describes forwarding variables through sudo and using XWayland-related settings. The actual launcher now runs as the desktop user with native Wayland selected. Documentation should follow the implementation and explicitly distinguish distro release, desktop environment, and X11/Wayland session.

The 26.04 setup creates `/etc/udev/rules.d/70-uinput-uaccess.rules` and `/etc/udev/rules.d/70-input-uaccess.rules`, writes a user-service override at `~/.config/systemd/user/ydotool.service.d/retry.conf`, and enables/starts `ydotool.service`. Explain these changes and their purpose. Setup still needs administrative authorization even though the application runs without sudo afterward.

Build a support matrix before promising broad Linux compatibility:

- Ubuntu: distinguish the existing X11 and 26.04 Wayland implementations and test each supported release/session.
- Debian and Mint: verify package names/versions and session behavior; do not assume an Ubuntu script is automatically supported.
- Fedora: verify dependencies, service packaging, input permissions, and desktop integration.
- Arch: validate the same components against its package/runtime versions.
- openSUSE: provide a separately verified dependency and desktop-service path.

Record tested versions and known limitations. Prefer one maintained Linux implementation with narrowly scoped platform setup differences if engineering work permits; the current duplicated folders increase the chance of documentation and behavior drifting apart.

## Updates, uninstall, and troubleshooting

No consolidated application update, rollback, uninstall, model-cache cleanup, or backup guide was found. "Restart after updating Python code" is not a complete user update process.

Document where settings, custom mappings, model files, and logs live, and which are preserved during updates or optional removal. Windows and Linux use `~/.dbdude-v2t` for settings; macOS uses `~/Library/Application Support/dbdude-v2t`. The [macOS file-location guide](../macos/docs/macos-file-locations.md) is a start but does not cover the full lifecycle. Model caches need separate verification, especially where the older Ubuntu launcher runs as root.

A 26.04 uninstall must account for the udev rules and user-service override as well as the app folder and desktop launcher. Design ownership-aware cleanup so removing this application does not disrupt another use of a shared typing service or delete unrelated model caches. Explain what is removed and what remains.

Beginner troubleshooting should use symptoms and observable checkpoints:

| Symptom | Information the guide should help the user check |
| --- | --- |
| Setup will not start | Correct download/folder, supported system, Python prerequisite for source installs, PowerShell policy where applicable |
| App appears stuck on first use | Model download versus loading, internet access, available disk space, progress and retry status |
| No recording indicator | Correct hotkey, Fn setting on macOS, required permissions, Linux input access |
| Recording starts but no text appears | Microphone selection/input level, model errors, transcription status |
| Transcript exists but is not typed | Focused window, macOS Accessibility, Windows typing helper, X11/Wayland path or ydotool service/socket |
| App fails after dependency changes | Tested runtime versions and a documented repair/reinstall process |
| App fails after sleep or device changes | Platform-specific recovery steps and relevant diagnostics, with tested behavior distinguished from implementation intent |

Existing Windows help has basic symptom advice but describes slow model startup only as GPU warm-up. Expand this to cover downloading, CPU loading, and failures. A future installer/application should surface these states without requiring users to interpret terminal output.

## Phased recommendations

### Phase 1: documentation-only improvements

Make the README an entry page with two routes: "Install and use" and "Technical setup." Keep the beginner path accurate about the current need for source files and Python until packaged releases are verified.

For each currently supported path, write an end-to-end guide: choose the correct platform/version, obtain files, install prerequisites, run setup, grant permissions, prepare the recommended model, dictate one short sentence into a simple text editor, quit, and launch again. Include screenshots and expected success messages. Add model-download expectations, update/uninstall instructions, and symptom-based troubleshooting. Resolve the Python, model-download, installer, and Linux documentation contradictions above.

### Phase 2: installer and application engineering

Hide Python and venv management behind a tested private runtime. Add compatibility checks, normal launch integration, understandable error reporting, and a repair path. Implement model selection with verified identifiers, download progress, disk-space checks, retry/cancel behavior, and a clear ready state before first dictation. Generate Linux desktop files automatically and manage required system changes explicitly. Add update/uninstall mechanisms that preserve user data by default and make optional cleanup clear.

Publish verified release artifacts and test them on fresh machines or clean environments. Cover first run, offline use after model preparation, model change, denied permissions, restart, update, uninstall, and relevant sleep/device transitions. These are future validation recommendations; they were not executed during this review.

### Phase 3: technical reference and broader support

Maintain a separate technical reference for supported Python/dependency versions, manual venv setup, package requirements, model catalog/cache behavior, CPU/CUDA/MLX choices, configuration paths, Linux input/service architecture, diagnostics, packaging, and release procedures. Remove dependence on private notes.

Expand Linux coverage through tested distro/session combinations, publish the resulting support matrix, and keep an explicit distinction between supported, experimental, and unverified paths. Keep beginners on a recommended path while making the implementation details available to maintainers and advanced users.

## Remaining evidence gaps

Fresh-machine installation, dependency compatibility, performance/resource measurements, every model/language mapping, packaged installer availability on the website, and broad Linux distribution support remain unverified. The pushed commit and clean checkout establish repository state only. This document is an assessment and proposal, not a claim that those engineering or validation tasks have been completed.
