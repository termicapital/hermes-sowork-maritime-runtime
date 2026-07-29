import unittest
from pathlib import Path

ROOT = Path(__file__).parent


class ContainerContractTests(unittest.TestCase):
    def test_maritime_persistence_and_privilege_drop_are_explicit(self):
        dockerfile = (ROOT / "Dockerfile").read_text()
        entrypoint = (ROOT / "entrypoint.sh").read_text()
        self.assertIn("ENV HERMES_HOME=/data/hermes", dockerfile)
        self.assertIn(
            "ENV HERMES_WRITE_SAFE_ROOT=/data/hermes/discovery-scout", dockerfile
        )
        self.assertNotIn("ln -s /data/hermes /opt/data", dockerfile)
        self.assertIn('ENTRYPOINT ["/opt/discovery-runtime/entrypoint.sh"]', dockerfile)
        self.assertIn("PERSISTENT_HOME=/data/hermes", entrypoint)
        self.assertIn("chown 10000:10000", entrypoint)
        self.assertIn("--reuid=10000", entrypoint)
        self.assertIn("--regid=10000", entrypoint)
        self.assertIn("--bounding-set=-all", entrypoint)
        self.assertIn("--no-new-privs", entrypoint)
        self.assertIn("/opt/discovery-runtime/discovery_runtime.py", entrypoint)
        self.assertNotIn("chown -R", entrypoint)


if __name__ == "__main__":
    unittest.main()
