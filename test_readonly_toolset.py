import importlib.util
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("install_readonly_toolset.py")


class ReadonlyToolsetInstallerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("readonly_installer", MODULE_PATH)
        cls.module = importlib.util.module_from_spec(spec)
        assert spec.loader
        sys.modules[spec.name] = cls.module
        spec.loader.exec_module(cls.module)

    def test_adds_readonly_toolset_without_skill_manage(self):
        source = '''TOOLSETS = {
    "skills": {
        "description": "Manage skills",
        "tools": ["skills_list", "skill_view", "skill_manage"],
        "includes": []
    },
}
'''
        patched = self.module.patch_source(source)
        self.assertIn('"skills_readonly"', patched)
        block = patched.split('"skills_readonly"', 1)[1].split('    "skills": {', 1)[0]
        self.assertIn('"skills_list", "skill_view"', block)
        self.assertNotIn("skill_manage", block)
        self.assertIn('"openrouter_safe"', patched)
        self.assertIn('"openrouter_query"', patched)
        self.assertIn('"asana_safe"', patched)
        self.assertIn('"asana_read"', patched)

    def test_patch_is_idempotent(self):
        source = '''TOOLSETS = {
    "skills": {
        "description": "Manage skills",
        "tools": ["skills_list", "skill_view", "skill_manage"],
        "includes": []
    },
}
'''
        once = self.module.patch_source(source)
        self.assertEqual(self.module.patch_source(once), once)


if __name__ == "__main__":
    unittest.main()
