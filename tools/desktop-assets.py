#!/usr/bin/env python3
"""Verify/restore wallpaper assets and the pinned Ayaka checkout without overwrites."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def digest(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Create missing theme/assets only')
    parser.add_argument('--asset-dir', type=Path, default=Path.home() / 'dev/omarchy-wallpapers')
    args = parser.parse_args()
    host = os.uname().nodename
    if host not in ('omarchy', 'omarchy-laptop'):
        parser.error('Desktop assets are only for the two Omarchy hosts')
    source = Path(__file__).resolve().parents[1]
    lock = json.loads((source / '.chezmoitemplates/desktop/theme-lock.json').read_text())
    # Constants are locked here as well; do not silently follow a moving branch.
    url = 'https://github.com/ponbac/omarchy-ayaka-theme'
    revision = 'a2a4aec56fcbd06258464d73eacbe0ede12aa10c'
    if revision not in json.dumps(lock):
        raise SystemExit('Theme lock changed: review installer pin before continuing')
    assets = args.asset_dir.expanduser().resolve()
    manifest = json.loads((assets / 'manifest.json').read_text())
    home = Path.home()
    theme = home / '.config/omarchy/themes/ayaka'
    missing = []
    for relative, entry in manifest['hosts'][host].items():
        parts = Path(relative).parts
        if '..' in parts or Path(relative).is_absolute() or not (
            relative.startswith('.config/omarchy/backgrounds/') or
            (relative.startswith('.config/omarchy/themes/') and len(parts) > 4 and parts[4] == 'backgrounds')
        ):
            raise SystemExit('Unsafe asset destination')
        obj = assets / entry['object']
        if not obj.resolve().is_relative_to(assets / 'objects'):
            raise SystemExit('Unsafe asset object')
        if obj.stat().st_size != entry['bytes'] or digest(obj) != obj.stem:
            raise SystemExit('Asset checksum mismatch: ' + entry['object'])
        dest = home / relative
        if not dest.resolve().is_relative_to(home / '.config/omarchy'):
            raise SystemExit('Asset destination escapes Omarchy config')
        if dest.exists():
            if not dest.is_file() or digest(dest) != obj.stem:
                raise SystemExit('Refusing to overwrite locally changed asset: ' + relative)
        else:
            missing.append((obj, dest))
    new_theme = not theme.exists()
    if not new_theme:
        if not (theme / '.git').exists():
            raise SystemExit('Existing theme is not a Git checkout; refusing to replace it')
        current = subprocess.check_output(['git', '-C', str(theme), 'rev-parse', 'HEAD'], text=True).strip()
        if current != revision:
            raise SystemExit('Existing Ayaka revision differs; reconcile manually')
        print('Ayaka revision verified; local modifications preserved.')
    if args.apply:
        if new_theme:
            theme.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix='.ayaka-install-', dir=theme.parent) as tmp:
                checkout = Path(tmp) / 'theme'
                subprocess.run(['git', 'clone', '--no-checkout', url, str(checkout)], check=True)
                subprocess.run(['git', '-C', str(checkout), 'checkout', '--detach', revision], check=True)
                # Restore intentional absences only inside a NEW checkout.
                for relative in manifest.get('absent', {}).get(host, []):
                    rel = Path(relative).relative_to('.config/omarchy/themes/ayaka')
                    if '..' in rel.parts or not str(rel).startswith('backgrounds/'):
                        raise SystemExit('Unsafe theme absence entry')
                    (checkout / rel).unlink(missing_ok=True)
                checkout.rename(theme)
        for obj, dest in missing:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                if digest(dest) != obj.stem:
                    raise SystemExit('New checkout asset differs: ' + str(dest))
            else:
                shutil.copyfile(obj, dest)
        print(f'Assets verified/restored for {host}; theme/background selection unchanged.')
    else:
        print(f'{len(manifest["hosts"][host])} mappings checked; {len(missing)} missing; theme missing: {new_theme}')
        if missing or new_theme:
            print('Use --apply to create missing files. Existing differing files are never overwritten.')


if __name__ == '__main__':
    main()
