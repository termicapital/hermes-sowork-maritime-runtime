import importlib.util
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("openrouter_safe_tool.py")


class OpenRouterSafeToolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Stub the Hermes registry so this unit test runs outside the image.
        class Registry:
            def register(self, **_kwargs):
                return None
        import types
        registry_module = types.ModuleType("tools.registry")
        registry_module.registry = Registry()
        sys.modules.setdefault("tools", types.ModuleType("tools"))
        sys.modules["tools.registry"] = registry_module
        spec = importlib.util.spec_from_file_location("openrouter_safe_tool", MODULE_PATH)
        cls.module = importlib.util.module_from_spec(spec)
        assert spec.loader
        sys.modules[spec.name] = cls.module
        spec.loader.exec_module(cls.module)

    def test_query_calls_only_loopback_parent_endpoint(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *_args): return None
            def read(self, *_args): return json.dumps({"model": "openai/gpt-4o-mini", "text": "OK"}).encode()
        with tempfile.TemporaryDirectory() as tmp:
            token_path = Path(tmp) / "token"
            token_path.write_text("t" * 48)
            with (
                patch.object(self.module, "TOKEN_PATH", token_path),
                patch.object(self.module.urllib.request, "urlopen", return_value=Response()) as urlopen,
            ):
                result = self.module.openrouter_query("openai/gpt-4o-mini", "test", 10)
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:8765/internal/openrouter/query")
        self.assertEqual(request.headers["X-discovery-internal-token"], "t" * 48)
        self.assertEqual(result["text"], "OK")

    def test_query_enforces_local_input_bounds_before_request(self):
        with self.assertRaises(ValueError):
            self.module.openrouter_query("", "test", 10)
        with self.assertRaises(ValueError):
            self.module.openrouter_query("openai/gpt-4o-mini", "x" * 12001, 10)
        with self.assertRaises(ValueError):
            self.module.openrouter_query("openai/gpt-4o-mini", "test", 5000)


if __name__ == "__main__":
    unittest.main()
