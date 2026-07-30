import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).parent


class Registry:
    def register(self, **_kwargs):
        return None


class PerplexitySafeToolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proxy = Mock(return_value='{"ok":true}')
        tools_module = types.ModuleType("tools")
        registry_module = types.ModuleType("tools.registry")
        registry_module.registry = Registry()
        safe_proxy_module = types.ModuleType("safe_proxy_client")
        safe_proxy_module.MAX_RESULT_CHARS = 200_000
        safe_proxy_module.proxy = cls.proxy
        spec = importlib.util.spec_from_file_location(
            "perplexity_safe_tool_under_test", ROOT / "perplexity_safe_tool.py"
        )
        cls.module = importlib.util.module_from_spec(spec)
        assert spec.loader
        with patch.dict(
            sys.modules,
            {
                "tools": tools_module,
                "tools.registry": registry_module,
                "safe_proxy_client": safe_proxy_module,
            },
        ):
            spec.loader.exec_module(cls.module)

    def setUp(self):
        self.proxy.reset_mock()

    def test_deep_research_uses_extended_child_proxy_timeout(self):
        self.module.perplexity_safe(
            action="chat",
            prompt="Research Saudi robotics",
            model="sonar-deep-research",
        )
        self.assertEqual(self.proxy.call_args.kwargs["timeout"], 1700)

    def test_other_models_keep_standard_child_proxy_timeout(self):
        self.module.perplexity_safe(action="chat", prompt="Question", model="sonar-pro")
        self.assertEqual(self.proxy.call_args.kwargs["timeout"], 300)


if __name__ == "__main__":
    unittest.main()
