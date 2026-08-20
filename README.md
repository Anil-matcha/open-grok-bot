# Open Grok Bot

A local-first AI workspace for creating bot personas, chatting with models exposed through MUAPI, and keeping conversations on your machine. The interface is built with Next.js and React; the API is built with FastAPI and Python.

This is an independent open-source project and is not affiliated with xAI.

[Quick start](#quick-start) · [Configuration](#configuration) · [API](#api) · [Architecture](#architecture) · [Limitations](#limitations)

> **Status:** Prototype / active development. The project is designed for local experimentation and is not yet a production, multi-user agent platform.

## What it does

- **Bot personas:** Create, edit, and switch between bots with their own role, system prompt, model, and visual identity.
- **Model picker:** Select model IDs from the catalog exposed by the FastAPI service. The default model is `grok-4-5`.
- **SSE chat:** Send a message, persist it locally, and receive `turn.started`, `content.delta`, and `turn.completed` events over Server-Sent Events.
- **Image attachments:** Upload JPEG, PNG, WEBP, GIF, or AVIF images. The backend sends them to the configured provider when possible and falls back to a local data URL for previews.
- **Markdown messages:** Render assistant replies as Markdown in the chat transcript.
- **Voice dictation:** Use the browser's Web Speech API when the browser supports it.
- **Approved workspace tools:** Explicit `/workspace list`, `/workspace read`, and `/workspace write` requests pause for user approval, stay inside `WORKSPACE_ROOT`, and produce audit events.
- **Governed action gateway:** Workspace actions use a structured request/result contract, a deny-by-default registry, approval state, and redacted lifecycle audit records.
- **Settings drawer:** Configure the MUAPI key, provider base URL, default model, Composio key, and local profile details.
- **Connector surface:** Browse a curated or live Composio app catalog, inspect connection status, and start OAuth authorization explicitly from Marketplace.
- **Read-only GitHub action:** After connecting GitHub, run an explicit issue lookup from chat and pass its structured result through the action gateway.
- **Approval-gated GitHub write:** Propose a GitHub issue from chat, inspect the repository/title/body-size preview, approve it, and receive a normalized issue result.
- **Audit trail:** Review local approval, workspace-tool, and connector events from the sidebar.
- **Computer workspace surface:** Preview the intended computer/terminal experience while the runtime integration is still being built.

## Quick start

### Requirements

- Node.js and npm
- Python and pip
- A MUAPI API key for live model responses

### 1. Clone the repository

```bash
git clone https://github.com/Anil-matcha/open-grok-bot.git
cd open-grok-bot
```

### 2. Start the FastAPI server

In a terminal window:

```bash
cd server
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

export MUAPI_API_KEY="your_muapi_api_key"
python run.py
```

The API starts at `http://127.0.0.1:8000`.

API documentation is available at:

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

### 3. Start the Next.js client

In a second terminal window:

```bash
cd client
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

You can also enter the provider key from **App Settings → Connections** after the UI loads. The environment variable is the server-side fallback.

## Configuration

The client defaults to `http://127.0.0.1:8000/api/v1`. Set `NEXT_PUBLIC_API_URL` if the API runs elsewhere:

```bash
NEXT_PUBLIC_API_URL="http://127.0.0.1:8000/api/v1"
```

The server reads these variables from the environment:

| Variable | Default | Purpose |
| --- | --- | --- |
| `MUAPI_API_KEY` | empty | Provider credential used when no key is saved in local settings |
| `MUAPI_BASE_URL` | `https://api.muapi.ai/api/v1` | Provider API base URL |
| `COMPOSIO_API_KEY` | empty | Optional connector credential used when no key is saved in local settings |
| `DEFAULT_MODEL` | `grok-4-5` | Initial model used for new settings and bots |
| `DATA_DIR` | per-user hidden app directory | SQLite database, migration copies, and local key location |
| `APP_ENCRYPTION_KEY` | generated mode-0600 key in `DATA_DIR` | Optional Fernet key for encrypted provider credentials |
| `WORKSPACE_ROOT` | repository root | Maximum directory that approved workspace tools can access |
| `WORKSPACE_MAX_FILE_BYTES` | `131072` | Read/write size limit for workspace files |
| `APPROVAL_TIMEOUT_SECONDS` | `120` | How long a pending approval remains open |
| `HOST` | `127.0.0.1` | FastAPI bind address |
| `PORT` | `8000` | FastAPI port |

The selected model ID is appended to `MUAPI_BASE_URL`. The configured provider must expose the expected endpoint and response shape for that model.

## App surfaces

| Surface | Purpose |
| --- | --- |
| Chat | Bot roster, model selection, Markdown replies, image attachments, voice dictation, and streamed responses |
| Computer | Visual preview of a future browser/terminal workspace |
| Marketplace | Searchable curated or live app catalog with explicit connect/disconnect actions |
| Audit trail | Recent approval, workspace-tool, and connector events persisted by the local API |
| App Settings | Local profile values and MUAPI connection/model settings |

## Architecture

```
Next.js client  ── HTTP + SSE ──▶  FastAPI server
                                     │
                 ┌───────────────────┼───────────────────┐
                 ▼                   ▼                   ▼
           SQLite + key store     MUAPI API       Optional Composio
           state/settings/audit   model + upload  connector endpoints
```

The main code areas are:

| Path | Responsibility |
| --- | --- |
| `client/app/` | Next.js app entry points and global styles |
| `client/components/` | Dashboard, chat, model picker, settings, marketplace, audit, and preview surfaces |
| `client/lib/api.js` | HTTP and EventSource client functions |
| `server/app/main.py` | FastAPI app, CORS, router registration, and health route |
| `server/app/routers/` | Bots, chat, models, uploads, settings, approvals, and connectors |
| `server/app/services/muapi_service.py` | Provider requests, prediction polling, output parsing, and response events |
| `server/app/services/storage_service.py` | SQLite persistence, legacy import, secrets, and default data |
| `server/app/services/database.py` | SQLite connection management and schema migrations |
| `server/app/services/secret_store.py` | Fernet encryption for provider credentials |
| `server/app/services/workspace_service.py` | Confined list/read/write workspace tools |
| `server/app/services/approval_broker.py` | Pending approval coordination and audit events |
| `server/app/services/action_gateway.py` | Registered action policy, approval handoff, execution, and lifecycle audit |
| `server/app/services/composio_service.py` | Server-side Composio MCP calls and normalized GitHub issue results |
| `server/app/services/connector_actions.py` | Explicit connector command parsing and gateway registration |
| `server/app/schemas/contracts.py` | Pydantic request and response models |
| `server/tests/` | Focused workspace and approval regression tests |

### Chat request flow

1. The client posts the user message to `/api/v1/chat/send`.
2. The server stores it in the local message store.
3. The client opens an EventSource connection to `/api/v1/chat/stream/{thread_id}`.
4. An explicit workspace or connector request becomes a structured action request and is checked against the deny-by-default gateway registry.
5. The gateway pauses the stream for approval when required, then executes the registered action.
6. The gateway emits normalized action lifecycle records; the client receives compatible tool events and the structured result.
7. The server sends the selected model, recent history, and tool result to MUAPI.
8. Provider output is forwarded as SSE deltas and the completed assistant message is persisted.

### Product direction

The prototype follows a local-first path: persistent bot personas and histories, explicit capabilities, user-visible approvals, provider flexibility, and optional app connectors. The next meaningful layers are durable memory and routines, voice input/output, browser and desktop execution, isolated computer providers, background jobs, and authenticated multi-user deployment. They are intentionally documented as roadmap items rather than implied by the current UI.

### Approved workspace commands

These commands are intentionally explicit; arbitrary shell commands are not accepted:

```text
/workspace list [path]
/workspace read <path>
/workspace write <path>
file content on the next line
```

Paths must remain inside `WORKSPACE_ROOT`. Reads and writes are limited by `WORKSPACE_MAX_FILE_BYTES`, and every request/decision/result is recorded in the local audit store.

Connector actions are intentionally explicit:

```text
/connector github issues <owner>/<repo> [open|closed|all]
/connector github create-issue <owner>/<repo> <title>
optional body on the next line
```

The read action requires a configured Composio key and an active GitHub connection. The write action also requires an approval response. Results are limited to issue summaries; credentials and issue bodies are not copied into the action request preview or audit summary.

## API

All routes are prefixed with `/api/v1`.

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/health` | Check server status and default model |
| GET, POST | `/bots` | List or create bot personas |
| PUT, DELETE | `/bots/{bot_id}` | Update or delete a bot |
| GET | `/models` | Return the configured model catalog |
| GET | `/chat/history/{thread_id}` | Read a bot's message history |
| POST | `/chat/send` | Store a user message |
| GET | `/chat/stream/{thread_id}?model=...` | Stream a response over SSE |
| POST | `/upload` | Validate and upload an image attachment |
| GET, POST | `/settings` | Read public settings or save write-only credentials and app settings |
| POST | `/approvals/respond` | Submit an Allow/Deny approval response |
| GET | `/audit?limit=100` | Read recent approval, tool, and connector events |
| GET | `/connectors/catalog` | Return curated or Composio-backed connector cards |
| GET | `/connectors?services=...` | Check connector connection status |
| POST | `/connectors/{slug}/authorize` | Request an OAuth URL |
| DELETE | `/connectors/{slug}` | Disconnect a connector |

Try the health route after starting the server:

```bash
curl http://127.0.0.1:8000/api/v1/health
```

## Local data and secrets

On first start, the server creates a SQLite database under the per-user data directory defined in `server/app/config.py`. Bots, messages, settings, approvals, and audit events survive restarts, with schema migrations tracked in the database. Existing JSON files are imported once and retained as migration copies; credential fields in the old settings file are scrubbed after import.

For local development:

- Provider credentials are encrypted at rest with a mode-0600 Fernet key in `DATA_DIR`. Set `APP_ENCRYPTION_KEY` when the key must be supplied by deployment secrets or shared across restarts and hosts.
- Settings responses never return provider credentials. Enter a new value to replace a stored key, or leave it blank to keep the current one.
- Back up the SQLite database and encryption key together. If the key is lost, encrypted credentials must be entered again.
- Keep the API bound to loopback unless you add authentication and tighten CORS.
- Never commit API keys, local settings, transcripts, or generated environment files.
- The repository ignores local SQLite files, encryption keys, `.env` files, virtual environments, caches, and build output.

## Limitations

The following surfaces are present but should not be mistaken for completed infrastructure:

- **No authentication or authorization:** The API is intended for one local user.
- **Single-user local storage:** SQLite improves restart durability, but authentication, ownership, backups, and multi-instance coordination are still pending.
- **No real computer runtime:** The Computer tab is a visual preview; this repository does not provision a browser desktop or provide a working VNC session.
- **No durable memory or routines:** Conversations persist, but there is no separate memory store, scheduled routine engine, or background worker yet.
- **No voice or multi-client apps:** Voice, desktop, and mobile clients are not included in this repository.
- **Workspace tools are intentionally narrow:** The first tool loop supports confined file listing, reads, and writes only. Arbitrary shell commands, browser control, and background agents are not implemented.
- **Connector actions are intentionally narrow:** Chat currently exposes only GitHub issue listing and approval-gated issue creation. Dynamic tool discovery, arbitrary connector calls, and other connector writes remain roadmap work.
- **Provider streaming is adapter-level:** Depending on the provider response, the service may receive a completed result and emit it to the UI in small deltas.
- **No CI workflow is included yet:** Focused workspace and approval tests are present, but broader API, provider, and browser tests remain to be added.

## Development

Available client scripts:

```bash
cd client
npm run dev       # Start the development server
npm run build     # Create a production build
npm run start     # Serve the production build
npm run lint      # Run the configured Next.js lint command
```

Run the focused backend tests with:

```bash
DATA_DIR=/tmp/open-grok-bot-test-data PYTHONPATH=server python -m unittest discover -s server/tests -v
```

When changing an API contract, update the Pydantic schema, router, client helper, tests, and this README together.

## Troubleshooting

### The UI says the API is offline

Confirm that the FastAPI server is running on port 8000, then check:

```bash
curl http://127.0.0.1:8000/api/v1/health
```

If the server runs on another host or port, set `NEXT_PUBLIC_API_URL` before starting the client.

### The chat returns a provider error

Check the key in App Settings, verify `MUAPI_BASE_URL`, and make sure the selected model ID is supported by that provider endpoint.

### Image uploads do not produce a hosted URL

The backend falls back to a base64 data URL for local previews when no usable provider key is configured or the provider upload request fails.

## Contributing

Focused issues and pull requests are welcome. Before opening a change:

- Keep setup and behavior documentation synchronized with the code.
- Do not include secrets, personal data, or local transcripts.
- Explain changes to provider behavior, API contracts, or persistence.
- Run the client checks that apply to your change.

## License

This repository does not currently include a license file. Add an explicit license before distributing it as a reusable package.
