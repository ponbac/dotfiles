"""Render the selected-key runtime migration without modifying live mise files."""
import json
from pathlib import Path
import subprocess
import tomllib
import unittest

SOURCE = Path(__file__).resolve().parents[1]
TEMPLATE = SOURCE / 'private_dot_config/mise/modify_private_config.toml'


class MiseRuntimePolicyTests(unittest.TestCase):
    def render(self, current):
        return subprocess.check_output([
            'chezmoi', '--source', str(SOURCE), '--override-data',
            json.dumps({'chezmoi': {'sourceDir': str(SOURCE), 'stdin': current}}),
            'execute-template', TEMPLATE.read_text(),
        ], text=True)

    def test_migrates_pins_preserving_unrelated_host_policy(self):
        for bun, dotnet in (
            ('"1.4.0"', '"10.0.203"'),
            ('{ version = "1.4.0", install_env = { LOCAL = "keep" } }',
             '{ version = "10.0.300", auto_update = false }'),
        ):
            with self.subTest(bun=bun, dotnet=dotnet):
                before = (f'[tools]\nbun = {bun}\ndotnet = {dotnet}\nnode = "24"\n'
                          '[settings]\ntrusted_config_paths = ["/host/project"]\n'
                          '[settings.tool_update]\nglobal_auto = false\n')
                after_text = self.render(before)
                after = tomllib.loads(after_text)
                original = tomllib.loads(before)
                for tool in ('bun', 'dotnet'):
                    self.assertEqual(after['tools'][tool]['version'], 'latest')
                    self.assertEqual(after['tools'][tool]['auto_update'], '24h')
                if isinstance(original['tools']['bun'], dict):
                    self.assertEqual(after['tools']['bun']['install_env'], {'LOCAL': 'keep'})
                self.assertEqual(after['tools']['node'], original['tools']['node'])
                self.assertEqual(after['settings'], original['settings'])
                self.assertEqual(self.render(after_text), after_text)

    def test_fresh_config_and_already_current_format(self):
        expected = {'version': 'latest', 'auto_update': '24h'}
        self.assertEqual(tomllib.loads(self.render('')),
                         {'tools': {'bun': expected, 'dotnet': expected}})
        current = ('# host comment\n[tools]\n'
                   'dotnet = {auto_update="24h", version="latest"}\n'
                   'bun = {version="latest", auto_update="24h"}\n')
        self.assertEqual(self.render(current), current)


if __name__ == '__main__':
    unittest.main()
