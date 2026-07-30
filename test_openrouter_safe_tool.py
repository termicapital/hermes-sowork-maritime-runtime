import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).with_name("openrouter_safe_tool.py")


class OpenRouterSafeToolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        class Registry:
            def register(self, **_kwargs):
                return None

        import types

        registry_module = types.ModuleType("tools.registry")
        registry_module.registry = Registry()
        sys.modules.setdefault("tools", types.ModuleType("tools"))
        sys.modules["tools.registry"] = registry_module
        spec = importlib.util.spec_from_file_location(
            "openrouter_safe_tool", MODULE_PATH
        )
        cls.module = importlib.util.module_from_spec(spec)
        assert spec.loader
        sys.modules[spec.name] = cls.module
        spec.loader.exec_module(cls.module)

    def test_catalog_calls_only_fixed_loopback_route(self):
        with patch.object(self.module, "proxy", return_value='{"models":[]}') as proxy:
            result = self.module.openrouter_catalog()
        proxy.assert_called_once_with(
            "/internal/openrouter/catalog",
            {"query": "", "output_modality": "", "limit": 50},
        )
        self.assertEqual(json.loads(result), {"models": []})

    def test_generation_calls_only_fixed_loopback_route(self):
        with patch.object(self.module, "proxy", return_value='{"text":"OK"}') as proxy:
            result = self.module.openrouter_generate(
                "text", "openai/gpt-4o-mini", "test", 10
            )
        self.assertEqual(json.loads(result), {"text": "OK"})
        self.assertEqual(proxy.call_args.args[0], "/internal/openrouter/generate")

    def test_generation_enforces_local_input_bounds_before_request(self):
        with self.assertRaises(ValueError):
            self.module.openrouter_generate("text", "", "test", 10)
        with self.assertRaises(ValueError):
            self.module.openrouter_generate(
                "text", "openai/gpt-4o-mini", "x" * 12001, 10
            )
        with self.assertRaises(ValueError):
            self.module.openrouter_generate("text", "openai/gpt-4o-mini", "test", 5000)


if __name__ == "__main__":
    unittest.main()
