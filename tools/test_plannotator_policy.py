"""Keep the installed extension pin across chezmoi applies, without live files."""
import json
from pathlib import Path
import subprocess
import unittest

SOURCE = Path(__file__).resolve().parents[1]


class PlannotatorPolicyTests(unittest.TestCase):
    def render(self, current):
        template = (SOURCE / 'private_dot_pi/private_agent/modify_settings.json').read_text()
        data = {'chezmoi': {'sourceDir': str(SOURCE), 'stdin': json.dumps(current)}}
        result = subprocess.check_output([
            'chezmoi', '--source', str(SOURCE), '--override-data', json.dumps(data),
            'execute-template', template], text=True)
        return json.loads(result)

    def test_preserves_installer_pin_and_managed_resource_filters(self):
        source = 'npm:@plannotator/pi-extension@0.28.12'
        for entry in [source, {'source': source, 'skills': ['old-filter']}]:
            with self.subTest(entry=entry):
                result = self.render({'packages': [entry], 'localPreference': 'keep'})
                self.assertEqual(result['packages'][0], {'source': source, 'skills': []})
                self.assertEqual(result['localPreference'], 'keep')
                self.assertEqual(self.render(result), result)

    def test_first_apply_leaves_release_selection_to_installer(self):
        result = self.render({'packages': ['npm:unrelated@1.2.3']})
        self.assertEqual(result['packages'][0]['source'], 'npm:@plannotator/pi-extension')


if __name__ == '__main__':
    unittest.main()
