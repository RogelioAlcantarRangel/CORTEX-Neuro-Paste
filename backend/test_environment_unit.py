import os
import sys
import unittest
from unittest.mock import patch

sys.path.append(os.path.dirname(__file__))

import environment_check as env


class EnvironmentValidationTests(unittest.TestCase):
    def test_validate_windows_platform_accepts_windows(self):
        env.validate_windows_platform(platform="win32")

    def test_validate_windows_platform_rejects_non_windows(self):
        with self.assertRaises(env.EnvironmentValidationError) as ctx:
            env.validate_windows_platform(platform="linux")

        self.assertIn("solo es compatible con Windows", str(ctx.exception))
        self.assertIn("linux", str(ctx.exception))

    @patch("environment_check.importlib.import_module")
    def test_validate_windows_dependencies_reports_pywin32_install_steps(self, mock_import_module):
        def _side_effect(module_name):
            if module_name == "win32gui":
                raise ImportError("missing win32gui")
            return object()

        mock_import_module.side_effect = _side_effect

        with self.assertRaises(env.EnvironmentValidationError) as ctx:
            env.validate_windows_dependencies()

        self.assertIn("pip install pywin32", str(ctx.exception))
        self.assertIn("pywin32_postinstall", str(ctx.exception))

    @patch("environment_check.importlib.import_module")
    def test_validate_windows_dependencies_reports_pynput_install_steps(self, mock_import_module):
        def _side_effect(module_name):
            if module_name == "pynput.keyboard":
                raise ImportError("missing pynput")
            return object()

        mock_import_module.side_effect = _side_effect

        with self.assertRaises(env.EnvironmentValidationError) as ctx:
            env.validate_windows_dependencies()

        self.assertIn("pip install pynput", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
