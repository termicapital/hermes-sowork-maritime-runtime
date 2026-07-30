# Hermes SoWork Maritime Runtime

Credential-isolated Maritime runtime for a Hermes Discovery Scout in one approved SoWork group.

## Security model

- Public `POST /webhook` is a coalesced wake signal only; its body never enters the LLM. The parent polls one configured conversation and accepts only explicit Scout invocations from allowlisted users.
- The Hermes child receives a strict non-secret environment. Provider keys stay in the parent. Every Hermes run receives a random, expiring capability file; it is revoked and deleted when that run exits. There are no child-editable approval booleans.
- Raw terminal, filesystem, code execution, delegation, browser, and skill mutation tools are excluded. Existing read-only Asana and SoWork Meeting Library access remains available.
- All internal provider calls are loopback-only, fixed-route, fixed-method proxies with bounded request, upstream, parsed value, and serialized result sizes.

### Safe provider capabilities

- **Firecrawl:** only `POST https://api.firecrawl.dev/v2/search` and `/v2/scrape`. Search has bounded query/limit/country and mutually exclusive validated domain filters. Scrape accepts only public HTTP(S), markdown/links, `onlyMainContent`, and basic/enhanced/auto proxy; no headers, actions, profile, or JavaScript. Requests set `storeInCache: false` but use Firecrawl's standard provider-side retention because this account is not Enterprise/ZDR-enabled.
- **Perplexity:** fixed Search API and current `/v1/sonar` endpoints with bounded search results/citations and models `sonar`, `sonar-pro`, `sonar-reasoning-pro`, and `sonar-deep-research`. Standard `sonar` calls try direct Perplexity first and fall back to the exact `perplexity/sonar` model through OpenRouter when the direct route is unavailable, quota/entitlement-limited, rate-limited, or transiently failing; invalid requests fail closed. Managed full discovery research admits paid stages under one monotonic 1,650-second provider deadline: direct Perplexity first (up to 600 seconds), then the same `perplexity/sonar-deep-research` model through OpenRouter (up to 500 seconds) when the direct route is unavailable, quota/entitlement-limited, rate-limited, or transiently failing. If that second route has a transient provider failure, the final independent fallback is `openai/gpt-5.2` through OpenRouter with the bounded `openrouter:web_search` server tool using Exa (up to 550 seconds, at most three searches and 30 results). Before every paid stage, the parent recalculates remaining deadline time and verifies that the child connection and run capability are still active; it does not start another stage after cancellation or deadline exhaustion. The child proxy waits up to 1,700 seconds and the overall worker up to 2,400 seconds to leave room for a late deep-research invocation. The listed OpenAI `o3`/`o4-mini` deep-research routes currently return provider HTTP 404 through this OpenRouter account, so they are not used as false fallback targets. HTTP-200 error envelopes are classified like HTTP exceptions; invalid requests and non-transient errors fail closed. The independent stage must return citations.
- **xAI:** only `POST /v1/responses`, default/only model `grok-4.5`, and only `web_search`/`x_search`; no code interpreter, file search, or arbitrary tools.
- **OpenRouter:** bounded live catalog from `GET /api/v1/models?output_modalities=all`; no static model allowlist. Calling the catalog creates a short-lived model-selection challenge. The agent must list models, ask the human for one exact model ID, and **STOP**. Generation is possible only in a later human-triggered run whose message contains exactly one exact live model ID and consumes that challenge. The parent validates output modality and dedicated Images API availability before spending. Supports text chat, dedicated image generations, and streaming audio. Bounded base64 media is stored under `/data/hermes/discovery-runtime/media` with random IDs, a seven-day/100-file retention bound, and read-only `GET /media/<id>` delivery. Returned URLs use the HTTPS `DISCOVERY_PUBLIC_BASE_URL`.
- **GitHub:** fixed `api.github.com` routes for exactly `termicapital/discovery-scout` and `termicapital/hermes-sowork-maritime-runtime`. Reads cover metadata, branches, files, commits, issues, PRs, checks, and workflows. Before a write, `prepare_write` hashes the complete operation and returns an `APPROVE_GITHUB_WRITE <digest>` marker; only Guillermo's later exact marker reply authorizes that byte-equivalent operation. Writes can create `agent/*` branches, upsert/delete bounded safe paths, and open/update PRs whose head is `agent/*`. Main/master/default writes, force, merge, releases, settings, secrets, and workflow mutation are unavailable.
- **Notion:** the credential remains parent-side. Reads are restricted to the Discovery Pipeline, Problem Signal Capture, and fixed Discovery Pipeline Meetings page. Page IDs must first be learned from an approved query; nested block IDs must first be learned from an approved page/block read. Page and block results expose bounded `has_more`/`next_cursor` pagination rather than silently truncating. Explicit requests from the single configured owner containing `--autonomous` may create at most one quality-gated row in each of the two approved data sources per run; failed validation or upstream errors release the reservation for an autonomous retry. Pipeline relations may reference only the Problem Signal row created in that same run. Interactive runs cannot write. Update, delete, owner assignment, schema mutation, workspace-wide search, and new select-option creation are unavailable.

## Endpoints

- `GET /health` — non-secret runtime status.
- `GET /media/<random-id>` — generated media only.
- `POST /webhook` — wake-only signal.
- `/internal/*` — loopback capability-protected provider operations.

## Required environment

Secrets:

- `SOWORK_API_TOKEN`
- `HERMES_CODEX_AUTH_B64`
- `OPENROUTER_API_KEY`
- `ASANA_TOKEN`
- `FIRECRAWL_API_KEY`
- `XAI_API_KEY`
- `PERPLEXITY_API_KEY`
- `GITHUB_TOKEN`
- `NOTION_API_TOKEN`

Non-secret:

- `SOWORK_CHANNEL_ID`
- `SOWORK_ALLOWED_USER_IDS`
- `GITHUB_WRITE_ALLOWED_USER_IDS` (Guillermo's SoWork user ID only; read access remains available to all otherwise-allowlisted senders)
- `DISCOVERY_BRIDGE_ENABLED`
- `DISCOVERY_POLL_INTERVAL`
- `DISCOVERY_PUBLIC_BASE_URL` (must be HTTPS for media delivery)
- `PORT`

No credential or customer identity is committed. Private skills/persona/config/OAuth state are synchronized separately.

## Verification

```bash
python3 -m unittest -v
ruff check *.py
python3 -m py_compile *.py
sh -n entrypoint.sh verify-runtime.sh
git diff --check
```

After deployment, execute `/opt/discovery-runtime/verify-runtime.sh` and a real non-paid Hermes CLI turn before enabling the bridge.
