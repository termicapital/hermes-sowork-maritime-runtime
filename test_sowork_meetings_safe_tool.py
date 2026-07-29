import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).with_name("sowork_meetings_safe_tool.py")


class SoWorkMeetingsSafeToolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        class Registry:
            def register(self, **_kwargs):
                return None

        registry_module = types.ModuleType("tools.registry")
        registry_module.registry = Registry()
        sys.modules.setdefault("tools", types.ModuleType("tools"))
        sys.modules["tools.registry"] = registry_module
        spec = importlib.util.spec_from_file_location("sowork_meetings_safe_tool", MODULE_PATH)
        cls.module = importlib.util.module_from_spec(spec)
        assert spec.loader
        sys.modules[spec.name] = cls.module
        spec.loader.exec_module(cls.module)

    def test_read_calls_only_loopback_parent_endpoint(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *_args): return None
            def read(self, *_args): return json.dumps({"items": []}).encode()

        with tempfile.TemporaryDirectory() as tmp:
            token_path = Path(tmp) / "token"
            token_path.write_text("t" * 48)
            with (
                patch.object(self.module, "TOKEN_PATH", token_path),
                patch.object(self.module.urllib.request, "urlopen", return_value=Response()) as urlopen,
            ):
                result = self.module.sowork_meetings_read("list_meetings", limit=10)
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:8765/internal/sowork/meetings/read")
        self.assertEqual(request.headers["X-discovery-internal-token"], "t" * 48)
        self.assertEqual(json.loads(result), {"items": []})

    def test_validation_rejects_writes_and_bad_inputs(self):
        for kwargs in (
            {"action": "delete_meeting"},
            {"action": "get_meeting", "digest_id": "../../secret"},
            {"action": "search_meetings", "query": ""},
            {"action": "search_meetings", "query": "x" * 257},
            {"action": "list_meetings", "kind": "video"},
            {"action": "list_meetings", "since": 20, "until": 10},
            {"action": "list_meetings", "limit": 51},
        ):
            with self.assertRaises(ValueError):
                self.module.sowork_meetings_read(**kwargs)

    def test_schema_is_read_only_and_has_no_video_action(self):
        actions = set(self.module.SCHEMA["parameters"]["properties"]["action"]["enum"])
        self.assertEqual(actions, {"list_meetings", "search_meetings", "get_meeting"})
        self.assertFalse({"delete_meeting", "update_meeting", "get_video"} & actions)


if __name__ == "__main__":
    unittest.main()
