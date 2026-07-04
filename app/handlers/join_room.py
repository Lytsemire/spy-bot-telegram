from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.handlers.lobby import notify_others_joined, render_lobby
from app.models import GameMode, Player, RoomStatus
from app.states import JoinRoom
from app.storage import storage

router = Router()


@router.callback_query(F.data == "join_room")
async def join_room_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(JoinRoom.waiting_code)
    await callback.message.edit_text("Введи код комнаты (например, AB12CD):")
    await callback.answer()


@router.message(JoinRoom.waiting_code)
async def join_room_code(message: Message, state: FSMContext) -> None:
    code = (message.text or "").strip().upper()
    await try_join_room(message, code, state)


async def try_join_room(message: Message, code: str, state: FSMContext) -> None:
    await state.clear()

    room = storage.get_room(code) if code else None
    if not room:
        await message.answer("❌ Комната с таким кодом не найдена. Проверь код и попробуй снова.")
        return

    if room.status not in (RoomStatus.LOBBY, RoomStatus.SETUP):
        await message.answer("⚠️ Игра в этой комнате уже началась или завершена.")
        return

    user = message.from_user
    newly_joined = False
    if user.id in room.players:
        await message.answer("Ты уже в этой комнате 👌")
    else:
        max_capacity = room.settings.num_players + (1 if room.settings.mode == GameMode.HOST_LED else 0)
        if len(room.players) >= max_capacity:
            await message.answer("😔 Комната уже заполнена.")
            return
        room.add_player(Player(user_id=user.id, name=user.full_name))
        storage.join_room(code, user.id)
        newly_joined = True

    await render_lobby(message, room, edit=False)

    if newly_joined:
        await notify_others_joined(message.bot, room, joined_user_id=user.id, joined_name=user.full_name)
