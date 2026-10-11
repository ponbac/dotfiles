"""Reconcile installer-owned releases without network calls or live settings."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).with_name('reconcile-pi-packages.py')
SPEC = importlib.util.spec_from_file_location('pi_reconciliation', SCRIPT)
RECONCILER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RECONCILER)


class PiReconciliationTests(unittest.TestCase):
    def setUp(self):
        environment = patch.dict(RECONCILER.os.environ, {}, clear=True)
        environment.start()
        self.addCleanup(environment.stop)

    def test_uses_current_installer_release_instead_of_stale_settings_pin(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            settings = home / '.pi/agent/settings.json'
            settings.parent.mkdir(parents=True)
            settings.write_text(json.dumps({'packages': [
                {'source': 'npm:@plannotator/pi-extension@0.27.25', 'skills': []},
                'npm:pi-web-access@0.33.0',
            ]}))
            for name, version in [('@plannotator/pi-extension', '0.28.12'), ('pi-web-access', '0.33.0')]:
                package = home / '.pi/agent/npm/node_modules' / name / 'package.json'
                package.parent.mkdir(parents=True)
                package.write_text(json.dumps({'version': version}))
            with patch.object(RECONCILER.Path, 'home', return_value=home), \
                 patch.object(RECONCILER.subprocess, 'check_output', return_value='plannotator 0.28.12\n') as version, \
                 patch.object(RECONCILER.subprocess, 'run') as install:
                RECONCILER.main()
            version.assert_called_once_with([str(home / '.local/bin/plannotator'), '--version'], text=True)
            install.assert_called_once_with([
                'pi', 'install', 'npm:@plannotator/pi-extension@0.28.12', '--no-approve'], check=True)


if __name__ == '__main__':
    unittest.main()
