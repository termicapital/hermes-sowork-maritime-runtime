# Hermes SoWork Maritime Runtime

Generic, credential-free Maritime runtime for a Hermes-based SoWork group agent.

## Security model

- Public `/webhook` payloads are wake signals only and never enter an LLM prompt.
- The runtime polls one configured SoWork conversation using an encrypted Maritime secret.
- Only allowlisted SoWork user IDs and explicit `/scout`, `@DiscoveryScout`, or `Discovery Scout:` invocations execute the agent.
- The Hermes child receives a strict non-secret environment allowlist and the runtime refuses to start if `/opt/data/.env` exists.
- Shared skills are exposed through a custom read-only toolset (`skills_list` and `skill_view`, never `skill_manage`).
- OpenRouter requests use a bounded model allowlist and a loopback-only parent proxy; the Hermes child never receives the key.
- Terminal, file, code execution, delegation, and browser toolsets are excluded from the shared surface.
- Inference is bounded to two workers; public HTTP concurrency, body size, and socket duration are capped.
- State and deduplication live on Maritime's persistent `/opt/data` volume; interrupted workers become retryable.
- No credentials or customer identity are committed to this repository.
- Private skills, persona, config, and OAuth state are synchronized separately after deployment.

## Endpoints

- `GET /health` — runtime status and non-secret processing counts.
- `POST /webhook` — coalesced wake/poll signal; request body is ignored.

## Required environment

Secrets: `SOWORK_API_TOKEN`, `HERMES_CODEX_AUTH_B64`, `OPENROUTER_API_KEY`.

Non-secret: `SOWORK_CHANNEL_ID`, `SOWORK_ALLOWED_USER_IDS`, `DISCOVERY_BRIDGE_ENABLED`, `DISCOVERY_POLL_INTERVAL`, `PORT`.

## Verification

Run unit tests locally:

```bash
python3 -m unittest -v test_discovery_runtime.py
```

After deployment, execute `/opt/discovery-runtime/verify-runtime.sh` through Maritime and run a real Hermes CLI turn before enabling the bridge.
