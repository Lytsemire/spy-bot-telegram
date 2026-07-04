from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, Message

from app.keyboards import lobby_kb
from app.models import Room
from app.storage import storage

router = Router()


def lobby_text(room: Room) -> str:
    players_list = "\n".join(
        f"• {p.name}{' 👑' if p.is_host else ''}" for p in room.players.values()
    ) or "пока никого"

    target = room.settings.num_players
    joined = len(room.playing_players())

    return (
        f"🔑 Код комнаты: <code>{room.code}</code>\n"
        f"👥 Игроков: {joined}/{target}\n"
        f"🕵️ Шпионов: {room.settings.num_spies}\n\n"
        f"<b>Участники:</b>\n{players_list}\n\n"
        "Отправь код друзьям, чтобы они подключились командой:\n"
        f"<code>/start {room.code}</code>\n"
        "или кнопкой «Присоединиться по коду» в главном меню."
    )


def _kb_for(room: Room, uid: int):
    return lobby_kb(is_host=(uid == room.host_id), ready=room.is_full())


async def render_lobby(message: Message, room: Room, edit: bool = False) -> None:
    """Показывает текущему пользователю (message.from_user) актуальный вид
    комнаты с правильной клавиатурой (кнопка "Начать игру" — только у хоста
    и только когда комната заполнена)."""
    text = lobby_text(room)
    kb = _kb_for(room, message.from_user.id)

    if edit:
        await message.edit_text(text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)


async def notify_others_joined(bot: Bot, room: Room, joined_user_id: int, joined_name: str) -> None:
    """Рассылает остальным участникам актуальный вид комнаты — КАЖДОМУ со
    своей клавиатурой (важно: раньше здесь уходил обычный текст без кнопок,
    из-за чего хост не видел "Начать игру", когда комната заполнялась)."""
    text = f"🔔 {joined_name} присоединился к комнате!\n\n{lobby_text(room)}"
    for uid in room.players:
        if uid == joined_user_id:
            continue
        try:
            await bot.send_message(uid, text, reply_markup=_kb_for(room, uid))
        except Exception:  # noqa: BLE001 - игрок мог заблокировать бота
            pass


@router.message(F.text == "/room")
async def show_room(message: Message) -> None:
    """Показать текущее состояние своей комнаты и актуальные кнопки —
    полезно, если кнопка "Начать игру" не появилась сама (например, из-за
    старого сообщения) или просто чтобы свериться с составом."""
    room = storage.get_room_by_user(message.from_user.id)
    if not room:
        await message.answer("Ты не в комнате. Напиши /start, чтобы начать.")
        return
    await render_lobby(message, room, edit=False)


@router.callback_query(F.data == "leave_room")
async def leave_room(callback: CallbackQuery) -> None:
    room = storage.get_room_by_user(callback.from_user.id)
    if not room:
        await callback.answer("Ты не в комнате.")
        return

    was_host = callback.from_user.id == room.host_id
    room.players.pop(callback.from_user.id, None)
    storage.user_room.pop(callback.from_user.id, None)
    await callback.message.edit_text("Ты вышел из комнаты. Напиши /start, чтобы начать заново.")

    if was_host:
        storage.delete_room(room.code)
        for uid in list(room.players):
            try:
                await callback.bot.send_message(uid, "❌ Хост покинул комнату, игра отменена.")
            except Exception:  # noqa: BLE001
                pass
    else:
        try:
            await callback.bot.send_message(
                room.host_id,
                f"⚠️ {callback.from_user.full_name} покинул комнату.\n\n{lobby_text(room)}",
                reply_markup=_kb_for(room, room.host_id),
            )
        except Exception:  # noqa: BLE001
            pass

    await callback.answer()
