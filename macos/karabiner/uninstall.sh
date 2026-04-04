#!/usr/bin/env bash
# Uninstall Karabiner-Elements rule: Remap Right Option → FN for DBDude V2T
set -e

KARABINER_CONFIG="$HOME/.config/karabiner/karabiner.json"

if ! [ -f "$KARABINER_CONFIG" ]; then
    echo "Karabiner config not found. Nothing to uninstall."
    exit 0
fi

if ! grep -q "Remap Right Option to FN" "$KARABINER_CONFIG" 2>/dev/null; then
    echo "Rule not found in config. Nothing to uninstall."
    exit 0
fi

# Remove the rule from the config using python
python3 -c "
import json

with open('$KARABINER_CONFIG') as f:
    config = json.load(f)

for profile in config.get('profiles', []):
    if profile.get('selected'):
        mods = profile.get('complex_modifications', {})
        rules = mods.get('rules', [])
        mods['rules'] = [r for r in rules if 'Remap Right Option to FN' not in r.get('description', '')]
        if not mods['rules']:
            del profile['complex_modifications']
        break

with open('$KARABINER_CONFIG', 'w') as f:
    json.dump(config, f, indent=4)
"

echo "Rule removed. Right Option is back to normal."
