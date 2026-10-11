"""Test installer coordination with isolated home files and no network calls."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).with_name('install-plannotator.py')
SPEC = importlib.util.spec_from_file_location('plannotator_install', SCRIPT)
INSTALLER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INSTALLER)


class PlannotatorInstallTests(unittest.TestCase):
    def setUp(self):
        environment = patch.dict(INSTALLER.os.environ, {}, clear=True)
        environment.start()
        self.addCleanup(environment.stop)

    def test_installs_matching_tag_and_backs_up_local_skill_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / 'home'
            skill = home / '.agents/skills/plannotator/SKILL.md'
            skill.parent.mkdir(parents=True)
            skill.write_text('local skill changes')
            package = home / '.pi/agent/npm/node_modules/@plannotator/pi-extension/package.json'
            package.parent.mkdir(parents=True)
            package.write_text(json.dumps({'version': '0.27.24'}))
            tool = Path(directory) / 'mise-tool'
            with patch.object(INSTALLER.Path, 'home', return_value=home), \
                 patch('sys.argv', [str(SCRIPT), '0.27.24', str(tool)]), \
                 patch.object(INSTALLER.subprocess, 'check_output', return_value='plannotator 0.27.24\n'), \
                 patch.object(INSTALLER.subprocess, 'run') as run:
                INSTALLER.main()
            download, install, pi_install = [call.args[0] for call in run.call_args_list]
            self.assertEqual(pi_install, ['pi', 'install', 'npm:@plannotator/pi-extension@0.27.24',
                                         '--no-approve'])
            self.assertEqual(download[-1],
                             'https://raw.githubusercontent.com/backnotprop/plannotator/v0.27.24/scripts/install.sh')
            self.assertEqual(install[2:], ['--version', 'v0.27.24', '--non-interactive',
                                          '--no-minimal', '--verify-attestation'])
            backups = list((home / '.local/state/plannotator-install-backups').iterdir())
            self.assertEqual(len(backups), 1)
            self.assertEqual((backups[0] / '.agents/skills/plannotator/SKILL.md').read_text(),
                             'local skill changes')
            manifest = json.loads((backups[0] / 'manifest.json').read_text())
            self.assertIn({'path': '.agents/skills/plannotator', 'existed': True}, manifest)
            self.assertEqual(skill.read_text(), 'local skill changes')

    def test_mismatched_mise_binary_never_runs_installer(self):
        with patch('sys.argv', [str(SCRIPT), '0.27.24', '/fake/mise-tool']), \
             patch.object(INSTALLER.subprocess, 'check_output', return_value='plannotator 0.27.22\n'), \
             patch.object(INSTALLER.subprocess, 'run') as run:
            with self.assertRaisesRegex(SystemExit, 'Mise binary version mismatch'):
                INSTALLER.main()
            run.assert_not_called()

    def test_rejects_config_override_before_installer_side_effects(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / 'home'
            with patch.object(INSTALLER.Path, 'home', return_value=home), \
                 patch.dict(INSTALLER.os.environ, {'PI_CODING_AGENT_DIR': str(Path(directory) / 'other')}), \
                 patch('sys.argv', [str(SCRIPT), '0.27.24', '/fake/mise-tool']), \
                 patch.object(INSTALLER.subprocess, 'check_output', return_value='plannotator 0.27.24\n'), \
                 patch.object(INSTALLER.subprocess, 'run') as run:
                with self.assertRaisesRegex(SystemExit, 'Review PI_CODING_AGENT_DIR'):
                    INSTALLER.main()
            run.assert_not_called()
            self.assertFalse(home.exists())

    def test_mismatched_pi_extension_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            package = home / '.pi/agent/npm/node_modules/@plannotator/pi-extension/package.json'
            package.parent.mkdir(parents=True)
            package.write_text(json.dumps({'version': '0.27.22'}))
            with patch.object(INSTALLER.Path, 'home', return_value=home), \
                 patch('sys.argv', [str(SCRIPT), '0.27.24', '/fake/mise-tool']), \
                 patch.object(INSTALLER.subprocess, 'check_output', return_value='plannotator 0.27.24\n'), \
                 patch.object(INSTALLER.subprocess, 'run'):
                with self.assertRaisesRegex(SystemExit, 'Pi extension version mismatch'):
                    INSTALLER.main()

    def test_mismatched_installer_copy_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(INSTALLER.Path, 'home', return_value=Path(directory)), \
                 patch('sys.argv', [str(SCRIPT), '0.27.24', '/fake/mise-tool']), \
                 patch.object(INSTALLER.subprocess, 'check_output', side_effect=[
                     'plannotator 0.27.24\n', 'plannotator 0.27.22\n']), \
                 patch.object(INSTALLER.subprocess, 'run'):
                with self.assertRaisesRegex(SystemExit, 'Installer binary version mismatch'):
                    INSTALLER.main()


if __name__ == '__main__':
    unittest.main()
