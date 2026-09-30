# Telegram Bot with Graph RAG (LightRAG)

Telegram bot for uploading text documents and querying them via Graph RAG (LightRAG).

## Features

- Upload text files (.txt, .md, .py, .csv, .json, .html, .xml, .log) up to 10 KB
- Free-form questions over uploaded documents
- Graph RAG via LightRAG API (hybrid query)
- Clear all data (`/clear`)

## Requirements

- Python 3.10+
- Running LightRAG server (default `http://localhost:9621`)
- OpenAI-compatible API key

## Installation

```bash
pip install -r requirements.txt
```

## Setup

Copy `.env.example` to `.env` and fill in:

```env
# Telegram Bot Token (from @BotFather)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# LightRAG Server
LIGHTRAG_API_URL=http://localhost:9621

# OpenAI-compatible API
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=your_openai_api_key_here

# LLM Model
LLM_MODEL=gpt-4o-mini
```

## Running

```bash
python main.py
```


## Bot Commands

| Command / Action | Description |
|---|---|
| `/start` | Greeting and instructions |
| `/clear` | Clear all LightRAG data |
| Send a file | Upload a text document for indexing |
| Send text | Ask a question about uploaded documents |

## Architecture

```
Telegram Bot
    ├── python-telegram-bot  →  message handler
    ├── httpx               →  LightRAG API (auth, upload, query)
    └── langchain-openai    →  LLM for answer generation
```

The bot authenticates with LightRAG via login/password, uploads documents through `/documents/text`, and performs hybrid queries via `/query`. If LightRAG returns a direct answer, it is sent as-is; otherwise the retrieved context is processed through the LLM.

## Dependencies

| Package | Version |
|---|---|
| python-telegram-bot | 21.9 |
| langchain | 0.3.13 |
| langchain-community | 0.3.12 |
| langchain-openai | 0.3.0 |
| openai | 1.58.1 |
| tiktoken | 0.8.0 |
| python-dotenv | 1.0.1 |
| httpx | 0.28.1 |
