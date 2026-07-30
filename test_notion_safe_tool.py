import importlib.util
import json
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).with_name("notion_safe_tool.py")


class NotionSafeToolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        class Registry:
            def register(self, **_kwargs):
                return None

        registry_module = types.ModuleType("tools.registry")
        registry_module.registry = Registry()
        sys.modules.setdefault("tools", types.ModuleType("tools"))
        sys.modules["tools.registry"] = registry_module
        spec = importlib.util.spec_from_file_location("notion_safe_tool", MODULE_PATH)
        cls.module = importlib.util.module_from_spec(spec)
        assert spec.loader
        sys.modules[spec.name] = cls.module
        spec.loader.exec_module(cls.module)

    def test_query_uses_only_fixed_parent_endpoint(self):
        with patch.object(
            self.module,
            "proxy",
            return_value=json.dumps({"results": [{"Idea": "Test"}]}),
        ) as proxy:
            result = self.module.notion_safe(
                "query", data_source="discovery_pipeline", page_size=25
            )
        self.assertEqual(proxy.call_args.args[0], "/internal/notion")
        self.assertEqual(proxy.call_args.kwargs["max_request_bytes"], 200_000)
        self.assertEqual(json.loads(result)["results"][0]["Idea"], "Test")

    def test_create_is_bounded_and_only_targets_approved_data_sources(self):
        with patch.object(self.module, "proxy", return_value='{"id":"page"}') as proxy:
            self.module.notion_safe(
                "create_page",
                data_source="problem_signal",
                properties={"Problem Statement": "Signal"},
                content="# Evidence\nBody",
            )
        payload = proxy.call_args.args[1]
        self.assertEqual(payload["data_source"], "problem_signal")
        self.assertEqual(payload["properties"]["Problem Statement"], "Signal")
        for bad in ("other", "", "5e6f6355-ec64-4950-b1cb-66806ef24401"):
            with self.assertRaises(ValueError):
                self.module.notion_safe("query", data_source=bad)
        with self.assertRaises(ValueError):
            self.module.notion_safe(
                "create_page",
                data_source="problem_signal",
                properties={"Problem Statement": "x"},
                content="x" * 80_001,
            )

    def test_schema_exposes_required_autonomous_run_actions_only(self):
        actions = set(self.module.SCHEMA["parameters"]["properties"]["action"]["enum"])
        self.assertEqual(
            actions,
            {"get_schema", "query", "fetch_page", "fetch_blocks", "create_page"},
        )
        self.assertNotIn("delete_page", actions)
        self.assertNotIn("update_page", actions)


if __name__ == "__main__":
    unittest.main()
