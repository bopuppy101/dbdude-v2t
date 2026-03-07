# Apple Developer Signing & Notarization Guide

## Prerequisites

1. Apple Developer Program membership ($99/year)
2. Xcode installed (for command-line tools)
3. Apple ID signed into Xcode

## Step 1: Create Certificates

1. Go to [Apple Developer Portal](https://developer.apple.com/account)
2. Navigate to **Certificates, Identifiers & Profiles**
3. Create a **Developer ID Application** certificate
4. Download and double-click to install in Keychain

## Step 2: Create App-Specific Password

1. Go to [Apple ID](https://appleid.apple.com)
2. Sign in → **App-Specific Passwords** → Generate
3. Name it "Voice2Text Notarization"
4. Save the password securely

## Step 3: Store Credentials

```bash
# Store notarization credentials in Keychain
xcrun notarytool store-credentials "Voice2Text-Notarize" \
    --apple-id "your-apple-id@email.com" \
    --team-id "YOUR_TEAM_ID" \
    --password "app-specific-password"
```

Find your Team ID in the Developer Portal under Membership.

## Step 4: Update build.sh

Replace the ad-hoc signing line with:

```bash
# Sign with Developer ID (replace TEAM_ID with yours)
codesign --force --deep --options runtime \
    --sign "Developer ID Application: Your Name (TEAM_ID)" \
    dist/Voice2Text.app
```

Add notarization after DMG creation:

```bash
# Notarize the DMG
echo "Notarizing DMG..."
xcrun notarytool submit dist/Voice2Text.dmg \
    --keychain-profile "Voice2Text-Notarize" \
    --wait

# Staple the notarization ticket
echo "Stapling notarization ticket..."
xcrun stapler staple dist/Voice2Text.dmg
```

## Step 5: Full Updated build.sh Signing Section

```bash
# Copy models manually
echo "Copying Whisper model to app bundle..."
cp -R models dist/Voice2Text.app/Contents/Resources/

# Move mlx_whisper assets to Resources and create symlink
echo "Moving mlx_whisper assets to Resources..."
mkdir -p dist/Voice2Text.app/Contents/Resources/mlx_whisper_assets
mv dist/Voice2Text.app/Contents/MacOS/mlx_whisper/assets/* dist/Voice2Text.app/Contents/Resources/mlx_whisper_assets/
rm -rf dist/Voice2Text.app/Contents/MacOS/mlx_whisper/assets
ln -s ../../Resources/mlx_whisper_assets dist/Voice2Text.app/Contents/MacOS/mlx_whisper/assets

# Remove extended attributes
echo "Removing quarantine/provenance attributes..."
xattr -cr dist/Voice2Text.app

# Sign with Developer ID
echo "Code signing app with Developer ID..."
codesign --force --deep --options runtime \
    --sign "Developer ID Application: Your Name (TEAM_ID)" \
    dist/Voice2Text.app

# Verify signature
codesign --verify --deep --strict dist/Voice2Text.app

# Create DMG installer
echo "Creating DMG installer..."
hdiutil create -volname "Voice2Text" \
    -srcfolder dist/Voice2Text.app \
    -ov -format UDZO \
    dist/Voice2Text.dmg

# Notarize
echo "Submitting for notarization (this may take a few minutes)..."
xcrun notarytool submit dist/Voice2Text.dmg \
    --keychain-profile "Voice2Text-Notarize" \
    --wait

# Staple
echo "Stapling notarization ticket..."
xcrun stapler staple dist/Voice2Text.dmg

echo "Build complete! DMG is signed and notarized."
```

## Verification

After building, verify everything works:

```bash
# Check signature
codesign -dv --verbose=4 dist/Voice2Text.app

# Check notarization
spctl --assess --type execute dist/Voice2Text.app
# Should output: "dist/Voice2Text.app: accepted"

# Check DMG
spctl --assess --type open --context context:primary-signature dist/Voice2Text.dmg
```

## Troubleshooting

### "Developer ID Application certificate not found"
- Ensure certificate is installed in Keychain
- Run `security find-identity -v -p codesigning` to list available certificates

### Notarization fails
- Check email from Apple for specific errors
- Common issues: hardened runtime missing, unsigned nested code
- Add `--options runtime` to codesign command

### "The signature is invalid"
- Ensure codesign runs AFTER all files are in place
- Check for unsigned nested binaries with:
  ```bash
  codesign --verify --deep --strict dist/Voice2Text.app 2>&1
  ```

## Timeline

- Certificate creation: ~10 minutes
- First build with signing: ~20 minutes
- Notarization: 2-10 minutes (Apple's servers)

## Cost

- Apple Developer Program: $99/year
- Includes: Developer ID, App Store distribution, TestFlight, beta access
