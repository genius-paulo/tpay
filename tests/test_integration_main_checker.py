import pytest
from src import main
from loguru import logger


@pytest.mark.asyncio(loop_scope="module")
async def test_bot():
    result_message = await main.bot.send_message(542570177, "Бот работает")
    logger.info(f"Результат: {result_message}")
    assert result_message.message_id is not None
