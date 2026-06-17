# AI-Powered Code Review Agent

An autonomous GitHub bot that reviews pull requests using LLMs (OpenAI, Anthropic Claude, or Ollama locally). Posts structured inline comments back to GitHub automatically.

## Architecture

```
GitHub PR opened
     │
     ▼
FastAPI webhook server  ──► HMAC signature verification
     │
     ▼
Redis job queue (Celery)
     │
     ▼
Celery worker
  ├─ Fetch PR diff from GitHub API
  ├─ Route through LLM provider (OpenAI / Anthropic / Ollama)
  └─ Post structured review comments back to GitHub
     │
     ▼
PostgreSQL (review history)    React dashboard (monitor reviews)
```

## Quick Start

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env — add your GitHub token and LLM API key

# 2. Start everything
docker compose up --build

# 3. Expose your local server (for GitHub webhooks)
ngrok http 8000

# 4. Configure GitHub webhook
# URL: https://<your-ngrok-url>/webhooks/github
# Content type: application/json
# Secret: matches GITHUB_WEBHOOK_SECRET in .env
# Events: Pull requests

# 5. Open a PR — the agent reviews it automatically
```

## Switching LLM Providers

No code changes needed. Just update `.env`:

```bash
# Use Anthropic Claude
ACTIVE_LLM_PROVIDER=anthropic
ACTIVE_LLM_MODEL=claude-sonnet-4-6

# Use local Ollama (free, private)
ACTIVE_LLM_PROVIDER=ollama
ACTIVE_LLM_MODEL=llama3

# Use OpenAI
ACTIVE_LLM_PROVIDER=openai
ACTIVE_LLM_MODEL=gpt-4o
```

Then `docker compose restart worker`.

## Project Structure

```
├── api/                    # FastAPI webhook server
│   ├── core/               # Config, logging
│   ├── llm/                # LLM provider abstraction (Strategy pattern)
│   │   ├── base.py         # Abstract interface
│   │   ├── factory.py      # Provider selection
│   │   ├── openai_provider.py
│   │   ├── anthropic_provider.py
│   │   └── ollama_provider.py
│   ├── models/             # SQLAlchemy database models
│   ├── routers/            # FastAPI route handlers
│   └── services/           # GitHub API client
├── worker/
│   └── tasks.py            # Celery task: fetch diff → review → post
├── dashboard/              # React monitoring UI
├── alembic/                # Database migrations
└── docker-compose.yml
```

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Health check |
| `/webhooks/github` | POST | GitHub webhook receiver |

## Development

```bash
# Run API locally (without Docker)
cd api
pip install -r requirements.txt
uvicorn main:app --reload

# Run worker locally
cd worker
celery -A tasks worker --loglevel=info

# Run database migrations
alembic upgrade head
```

## Key Design Decisions

**Strategy Pattern for LLMs** — `BaseLLMProvider` defines the contract. The worker never imports OpenAI or Anthropic directly — it only calls `get_provider().review(diff, ctx)`. Swapping providers is a config change, not a code change.

**Async-first** — FastAPI + asyncpg + httpx throughout. The webhook handler returns in milliseconds; all heavy work happens in Celery.

**HMAC Verification** — Every webhook is verified with `hmac.compare_digest` to prevent timing attacks. Unsigned requests are rejected with 401.

**Diff Truncation** — Diffs over 15,000 characters are truncated before sending to the LLM to stay within token limits.
