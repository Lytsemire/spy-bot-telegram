import asyncio
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import BOT_TOKEN
from app.handlers import create_room, game, join_room, lobby, start, voting


def setup_logging() -> None:
    """Пишем логи и в консоль, и в файл bot.log — если бот запущен как
    служба/задача Windows без консоли, это единственный способ увидеть,
    что происходит и почему упал."""
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)

    handlers = [
        logging.StreamHandler(),
        RotatingFileHandler(log_dir / "bot.log", maxBytes=5_000_000, backupCount=3, encoding="utf-8"),
    ]
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
    )


async def main() -> None:
    setup_logging()

    if not BOT_TOKEN:
        raise RuntimeError(
            "Переменная окружения BOT_TOKEN не задана. "
            "Получи токен у @BotFather и укажи его в .env"
        )

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    dp.include_router(start.router)
    dp.include_router(create_room.router)
    dp.include_router(join_room.router)
    dp.include_router(lobby.router)
    dp.include_router(game.router)
    dp.include_router(voting.router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
