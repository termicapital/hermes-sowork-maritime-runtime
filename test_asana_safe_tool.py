import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).with_name("asana_safe_tool.py")


class AsanaSafeToolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        class Registry:
            def register(self, **_kwargs):
                return None

        registry_module = types.ModuleType("tools.registry")
        registry_module.registry = Registry()
        sys.modules.setdefault("tools", types.ModuleType("tools"))
        sys.modules["tools.registry"] = registry_module
        spec = importlib.util.spec_from_file_location("asana_safe_tool", MODULE_PATH)
        cls.module = importlib.util.module_from_spec(spec)
        assert spec.loader
        sys.modules[spec.name] = cls.module
        spec.loader.exec_module(cls.module)

    def test_read_calls_only_loopback_parent_endpoint(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *_args): return None
            def read(self, *_args): return json.dumps({"data": [{"gid": "1", "name": "Project"}]}).encode()

        with tempfile.TemporaryDirectory() as tmp:
            token_path = Path(tmp) / "token"
            token_path.write_text("t" * 48)
            with (
                patch.object(self.module, "TOKEN_PATH", token_path),
                patch.object(self.module.urllib.request, "urlopen", return_value=Response()) as urlopen,
            ):
                result = self.module.asana_read("list_projects", limit=10)
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:8765/internal/asana/read")
        self.assertEqual(request.headers["X-discovery-internal-token"], "t" * 48)
        self.assertEqual(json.loads(result)["data"][0]["name"], "Project")

    def test_local_validation_rejects_writes_and_bad_inputs(self):
        with self.assertRaises(ValueError):
            self.module.asana_read("create_task")
        with self.assertRaises(ValueError):
            self.module.asana_read("list_tasks")
        with self.assertRaises(ValueError):
            self.module.asana_read("get_task", task_gid="")
        with self.assertRaises(ValueError):
            self.module.asana_read("search_tasks", query="x" * 201)
        with self.assertRaises(ValueError):
            self.module.asana_read("list_projects", limit=101)

    def test_schema_exposes_no_mutation_action(self):
        actions = set(self.module.SCHEMA["parameters"]["properties"]["action"]["enum"])
        self.assertTrue({"list_projects", "list_tasks", "get_task"} <= actions)
        self.assertFalse({"create_task", "update_task", "complete_task", "delete_task"} & actions)


if __name__ == "__main__":
    unittest.main()
