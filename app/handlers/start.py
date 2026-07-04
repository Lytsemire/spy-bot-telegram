from aiogram import Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.keyboards import main_menu_kb

router = Router()


@router.message(CommandStart(deep_link=True))
async def start_with_code(message: Message, command: CommandObject, state: FSMContext) -> None:
    from app.handlers.join_room import try_join_room

    code = (command.args or "").strip().upper()
    await try_join_room(message, code, state)


@router.message(CommandStart())
async def start(message: Message) -> None:
    await message.answer(
        "👋 Привет! Это бот для игры в «Шпиона».\n\n"
        "Собери компанию (от 3 человек) и решите, что делаем:",
        reply_markup=main_menu_kb(),
    )
