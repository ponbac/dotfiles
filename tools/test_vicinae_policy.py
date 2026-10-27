"""Check indexer policy and migration without touching live Vicinae settings."""
import json
from pathlib import Path
import subprocess
import unittest

SOURCE = Path(__file__).resolve().parents[1]
SETTINGS = '.config/vicinae/settings.json'
WORKAROUND = '.config/systemd/user/vicinae.service.d/no-file-indexer.conf'


class VicinaePolicyTests(unittest.TestCase):
    def chezmoi(self, host, *args, current=''):
        data = {'chezmoi': {'sourceDir': str(SOURCE), 'hostname': host,
                            'stdin': current}}
        return subprocess.check_output(
            ['chezmoi', '--source', str(SOURCE), '--override-data', json.dumps(data),
             *args], text=True)

    def test_managed_settings_replace_namespace_workaround_on_desktops_only(self):
        for host in ('omarchy', 'omarchy-laptop', 'dev-1', 'unknown-host'):
            with self.subTest(host=host):
                managed = self.chezmoi(host, 'managed', '--include=files').splitlines()
                self.assertFalse(WORKAROUND in managed,
                                 'The namespace workaround must no longer be managed')
                self.assertEqual(SETTINGS in managed,
                                 host in ('omarchy', 'omarchy-laptop'))
                retired = self.chezmoi(
                    host, 'execute-template', (SOURCE / '.chezmoiremove').read_text()
                ).splitlines()
                self.assertEqual(WORKAROUND in retired,
                                 host in ('omarchy', 'omarchy-laptop'))

    def test_policy_disables_indexing_without_overwriting_local_preferences(self):
        template = (SOURCE / 'private_dot_config/vicinae/modify_settings.json').read_text()
        before = {'theme': {'dark': {'name': 'local-theme'}},
                  'providers': {'files': {'enabled': True, 'preferences': {
                      'autoIndexing': True, 'indexingPaths': ['/home/local/Documents']}},
                                'applications': {'preferences': {'launchPrefix': 'local-launcher'}}}}
        current = '// Host-local Vicinae settings\n' + json.dumps(before)
        after_text = self.chezmoi('omarchy', 'execute-template', template, current=current)
        after = json.loads(after_text)
        self.assertIs(after['providers']['files']['preferences']['autoIndexing'], False)
        after['providers']['files']['preferences']['autoIndexing'] = True
        self.assertEqual(after, before)
        self.assertEqual(self.chezmoi('omarchy', 'execute-template', template,
                                     current=after_text), after_text)
        sparse = json.loads(self.chezmoi('omarchy', 'execute-template', template))
        self.assertEqual(sparse, {'providers': {'files': {'preferences': {
            'autoIndexing': False}}}})


if __name__ == '__main__':
    unittest.main()
