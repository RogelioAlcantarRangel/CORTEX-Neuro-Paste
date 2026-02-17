import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.append(os.path.dirname(__file__))

import config as cfg


class BackendConfigTests(unittest.TestCase):
    def setUp(self):
        self._original_path = cfg.CONFIG_PATH

    def tearDown(self):
        cfg.CONFIG_PATH = self._original_path

    def test_defaults_when_missing_file(self):
        cfg.CONFIG_PATH = Path('/tmp/non-existent-cortex-config.json')
        loaded = cfg.load_config()
        self.assertEqual(loaded['ws_host'], 'localhost')
        self.assertEqual(loaded['ws_port'], 8989)
        self.assertEqual(loaded['transform_rules'], ['uppercase'])
        self.assertEqual(loaded['log_level'], 'INFO')
        self.assertEqual(loaded['log_file'], 'backend/backend.log')

    def test_valid_file_is_loaded(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'config.json'
            path.write_text(
                json.dumps(
                    {
                        'ws_host': '0.0.0.0',
                        'ws_port': 9001,
                        'transform_rules': ['trim', 'uppercase'],
                        'log_level': 'debug',
                        'log_file': 'logs/cortex.log',
                    }
                ),
                encoding='utf-8',
            )
            cfg.CONFIG_PATH = path
            loaded = cfg.load_config()
            self.assertEqual(loaded['ws_host'], '0.0.0.0')
            self.assertEqual(loaded['ws_port'], 9001)
            self.assertEqual(loaded['transform_rules'], ['trim', 'uppercase'])
            self.assertEqual(loaded['log_level'], 'DEBUG')
            self.assertEqual(loaded['log_file'], 'logs/cortex.log')

    def test_invalid_values_fallback_to_defaults(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'config.json'
            path.write_text(
                json.dumps(
                    {
                        'ws_host': '',
                        'ws_port': -10,
                        'transform_rules': ['   ', 1],
                        'log_level': 'verbose',
                        'log_file': '   ',
                    }
                ),
                encoding='utf-8',
            )
            cfg.CONFIG_PATH = path
            loaded = cfg.load_config()
            self.assertEqual(loaded['ws_host'], 'localhost')
            self.assertEqual(loaded['ws_port'], 8989)
            self.assertEqual(loaded['transform_rules'], ['uppercase'])
            self.assertEqual(loaded['log_level'], 'INFO')
            self.assertEqual(loaded['log_file'], 'backend/backend.log')


if __name__ == '__main__':
    unittest.main()
