# Voice2Text macOS - Installation Guide

## Download

Download `Voice2Text.dmg` from the releases page.

The DMG contains the complete application - no additional downloads required. The Whisper speech recognition model is bundled inside.

## Installation

1. **Open the DMG:**
   Double-click `Voice2Text.dmg` to mount it.

2. **Install the App:**
   Drag `Voice2Text.app` to your Applications folder.

3. **Eject the DMG:**
   Right-click the mounted volume and select "Eject" (or drag to Trash).

4. **First Launch:**
   - Right-click `Voice2Text.app` and select **Open**
   - Click **Open** in the security dialog
   - This is only required once (the app is not notarized)

## Required Permissions

Voice2Text needs two permissions to function:

### Accessibility (required for Fn key detection and text typing)
1. Go to **System Settings > Privacy & Security > Accessibility**
2. Click the **+** button
3. Navigate to Applications and select **Voice2Text**
4. Enable the toggle

### Microphone (required for voice recording)
- macOS will prompt automatically on first recording
- Click **Allow** when prompted

## Usage

1. Voice2Text appears as an icon in your menu bar
2. **Hold the Fn key** to record your voice
3. **Release Fn** to transcribe and type the text
4. Click the menu bar icon for settings and options

## Uninstall

1. Quit Voice2Text from the menu bar icon
2. Drag `Voice2Text.app` from Applications to Trash
3. (Optional) Remove settings:
   ```
   ~/Library/Application Support/Voice2Text
   ```

## Troubleshooting

### "Voice2Text is damaged and can't be opened"
Open Terminal and run:
```bash
xattr -cr /Applications/Voice2Text.app
```
Then try opening again.

### Fn key not responding
- Verify Accessibility permission is granted (see above)
- Try removing and re-adding Voice2Text in Accessibility settings
- Restart the app

### No audio / recording not working
- Check Microphone permission in System Settings > Privacy & Security > Microphone
- Open Configurator from the menu bar to verify the correct input device is selected

### App won't start
Run from Terminal to see error messages:
```bash
/Applications/Voice2Text.app/Contents/MacOS/voice2text-2026-macos
```

## System Requirements

- macOS 13 (Ventura) or later
- Apple Silicon (M1/M2/M3/M4) recommended for best performance
- Intel Macs supported but transcription will be slower
- ~500MB disk space (includes bundled Whisper model)
