"""Deployment preview regression using real chezmoi and an isolated home.

Run: python3 -B -m unittest discover -s tools -p 'test_deploy.py' -v
"""
import contextlib
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import deploy


class DeploymentPreviewTests(unittest.TestCase):
    def test_preview_accepts_local_drift_without_writing_targets(self):
        chezmoi = shutil.which('chezmoi')
        self.assertIsNotNone(chezmoi, 'This integration test requires chezmoi')
        with tempfile.TemporaryDirectory(prefix='deploy-preview-test-') as temp:
            root = Path(temp)
            home = root / 'home'
            home.mkdir()
            source = root / 'source'
            source.mkdir()
            target = home / '.example'
            managed = source / 'dot_example'
            managed.write_text('original\n')
            config = root / 'chezmoi.toml'
            config.write_text('')
            state = root / 'state.boltdb'
            isolated_args = [
                '--config', str(config), '--destination', str(home),
                '--persistent-state', str(state),
            ]
            env = {
                'PATH': os.defpath, 'HOME': str(home),
                'XDG_CONFIG_HOME': str(home / '.config'),
                'XDG_CACHE_HOME': str(home / '.cache'),
                'XDG_STATE_HOME': str(home / '.local/state'),
            }
            subprocess.run(
                [chezmoi, *isolated_args, '--source', str(source), 'apply', '--force'],
                env=env, check=True, capture_output=True, timeout=20,
            )
            target.write_text('local edits to preserve\n')
            managed.write_text('incoming configuration\n')
            state_before = state.read_bytes()

            # Capture the Python payload at the host transport boundary, then
            # execute it against real chezmoi with isolated config/state/targets.
            requests = []
            with patch.object(deploy, 'SOURCE', source), \
                    patch.object(deploy, 'run_host', side_effect=lambda *a, **kw: requests.append((a, kw))), \
                    patch.object(deploy.subprocess, 'run'), \
                    patch.object(sys, 'argv', ['deploy.py', 'omarchy-laptop']), \
                    contextlib.redirect_stdout(io.StringIO()):
                deploy.main()
            (_, argv), kwargs = requests[-1]
            self.assertEqual(argv[-1], 'no')
            payload = kwargs['input']
            bin_dir = root / 'bin'
            bin_dir.mkdir()
            wrapper = bin_dir / 'chezmoi'
            wrapper.write_text(
                f'#!{sys.executable}\n'
                'import os, sys\n'
                f'os.execv({chezmoi!r}, {[chezmoi, *isolated_args]!r} + sys.argv[1:])\n'
            )
            wrapper.chmod(0o755)
            env['PATH'] = str(bin_dir) + os.pathsep + os.defpath
            result = subprocess.run(
                [sys.executable, '-', str(source), 'no'], input=payload,
                env=env, capture_output=True, text=True, timeout=20,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('.example', result.stdout)
            self.assertEqual(target.read_text(), 'local edits to preserve\n')
            self.assertEqual(managed.read_text(), 'incoming configuration\n')
            self.assertEqual(state.read_bytes(), state_before)
            self.assertFalse((home / '.local/state/chezmoi-deploy-backups').exists())


if __name__ == '__main__':
    unittest.main()
