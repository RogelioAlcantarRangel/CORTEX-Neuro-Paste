import os
import sys
import types
import unittest

sys.path.append(os.path.dirname(__file__))

# Stub de pyperclip para permitir importar clipboard_mgr en entornos sin dependencias instaladas.
pyperclip_stub = types.SimpleNamespace(copy=lambda text: None, paste=lambda: "")
sys.modules.setdefault("pyperclip", pyperclip_stub)

from clipboard_mgr import process_text


class ClipboardManagerTests(unittest.TestCase):
    def test_default_rules_uppercase(self):
        self.assertEqual(process_text("hola mundo"), "HOLA MUNDO")

    def test_pipeline_order(self):
        result = process_text("  hola\nMUNDO  ", rules=("trim", "remove_line_breaks", "title_case"))
        self.assertEqual(result, "Hola Mundo")

    def test_normalize_spaces(self):
        result = process_text("hola    mundo\t  cortex", rules=("normalize_spaces",))
        self.assertEqual(result, "hola mundo cortex")

    def test_ignores_unknown_rules(self):
        result = process_text("abc", rules=("unknown", "uppercase"))
        self.assertEqual(result, "ABC")

    def test_handles_non_string_input(self):
        self.assertEqual(process_text(123, rules=("uppercase",)), "123")
        self.assertEqual(process_text(None), "")


if __name__ == "__main__":
    unittest.main()
