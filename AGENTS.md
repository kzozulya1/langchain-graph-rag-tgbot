# Repository Guidelines

## Project Overview

Telegram bot that accepts text documents for indexing into a LightRAG (graph-based RAG) server, then answers user questions over those documents using hybrid graph retrieval + LLM generation. Pure Python, no TypeScript/Node tooling.

## Architecture & Data Flow

```
User (Telegram) → python-telegram-bot → main.py → httpx → LightRAG server (localhost:9621)
                                                        ↓
                                              ChatOpenAI (langchain-openai)
```

**Three layers:**

1. **Telegram bridge** — `python-telegram-bot` v21.9 (`ApplicationBuilder`). Handles `/start`, `/clear`, document uploads, and text queries.
2. **LightRAG HTTP client** — `httpx.AsyncClient` with Bearer auth. Endpoints: `/login`, `/documents/text`, `/query`, `/health`, `/documents` (DELETE).
3. **LLM** — `langchain-openai` `ChatOpenAI` (lazy singleton). Used directly via `.invoke()` — no LangChain RAG chains.

**Data flow:**

- **Document upload**: User sends file → validate mime/extension/size → download → `POST /documents/text` with fixed_token chunking (1200 tokens, 100 overlap) → LightRAG indexes into graph DB.
- **Query**: User sends text → `GET /health` → `POST /query {query, mode: hybrid}` → if direct answer exists, send it; if sources exist, build context → `ChatOpenAI.invoke()` → send synthesized answer; else "nothing found".
- **Clear**: `DELETE /documents` → wipes all LightRAG workspace data.

## Key Directories

| Path | Purpose |
|------|---------|
| `main.py` | Single-file application (251 lines): all bot handlers, LightRAG client, LLM factory |
| `config.py` | Thin `os.getenv` wrapper loaded via `python-dotenv` |
| `.env.example` | Template for TELEGRAM_BOT_TOKEN, LIGHTRAG_API_URL, OPENAI_BASE_URL, OPENAI_API_KEY, LLM_MODEL |
| `requirements.txt` | 8 deps: python-telegram-bot, langchain family, openai, tiktoken, python-dotenv, httpx |
| `README.md` | Russian-language documentation only |

## Development Commands

```bash
# Run the bot
python main.py

# Install dependencies
pip install -r requirements.txt
```

No build step, no linting, no formatting tooling, no CI/CD.

## Code Conventions & Common Patterns

- **Async-first**: All handlers `async def`, `httpx.AsyncClient` throughout.
- **Module-level globals**: `_llm_cache` and `_lightrag_token` as global singletons.
- **Minimal config**: Flat `os.getenv` in `config.py`, no Pydantic models.
- **Error handling**: `try/except` around every external call (Telegram API, LightRAG HTTP, LLM API) with Russian user-facing messages + Python `logging`.
- **No LangChain chains**: `ChatOpenAI` used directly via `.invoke(prompt)`, not LangChain pipelines.
- **Hardcoded credentials**: LightRAG login `admin/admin` not from config (in `_ensure_lightrag_auth`).
- **No input validation framework**: Manual `if` statements for file checks.
- **Token refresh missing**: `_lightrag_token` never invalidated.
- **Stateless**: Each message is independent; no conversation context.

## Important Files

| File | Role |
|------|------|
| `main.py` | Entry point — all bot logic in one file |
| `config.py` | Environment variable loading |
| `requirements.txt` | Dependency list |
| `run.sh` | Proxy-aware launcher |
| `.env.example` | Config template |
| `README.md` | User docs (Russian) |

## Runtime/Tooling Preferences

- **Runtime**: CPython (no Bun/Node).
- **Package manager**: `pip` (no `pipenv`, `poetry`, `uv`).
- **No TypeScript, no JS tooling**: Pure Python project.
- **No containerization**: No Dockerfile or docker-compose.
- **No linting/formatting**: No `flake8`, `black`, `ruff`, `mypy`.
- **LightRAG server required**: External dependency on `localhost:9621` (default).

## Testing & QA

- **No tests exist**: Zero test files, no `pytest`, no `unittest`.
- **No coverage tooling**: No `coverage.py`, no `pytest-cov`.
- **No CI/CD**: No GitHub Actions, no CI pipeline.

To add testing, the project would need:
- `pytest` + `pytest-asyncio` (bot is async)
- Refactor `main.py` to extract testable modules (currently tightly coupled to `telegram.ext` and `httpx`)
- `tests/` directory with `conftest.py` for fixtures
- `pytest.ini` or `pyproject.toml` for async test support
- Mocking strategy for Telegram API, httpx LightRAG calls, and LLM API
