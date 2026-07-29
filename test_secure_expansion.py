import base64
import importlib.util
import io
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).parent


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class Response:
    def __init__(self, payload, status=200, headers=None):
        self.raw = (
            payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        )
        self.status = status
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self, limit=-1):
        return self.raw if limit < 0 else self.raw[:limit]

    def __iter__(self):
        return iter(self.raw.splitlines(keepends=True))


class SecureExpansionTests(unittest.TestCase):
    def test_parent_http_client_refuses_redirects(self):
        handler = self.runtime.NoRedirectHandler()
        request = self.runtime.urllib.request.Request("https://api.example.test/start")
        self.assertIsNone(
            handler.redirect_request(
                request, None, 302, "Found", {}, "https://attacker.example/"
            )
        )

    @classmethod
    def setUpClass(cls):
        cls.runtime = load("discovery_runtime")

    def test_firecrawl_fixed_endpoints_validation_ssrf_and_bounds(self):
        r = self.runtime
        valid = r.validate_firecrawl_payload(
            {
                "action": "search",
                "query": "ships",
                "limit": 20,
                "country": "US",
                "include_domains": ["example.com"],
                "hydrate_markdown": True,
            }
        )
        self.assertEqual(valid[0], "search")
        for bad in [
            {"action": "search", "query": "x" * 501},
            {"action": "search", "query": "x", "limit": 21},
            {
                "action": "search",
                "query": "x",
                "include_domains": ["a.com"],
                "exclude_domains": ["b.com"],
            },
            {"action": "search", "query": "x", "include_domains": ["https://a.com/x"]},
            {"action": "scrape", "url": "http://localhost/a"},
            {"action": "scrape", "url": "http://127.0.0.1/a"},
            {"action": "scrape", "url": "http://169.254.1.1/a"},
            {"action": "scrape", "url": "http://10.1.2.3/a"},
            {"action": "scrape", "url": "file:///etc/passwd"},
            {"action": "scrape", "url": "https://example.com", "proxy": "evil"},
            {"action": "scrape", "url": "https://example.com", "headers": {"x": "y"}},
        ]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                r.validate_firecrawl_payload(bad)
        with (
            patch.dict(os.environ, {"FIRECRAWL_API_KEY": "secret"}),
            patch.object(
                r.urllib.request, "urlopen", return_value=Response({"data": []})
            ) as call,
        ):
            r.call_firecrawl({"action": "search", "query": "ships"})
        req = call.call_args.args[0]
        self.assertEqual(
            (req.method, req.full_url), ("POST", "https://api.firecrawl.dev/v2/search")
        )
        self.assertEqual(json.loads(req.data), {"query": "ships", "limit": 5})

        with (
            patch.dict(os.environ, {"FIRECRAWL_API_KEY": "secret"}),
            patch.object(
                r.urllib.request,
                "urlopen",
                return_value=Response({"success": True, "data": {"markdown": "ok"}}),
            ) as call,
        ):
            r.call_firecrawl(
                {
                    "action": "scrape",
                    "url": "https://example.com/public-research",
                }
            )
        scrape_body = json.loads(call.call_args.args[0].data)
        self.assertFalse(scrape_body["storeInCache"])
        self.assertNotIn("zeroDataRetention", scrape_body)

    def test_perplexity_exact_endpoints_models_and_bounded_results(self):
        r = self.runtime
        for model in (
            "sonar",
            "sonar-pro",
            "sonar-reasoning-pro",
            "sonar-deep-research",
        ):
            self.assertEqual(
                r.validate_perplexity_payload(
                    {"action": "chat", "prompt": "q", "model": model}
                )[1],
                model,
            )
        for bad in (
            {"action": "chat", "prompt": "q", "model": "other"},
            {"action": "search", "query": "x" * 501},
            {"action": "chat", "prompt": "x" * 12001, "max_tokens": 1},
            {"action": "chat", "prompt": "q", "max_tokens": 4001},
        ):
            with self.assertRaises(ValueError):
                r.validate_perplexity_payload(bad)
        with (
            patch.dict(os.environ, {"PERPLEXITY_API_KEY": "secret"}),
            patch.object(
                r.urllib.request, "urlopen", return_value=Response({"results": []})
            ) as call,
        ):
            r.call_perplexity({"action": "search", "query": "q"})
        self.assertEqual(
            call.call_args.args[0].full_url, "https://api.perplexity.ai/search"
        )
        with (
            patch.dict(os.environ, {"PERPLEXITY_API_KEY": "secret"}),
            patch.object(
                r.urllib.request,
                "urlopen",
                return_value=Response(
                    {
                        "choices": [{"message": {"content": "ok"}}],
                        "citations": ["u"] * 100,
                    }
                ),
            ) as call,
        ):
            out = r.call_perplexity(
                {"action": "chat", "prompt": "q", "model": "sonar-deep-research"}
            )
        self.assertEqual(
            call.call_args.args[0].full_url,
            "https://api.perplexity.ai/v1/sonar",
        )
        self.assertLessEqual(len(out["citations"]), 20)

    def test_perplexity_deep_research_falls_back_to_openrouter(self):
        r = self.runtime
        quota_error = r.urllib.error.HTTPError(
            "https://api.perplexity.ai/v1/sonar",
            401,
            "insufficient_quota",
            {},
            io.BytesIO(b'{"error":{"code":"insufficient_quota"}}'),
        )
        fallback_result = {
            "choices": [
                {
                    "message": {
                        "content": "researched",
                        "reasoning_details": "x" * 200_000,
                        "annotations": [
                            {
                                "type": "url_citation",
                                "url": f"https://example.com/{index}",
                            }
                            for index in range(30)
                        ],
                    }
                }
            ],
        }
        with (
            patch.dict(
                os.environ,
                {
                    "PERPLEXITY_API_KEY": "perplexity-secret",
                    "OPENROUTER_API_KEY": "openrouter-secret",
                },
            ),
            patch.object(
                r, "_provider_json", side_effect=[quota_error, fallback_result]
            ) as provider,
        ):
            out = r.call_perplexity(
                {
                    "action": "chat",
                    "prompt": "Research Saudi robotics sandboxes",
                    "model": "sonar-deep-research",
                    "max_tokens": 2000,
                }
            )
        self.assertEqual(provider.call_count, 2)
        direct_call, fallback_call = provider.call_args_list
        self.assertEqual(direct_call.args[0], "https://api.perplexity.ai/v1/sonar")
        self.assertEqual(direct_call.kwargs["timeout"], 1200)
        self.assertEqual(
            fallback_call.args[:2],
            (
                "https://openrouter.ai/api/v1/chat/completions",
                "OPENROUTER_API_KEY",
            ),
        )
        self.assertEqual(
            fallback_call.args[2]["model"], "perplexity/sonar-deep-research"
        )
        self.assertEqual(fallback_call.kwargs["timeout"], 1200)
        self.assertFalse(fallback_call.kwargs["bound_result"])
        self.assertEqual(len(out["citations"]), 20)
        self.assertEqual(out["choices"][0]["message"]["content"], "researched")
        self.assertNotIn("truncated", out)

    def test_perplexity_deep_research_invalid_request_does_not_fallback(self):
        r = self.runtime
        invalid_request = r.urllib.error.HTTPError(
            "https://api.perplexity.ai/v1/sonar",
            400,
            "invalid_request",
            {},
            io.BytesIO(b'{"error":{"code":"invalid_request"}}'),
        )
        with (
            patch.dict(
                os.environ,
                {
                    "PERPLEXITY_API_KEY": "perplexity-secret",
                    "OPENROUTER_API_KEY": "openrouter-secret",
                },
            ),
            patch.object(r, "_provider_json", side_effect=invalid_request) as provider,
            self.assertRaises(r.urllib.error.HTTPError),
        ):
            r.call_perplexity(
                {
                    "action": "chat",
                    "prompt": "q",
                    "model": "sonar-deep-research",
                }
            )
        self.assertEqual(provider.call_count, 1)

    def test_perplexity_openrouter_fallback_rejects_error_payload(self):
        r = self.runtime
        quota_error = r.urllib.error.HTTPError(
            "https://api.perplexity.ai/v1/sonar",
            401,
            "insufficient_quota",
            {},
            io.BytesIO(b"{}"),
        )
        with (
            patch.dict(
                os.environ,
                {
                    "PERPLEXITY_API_KEY": "perplexity-secret",
                    "OPENROUTER_API_KEY": "openrouter-secret",
                },
            ),
            patch.object(
                r,
                "_provider_json",
                side_effect=[
                    quota_error,
                    {"error": {"code": 402, "message": "Insufficient credits"}},
                ],
            ),
            self.assertRaisesRegex(RuntimeError, "OpenRouter deep research failed"),
        ):
            r.call_perplexity(
                {
                    "action": "chat",
                    "prompt": "q",
                    "model": "sonar-deep-research",
                }
            )

    def test_xai_responses_is_fixed_and_tools_are_allowlisted(self):
        r = self.runtime
        self.assertEqual(r.validate_xai_payload({"prompt": "q"})[0], "grok-4.5")
        for bad in (
            {"prompt": ""},
            {"prompt": "x" * 12001},
            {"prompt": "q", "tools": ["code_interpreter"]},
            {"prompt": "q", "model": "evil"},
            {"prompt": "q", "max_output_tokens": 4001},
        ):
            with self.assertRaises(ValueError):
                r.validate_xai_payload(bad)
        with (
            patch.dict(os.environ, {"XAI_API_KEY": "secret"}),
            patch.object(
                r.urllib.request,
                "urlopen",
                return_value=Response({"output_text": "ok", "citations": []}),
            ) as call,
        ):
            r.call_xai({"prompt": "q", "tools": ["web_search", "x_search"]})
        req = call.call_args.args[0]
        self.assertEqual(
            (req.method, req.full_url), ("POST", "https://api.x.ai/v1/responses")
        )
        self.assertEqual(
            json.loads(req.data)["tools"],
            [{"type": "web_search"}, {"type": "x_search"}],
        )

    def test_dynamic_openrouter_catalog_hard_human_gate_and_expiring_capability(self):
        r = self.runtime
        catalog_payload = {
            "data": [
                {
                    "id": "vendor/live-model",
                    "name": "Live",
                    "architecture": {
                        "input_modalities": ["text"],
                        "output_modalities": ["text"],
                    },
                    "pricing": {"prompt": "0.1", "completion": "0.2"},
                }
            ]
        }
        cache = r.OpenRouterCatalogCache(ttl=60)
        with (
            patch.dict(os.environ, {"OPENROUTER_API_KEY": "secret"}),
            patch.object(
                r.urllib.request, "urlopen", return_value=Response(catalog_payload)
            ),
        ):
            catalog = cache.get()
        self.assertEqual(catalog[0]["id"], "vendor/live-model")
        self.assertIsNone(r.select_exact_catalog_model("please use something", catalog))
        self.assertEqual(
            r.select_exact_catalog_model("vendor/live-model", catalog),
            "vendor/live-model",
        )
        self.assertIsNone(
            r.select_exact_catalog_model(
                "vendor/live-model and other/model", catalog + [{"id": "other/model"}]
            )
        )
        registry = r.RunCapabilityRegistry(ttl=60)
        token = registry.issue("vendor/live-model")
        self.assertEqual(registry.authorize(token), "vendor/live-model")
        self.assertNotEqual(token, registry.issue(None))
        with self.assertRaises(PermissionError):
            registry.require_model(token, "other/model")
        registry.require_model(token, "vendor/live-model")
        registry.revoke(token)
        with self.assertRaises(PermissionError):
            registry.authorize(token)

        challenges = self.runtime.ModelSelectionChallenges(ttl=60)
        self.assertFalse(challenges.consume("u"))
        challenges.issue("u")
        self.assertTrue(challenges.consume("u"))
        self.assertFalse(challenges.consume("u"))

    def test_openrouter_catalog_can_be_bounded_and_filtered_without_hiding_full_catalog(
        self,
    ):
        catalog = [
            {"id": "vendor/text", "name": "Text", "output_modalities": ["text"]},
            {
                "id": "vendor/image-one",
                "name": "Image One",
                "output_modalities": ["image"],
            },
            {
                "id": "other/image-two",
                "name": "Image Two",
                "output_modalities": ["image"],
            },
        ]
        result = self.runtime.filter_openrouter_catalog(catalog, "vendor", "image", 10)
        self.assertEqual([item["id"] for item in result], ["vendor/image-one"])
        with self.assertRaises(ValueError):
            self.runtime.filter_openrouter_catalog(catalog, "", "video", 10)
        with self.assertRaises(ValueError):
            self.runtime.filter_openrouter_catalog(catalog, "", "", 101)

    def test_openrouter_generation_uses_live_catalog_and_media_is_safely_persisted(
        self,
    ):
        r = self.runtime
        cache = r.OpenRouterCatalogCache(ttl=60)
        cache.seed(
            [
                {
                    "id": "vendor/image",
                    "name": "I",
                    "input_modalities": ["text"],
                    "output_modalities": ["image"],
                    "pricing": {},
                }
            ]
        )
        cache.seed_image_models({"vendor/image"})
        with tempfile.TemporaryDirectory() as tmp:
            cfg = r.Config(
                channel_id="c",
                allowed_user_ids={"u"},
                data_dir=Path(tmp),
                public_base_url="https://public.example",
            )
            png = base64.b64encode(b"\x89PNG\r\n\x1a\ncontent").decode()
            with (
                patch.dict(os.environ, {"OPENROUTER_API_KEY": "secret"}),
                patch.object(
                    r.urllib.request,
                    "urlopen",
                    return_value=Response({"data": [{"b64_json": png}]}),
                ) as call,
            ):
                out = r.call_openrouter(
                    cfg,
                    {"kind": "image", "model": "vendor/image", "prompt": "draw"},
                    cache,
                )
            self.assertTrue(
                out["media_url"].startswith("https://public.example/media/")
            )
            self.assertEqual(
                call.call_args.args[0].full_url, "https://openrouter.ai/api/v1/images"
            )
            media_id = out["media_url"].rsplit("/", 1)[1]
            mime, data = r.read_media(cfg, media_id)
            self.assertEqual(mime, "image/png")
            self.assertEqual(data, base64.b64decode(png))
            path = cfg.data_dir / "media" / media_id
            os.utime(path, (0, 0))
            with self.assertRaises(FileNotFoundError):
                r.read_media(cfg, media_id)
            for bad in ("../x", "x/y", "not-valid"):
                with self.assertRaises((ValueError, FileNotFoundError)):
                    r.read_media(cfg, bad)

        with self.assertRaises(ValueError):
            r.validate_openrouter_payload(
                {"kind": "image", "model": "vendor/text", "prompt": "draw"},
                [{"id": "vendor/text", "output_modalities": ["text"]}],
            )
        with self.assertRaises(ValueError):
            r.validate_openrouter_payload(
                {
                    "kind": "audio",
                    "model": "vendor/audio",
                    "prompt": "say hi",
                    "format": "exe",
                },
                [{"id": "vendor/audio", "output_modalities": ["audio"]}],
            )

    def test_github_exact_repos_safe_routes_paths_and_branches(self):
        r = self.runtime
        allowed = "termicapital/discovery-scout"
        self.assertEqual(
            r.validate_github_payload({"action": "repo", "repo": allowed})[1], allowed
        )
        for bad in (
            {"action": "repo", "repo": "other/repo"},
            {
                "action": "upsert_file",
                "repo": allowed,
                "branch": "main",
                "path": "x",
                "content": "a",
            },
            {
                "action": "upsert_file",
                "repo": allowed,
                "branch": "agent/x",
                "path": "../secret",
                "content": "a",
            },
            {
                "action": "upsert_file",
                "repo": allowed,
                "branch": "agent/x",
                "path": ".github/workflows/x.yml",
                "content": "a",
            },
            {"action": "merge_pr", "repo": allowed},
            {
                "action": "create_branch",
                "repo": allowed,
                "branch": "agent/x",
                "force": True,
            },
            {
                "action": "open_pr",
                "repo": allowed,
                "branch": "main",
                "base": "main",
                "title": "unsafe",
            },
        ):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                r.validate_github_payload(bad)
        with (
            patch.dict(os.environ, {"GITHUB_TOKEN": "secret"}),
            patch.object(
                r.urllib.request,
                "urlopen",
                return_value=Response({"full_name": allowed}),
            ) as call,
        ):
            r.call_github({"action": "repo", "repo": allowed})
        req = call.call_args.args[0]
        self.assertEqual(
            (req.method, req.full_url),
            ("GET", f"https://api.github.com/repos/{allowed}"),
        )
        self.assertNotIn("secret", json.dumps(r.call_github.__annotations__))

    def test_github_writes_require_exact_owner_approval_digest(self):
        registry = self.runtime.RunCapabilityRegistry(ttl=60)
        digest = "a" * 64
        reader = registry.issue(None)
        writer = registry.issue(None, github_write_digest=digest)
        with self.assertRaises(PermissionError):
            registry.authorize_github_write(reader, digest)
        with self.assertRaises(PermissionError):
            registry.authorize_github_write(writer, "b" * 64)
        registry.authorize_github_write(writer, digest)

        payload = {
            "action": "upsert_file",
            "repo": "termicapital/discovery-scout",
            "branch": "agent/test",
            "path": "README.md",
            "content": "exact content",
            "message": "Agent update",
        }
        prepared = self.runtime.prepare_github_write(
            {
                "action": "prepare_write",
                "write_action": "upsert_file",
                **{k: v for k, v in payload.items() if k != "action"},
            }
        )
        self.assertEqual(
            prepared["approval_marker"],
            "APPROVE_GITHUB_WRITE " + self.runtime.github_write_digest(payload),
        )
        self.assertEqual(
            self.runtime.parse_github_write_approval(prepared["approval_marker"]),
            self.runtime.github_write_digest(payload),
        )
        without_message = {k: v for k, v in payload.items() if k != "message"}
        explicit_default = {**without_message, "message": "Agent update"}
        self.assertEqual(
            self.runtime.github_write_digest(without_message),
            self.runtime.github_write_digest(explicit_default),
        )
        self.assertEqual(
            self.runtime._github_default_message("delete_file"), "Agent delete"
        )

    def test_github_writer_config_is_exactly_one_allowlisted_owner(self):
        cfg = self.runtime.Config(
            enabled=True,
            channel_id="channel",
            allowed_user_ids={"owner", "reader"},
            api_token="token",
            github_write_allowed_user_ids={"owner"},
        )
        cfg.validate()
        cfg.github_write_allowed_user_ids = {"owner", "reader"}
        with self.assertRaises(RuntimeError):
            cfg.validate()
        cfg.github_write_allowed_user_ids = {"outsider"}
        with self.assertRaises(RuntimeError):
            cfg.validate()

    def test_firecrawl_rejects_hostname_resolving_to_private_address(self):
        with patch.object(
            self.runtime.socket,
            "getaddrinfo",
            return_value=[
                (
                    self.runtime.socket.AF_INET,
                    self.runtime.socket.SOCK_STREAM,
                    6,
                    "",
                    ("127.0.0.1", 443),
                ),
            ],
        ):
            with self.assertRaises(ValueError):
                self.runtime.validate_firecrawl_payload(
                    {"action": "scrape", "url": "https://attacker.example/"}
                )

    def test_prompt_toolsets_and_child_env_wiring(self):
        r = self.runtime
        tools = set(r.agent_toolsets().split(","))
        self.assertTrue(
            {
                "firecrawl_safe",
                "perplexity_safe",
                "xai_safe",
                "github_safe",
                "openrouter_safe",
            }
            <= tools
        )
        prompt = r.build_prompt(
            {"id": "m", "text": "/scout image", "sender": {"id": "u", "name": "N"}},
            "",
            r.Config(channel_id="c", allowed_user_ids={"u"}),
        )
        self.assertIn("exact catalog model ID", prompt)
        self.assertIn("STOP", prompt)
        child = r.sanitized_child_env(
            {
                "PATH": "/bin",
                "HERMES_RUN_CAPABILITY_PATH": "/safe/token",
                "FIRECRAWL_API_KEY": "secret",
                "GITHUB_TOKEN": "secret",
            }
        )
        self.assertEqual(
            child, {"PATH": "/bin", "HERMES_RUN_CAPABILITY_PATH": "/safe/token"}
        )


class ChildToolsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        class Registry:
            def register(self, **_kwargs):
                pass

        registry_module = types.ModuleType("tools.registry")
        registry_module.registry = Registry()
        sys.modules.setdefault("tools", types.ModuleType("tools"))
        sys.modules["tools.registry"] = registry_module

    def test_children_use_only_fixed_loopback_and_return_bounded_json_strings(self):
        cases = [
            (
                "firecrawl_safe_tool",
                "firecrawl_safe",
                {"action": "search", "query": "q"},
                "/internal/firecrawl",
            ),
            (
                "perplexity_safe_tool",
                "perplexity_safe",
                {"action": "search", "query": "q"},
                "/internal/perplexity",
            ),
            ("xai_safe_tool", "xai_safe", {"prompt": "q"}, "/internal/xai"),
            (
                "github_safe_tool",
                "github_safe",
                {"action": "repo", "repo": "termicapital/discovery-scout"},
                "/internal/github",
            ),
        ]
        for module_name, function_name, kwargs, path in cases:
            with self.subTest(module=module_name):
                module = load(module_name)
                with tempfile.TemporaryDirectory() as tmp:
                    token_path = Path(tmp) / "run-token"
                    token_path.write_text("t" * 48)
                    os.environ["HERMES_RUN_CAPABILITY_PATH"] = str(token_path)
                    client = sys.modules["safe_proxy_client"]
                    with patch.object(
                        client.urllib.request,
                        "urlopen",
                        return_value=Response({"ok": True}),
                    ) as call:
                        result = getattr(module, function_name)(**kwargs)
                self.assertIsInstance(result, str)
                self.assertEqual(json.loads(result), {"ok": True})
                self.assertEqual(
                    call.call_args.args[0].full_url, f"http://127.0.0.1:8765{path}"
                )
                self.assertLessEqual(len(result), module.MAX_RESULT_CHARS)


if __name__ == "__main__":
    unittest.main()
