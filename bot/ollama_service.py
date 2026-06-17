from ollama import AsyncClient
import config
import logging

logger = logging.getLogger(__name__)

client = AsyncClient(host=config.OLLAMA_HOST)

def build_messages(history: list, current_text: str) -> list[dict]:
    """Формирует контекст для отправки в Ollama (системный промпт + история + новый запрос)."""
    system = {'role': 'system', 'content': config.OLLAMA_SYSTEM_PROMPT}
    user   = {'role': 'user',   'content': current_text}
    return [system] + history + [user]

async def ask_ollama(messages: list[dict[str,str]]) -> dict:
    try:
        response = await client.chat(
            model=config.OLLAMA_MODEL,
            messages=messages,
            options={
                "temperature": config.OLLAMA_TEMPERATURE,
                "num_ctx": config.OLLAMA_NUM_CTX,
            }
        )
        return response
    except Exception as e:
        logger.error(f"Ошибка при запросе к Ollama: {e}")
        return None