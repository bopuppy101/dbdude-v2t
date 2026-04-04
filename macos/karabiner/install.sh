#!/usr/bin/env bash
# Install Karabiner-Elements rule: Remap Right Option → FN for DBDude V2T
set -e

KARABINER_CONFIG="$HOME/.config/karabiner/karabiner.json"

# Check if Karabiner-Elements is installed
if ! [ -d "/Applications/Karabiner-Elements.app" ]; then
    echo "Karabiner-Elements is not installed."
    read -p "Install it via Homebrew? [y/N] " answer
    if [[ "$answer" =~ ^[Yy]$ ]]; then
        brew install --cask karabiner-elements
        echo ""
        echo "Karabiner-Elements installed."
        echo "Please open it, grant Accessibility and Input Monitoring permissions,"
        echo "enable extensions in System Settings > General > Login Items & Extensions,"
        echo "then re-run this script."
        exit 0
    else
        echo "Aborted. Install Karabiner-Elements first:"
        echo "  brew install --cask karabiner-elements"
        exit 1
    fi
fi

# Check if config exists
if ! [ -f "$KARABINER_CONFIG" ]; then
    echo "Karabiner config not found at $KARABINER_CONFIG"
    echo "Open Karabiner-Elements once first to generate the default config, then re-run this script."
    exit 1
fi

# Check if rule already exists
if grep -q "Remap Right Option to FN" "$KARABINER_CONFIG" 2>/dev/null; then
    echo "Rule is already installed."
    exit 0
fi

# Add the rule to the config using python (available on macOS)
python3 -c "
import json, sys

with open('$KARABINER_CONFIG') as f:
    config = json.load(f)

rule = {
    'description': 'Remap Right Option to FN (for V2T trigger)',
    'manipulators': [{
        'type': 'basic',
        'from': {'key_code': 'right_option'},
        'to': [{'key_code': 'fn'}]
    }]
}

for profile in config.get('profiles', []):
    if profile.get('selected'):
        mods = profile.setdefault('complex_modifications', {})
        rules = mods.setdefault('rules', [])
        rules.append(rule)
        break

with open('$KARABINER_CONFIG', 'w') as f:
    json.dump(config, f, indent=4)
"

echo "Rule installed. Karabiner picks up the change automatically."
echo "Press Right Option to trigger V2T."
