# macOS Python environment and model setup

Installation documentation is maintained in two guides:

- [Beginner guide](../../docs/installation-macos-beginners.md) for prerequisites,
  setup, permissions, first dictation, everyday launch, and troubleshooting.
- [Technical guide](../../docs/installation-macos-technical.md) for commands and
  manual environment creation; see also [Python behavior](../../docs/installation-macos-technical.md#python-and-environment-behavior)
  and [model loading](../../docs/installation-macos-technical.md#models-and-download-timing).

The current setup script selects an installed Python 3.10+; it prefers versioned
commands from 3.14 down to 3.10, then tries `python3`. It is not pinned to Python
3.12. Existing `macos/venv` directories are reused. Requirements currently specify
`pyobjc-framework-Quartz>=12.0`; historical notes about older PyObjC versions do
not describe the current requirements.

Setup installs packages, not model weights. The default Whisper model is `small`
(English), loaded on first transcription from a local model directory if present,
otherwise through Hugging Face. Optional R2T2 requires the extra setup flag.

The main audio capture path uses AVAudioEngine; `sounddevice` remains for
Configurator device listing. See [AVAudioEngine implementation](av-audio-engine-implementation.md)
and [audio capture by platform](../../docs/audio-capture-library-per-platform.md).
