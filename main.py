import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from langchain_openai import ChatOpenAI
import config
import httpx

_lightrag_token: str | None = None


async def _ensure_lightrag_auth() -> str:
    """Логинится в LightRAG и возвращает access_token."""
    global _lightrag_token
    if _lightrag_token:
        return _lightrag_token

    url = config.LIGHTRAG_API_URL.rstrip("/")
    data = {
        "username": "admin",
        "password": "admin",
        "grant_type": "password",
    }

    async with httpx.AsyncClient(base_url=url, timeout=15) as client:
        resp = await client.post("/login", data=data)
        resp.raise_for_status()
        data = resp.json()
        _lightrag_token = data["access_token"]
        logger.info("LightRAG auth OK")
    return _lightrag_token


def _lightrag_client(timeout: float = 120) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=config.LIGHTRAG_API_URL.rstrip("/"),
        timeout=timeout,
        headers={"Authorization": f"Bearer {_lightrag_token}"},
    )

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_llm_cache: ChatOpenAI | None = None


def get_llm() -> ChatOpenAI:
    """Returns a cached ChatOpenAI instance configured from config."""
    global _llm_cache
    if _llm_cache is None:
        _llm_cache = ChatOpenAI(
            model=config.LLM_MODEL,
            openai_api_key=config.OPENAI_API_KEY,
            openai_api_base=config.OPENAI_BASE_URL,
        )
    return _llm_cache


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Hello! I'm a RAG bot.\n\n"
        "📄 Upload a text document (up to 10 KB) — I'll index it.\n"
        "💬 Ask a question — I'll answer based on the document content.\n\n"
        "Or /clear to delete all data."
    )


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear the LightRAG workspace data."""

    try:
        _lightrag_token = await _ensure_lightrag_auth()
        async with _lightrag_client(timeout=30) as client:
            resp = await client.delete("/documents")
            resp.raise_for_status()
            await update.message.reply_text("✅ Данные LightRAG очищены.")
    except Exception as e:
        logger.error("Clear failed: %s", e)
        await update.message.reply_text("Не удалось подключиться к LightRAG.")


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Accepts a text document and loads it into LightRAG."""
    file = update.message.document

    # Check if it's a text file
    if not file.mime_type or not file.mime_type.startswith("text/"):
        # Also accept .txt, .md, etc.
        if not file.file_name or not any(
            file.file_name.endswith(ext)
            for ext in (".txt", ".md", ".py", ".csv", ".json", ".html", ".xml", ".log")
        ):
            await update.message.reply_text("Please upload a text file (.txt, .md, etc.)")
            return

    # 10 KB limit
    if file.file_size and file.file_size > 10_000:
        await update.message.reply_text("File is too large (max 10 KB).")
        return

    try:
        telegram_file = await context.bot.get_file(file.file_id)
        content = await telegram_file.download_as_bytearray()
    except Exception as e:
        logger.error("File download failed: %s", e)
        await update.message.reply_text("Ошибка при скачивании файла. Попробуйте позже.")
        return

    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        await update.message.reply_text("Failed to read file as UTF-8.")
        return

    if not text.strip():
        await update.message.reply_text("File is empty.")
        return

    # Load into LightRAG
    try:
        payload = {
            "text": text,
            "file_source": file.file_name or "telegram_document",
            "chunking": {
                "strategy": "fixed_token",
                "params": {
                    "chunk_token_size": 1200,
                    "chunk_overlap_token_size": 100,
                    "split_by_character_only": False,
                },
            },
        }

        async with _lightrag_client(timeout=120) as client:
            resp = await client.post("/documents/text", json=payload)
            resp.raise_for_status()
    except Exception as e:
        logger.error("Document indexing failed: %s", e)
        await update.message.reply_text("Ошибка при индексации документа. Попробуйте позже.")
        return
    await update.message.reply_text(
        f"✅ Document '{file.file_name}' processed.\n"
        f"Size: {len(text)} characters.\n"
        f"You can now ask questions!"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Processes user questions via LightRAG."""
    query = update.message.text.strip()
    if not query:
        return

    # Auth + Health check
    try:
        await _ensure_lightrag_auth()
        async with _lightrag_client(timeout=10) as client:
            resp = await client.get("/health")
            resp.raise_for_status()
    except Exception as e:
        logger.error("Health check failed: %s", e)
        await update.message.reply_text(
            "LightRAG недоступен. Попробуйте позже."
        )
        return

    # Query LightRAG
    try:
        await _ensure_lightrag_auth()
        async with _lightrag_client(timeout=120) as client:
            resp = await client.post(
                "/query",
                json={"query": query, "mode": "hybrid"},
            )
            resp.raise_for_status()
            data = resp.json()
            logger.info("LightRAG query response: %s", data)  # для отладки
    except Exception as e:
        logger.error("Query failed: %s", e)
        await update.message.reply_text("Ошибка при поиске. Попробуйте позже.")
        return

    answer = data.get("response") or ""
    references = data.get("references") or []

    if isinstance(references, str):
        references = [references]

    sources = []
    for ref in references:
        if isinstance(ref, dict):
            content = ref.get("content")
            if content is None:
                continue
            if isinstance(content, str):
                sources.append(content)
            elif isinstance(content, list):
                sources.extend(str(c) for c in content if c is not None)
        elif ref is not None:
            sources.append(str(ref))

    # Если LightRAG уже вернул готовый ответ — используем его
    if answer and answer.strip():
        await update.message.reply_text(answer)
        return

    # Если есть sources — строим ответ через LLM
    if sources:
        context_text = "\n\n---\n\n".join(sources)
        prompt = (
            f"Answer the question using only the following context:\n\n"
            f"<context>\n{context_text}\n</context>\n\n"
            f"Question: {query}\n\n"
            f"If the context doesn't contain an answer, say: "
            f"'No information about this in the loaded document.'"
        )
        llm = get_llm()
        try:
            response = llm.invoke(prompt)
            answer = response.content if hasattr(response, "content") else str(response)
            await update.message.reply_text(answer)
        except Exception as e:
            logger.error("LLM invocation failed: %s", e)
            await update.message.reply_text("Ошибка при обработке запроса. Попробуйте позже.")
        return

    # Ничего не найдено
    await update.message.reply_text(
        "Ничего не найдено. Загрузите текстовый файл для индексации."
    )


def main() -> None:
    app = ApplicationBuilder().token(config.TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot started. Waiting for documents and questions...")
    app.run_polling()


if __name__ == "__main__":
    main()
