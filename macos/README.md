# dbdude-v2t / macOS

Local voice-to-text for Apple Silicon Macs. See the [main README](../README.md)
for features and supported platforms.

## Installation

- [Beginner installation guide](../docs/installation-macos-beginners.md): Python,
  setup, permissions, launch, and your first transcription.
- [Technical installation guide](../docs/installation-macos-technical.md):
  interpreter selection, environments, models, updates, and diagnostics.

From this `macos` folder, with a compatible Python 3.10+ installed:

```bash
bash setup.bash
bash dbdude-v2t.command
```

Setup creates the virtual environment automatically. The default `small` model
loads/downloads on the first transcription, not during setup. Grant Microphone
and Accessibility permissions and set Globe/Fn to Do Nothing as described in the
[Fn key guide](../docs/macos-fn-key-setup.md).
