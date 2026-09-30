# Telegram Bot с Graph RAG (LightRAG)

Telegram-бот для загрузки текстовых документов и вопросов по ним через Graph RAG (LightRAG).

## Возможности

- Загрузка текстовых файлов (.txt, .md, .py, .csv, .json, .html, .xml, .log) до 10 КБ
- Вопросы по загруженным документам в свободной форме
- Графовый RAG через LightRAG API (hybrid query)
- Очистка всех данных (`/clear`)

## Требования

- Python 3.10+
- Запущенный LightRAG сервер (по умолчанию `http://localhost:9621`)
- OpenAI-compatible API ключ

## Установка

```bash
pip install -r requirements.txt
```

## Настройка

Скопируйте `.env.example` в `.env` и заполните:

```env
# Telegram Bot Token (от @BotFather)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# LightRAG Server
LIGHTRAG_API_URL=http://localhost:9621

# OpenAI-compatible API
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=your_openai_api_key_here

# LLM модель
LLM_MODEL=gpt-4o-mini
```

## Запуск

```bash
python main.py
```

Или через `run.sh` (с SOCKS-прокси):

```bash
chmod +x run.sh
./run.sh
```

## Команды бота

| Команда / действие | Описание |
|---|---|
| `/start` | Приветствие и инструкция |
| `/clear` | Очистить все данные LightRAG |
| Отправка файла | Загрузить текстовый документ для индексации |
| Текстовое сообщение | Задать вопрос по загруженным документам |

## Архитектура

```
Telegram Bot
    ├── python-telegram-bot  →  обработчик сообщений
    ├── httpx               →  LightRAG API (auth, upload, query)
    └── langchain-openai    →  LLM для генерации ответов
```

Бот аутентифицируется в LightRAG по логину/паролю, загружает документы через `/documents/text` и выполняет hybrid-запросы через `/query`. Если LightRAG возвращает готовый ответ — он отправляется напрямую; иначе контекст из источников обрабатывается через LLM.

## Зависимости

| Пакет | Версия |
|---|---|
| python-telegram-bot | 21.9 |
| langchain | 0.3.13 |
| langchain-community | 0.3.12 |
| langchain-openai | 0.3.0 |
| openai | 1.58.1 |
| tiktoken | 0.8.0 |
| python-dotenv | 1.0.1 |
| httpx | 0.28.1 |
