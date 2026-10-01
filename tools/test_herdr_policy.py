"""Check entry-scoped hook ownership without modifying live agent configs."""
import json
from pathlib import Path
import subprocess
import unittest

SOURCE = Path(__file__).resolve().parents[1]


class HerdrPolicyTests(unittest.TestCase):
    def render(self, current):
        template = (SOURCE / 'private_dot_codex/modify_hooks.json').read_text()
        data = {'chezmoi': {'sourceDir': str(SOURCE), 'stdin': json.dumps(current),
                            'homeDir': '/home/test'}}
        result = subprocess.check_output(
            ['chezmoi', '--source', str(SOURCE), '--override-data', json.dumps(data),
             'execute-template', template], text=True)
        return json.loads(result)

    def test_plannotator_reconciliation_preserves_other_hooks(self):
        herdr = {'hooks': [{'type': 'command', 'command': 'herdr-session'}]}
        other = {'type': 'command', 'command': 'other-stop', 'timeout': 20}
        before = {'custom': True, 'hooks': {
            'SessionStart': [herdr],
            'Stop': [{'matcher': '*', 'custom': 'keep', 'hooks': [other, {
                'type': 'command', 'command': '/home/test/.local/bin/plannotator',
                'timeout': 1}]}],
        }}
        after = self.render(before)
        self.assertIs(after['custom'], True)
        self.assertEqual(after['hooks']['SessionStart'], [herdr])
        self.assertEqual(after['hooks']['Stop'][0], {
            'matcher': '*', 'custom': 'keep', 'hooks': [other]})
        self.assertEqual(after['hooks']['Stop'][1], {'hooks': [{
            'type': 'command', 'command': '/home/test/.local/bin/plannotator',
            'timeout': 345600}]})
        self.assertEqual(self.render(after), after)
        self.assertEqual(self.render({})['hooks']['Stop'], [after['hooks']['Stop'][1]])


if __name__ == '__main__':
    unittest.main()
