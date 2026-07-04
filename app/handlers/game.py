from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from app.game_logic import start_game as run_game_logic
from app.images import get_image_for_word, get_spy_image
from app.keyboards import spy_action_kb
from app.models import GameFormat, GameMode, Room, RoomStatus
from app.states import SpyGuess
from app.storage import storage

router = Router()


@router.callback_query(F.data == "start_game")
async def start_game_cb(callback: CallbackQuery) -> None:
    room = storage.get_room_by_user(callback.from_user.id)
    if not room or room.host_id != callback.from_user.id:
        await callback.answer("Только хост может начать игру.", show_alert=True)
        return
    if not room.is_full():
        await callback.answer("Ещё не все игроки подключились.", show_alert=True)
        return

    run_game_logic(room)
    room.status = RoomStatus.IN_PROGRESS
    await callback.answer("Игра началась! Карточки разосланы в личные сообщения 📨")
    await deliver_cards(callback.bot, room)


async def deliver_cards(bot: Bot, room: Room) -> None:
    spy_image_bytes: bytes | None = None
    word_image_cache: dict[str, bytes] = {}

    for uid, player in room.players.items():
        if player.is_host and room.settings.mode == GameMode.HOST_LED:
            await _safe_send(
                bot, uid,
                "👑 Ты ведущий. Ты не участвуешь в раунде — просто следи за игрой "
                "и, если нужно, помоги с голосованием (команда /vote) или "
                "объяви результат вручную и заверши игру командой /reveal.",
            )
            continue

        if player.is_spy and not player.is_agent:
            if spy_image_bytes is None:
                spy_image_bytes = await get_spy_image()
            caption = "🕵️ Ты — ШПИОН!\nСлушай внимательно и постарайся не выдать себя."
            if room.settings.mode == GameMode.ROLES:
                caption += "\nЛокацию тебе не сообщаю — угадывай по вопросам остальных."
            await _safe_send_photo(bot, uid, spy_image_bytes, "spy.png", caption, spy_action_kb())
        else:
            word = player.word or "—"
            if word not in word_image_cache:
                word_image_cache[word] = await get_image_for_word(word)

            if room.settings.mode == GameMode.ROLES and room.location:
                caption = f"📍 Локация: <b>{room.location}</b>\n🎭 Твоя роль: <b>{word}</b>"
            else:
                caption = f"📝 Твоё слово: <b>{word}</b>"

            if player.is_agent:
                caption += (
                    "\n\n🤐 Обращай внимание на вопросы — возможно, у кого-то "
                    "здесь другое слово, чем у большинства."
                )

            await _safe_send_photo(bot, uid, word_image_cache[word], "word.png", caption)

    await _announce_format(bot, room)


async def _announce_format(bot: Bot, room: Room) -> None:
    fmt = room.settings.game_format
    if fmt == GameFormat.OFFLINE:
        note = (
            "🧑‍🤝‍🧑 Формат: офлайн.\n"
            "Обсуждайте вслух и в конце просто укажите пальцем на подозреваемого — "
            "бот тут не нужен.\n"
            "Хост может в любой момент завершить раунд и раскрыть шпиона командой /reveal."
        )
    elif fmt == GameFormat.ONLINE_TURNS:
        note = (
            "💬 Формат: онлайн по очереди.\n"
            "Команда /next объявляет, чей сейчас ход (используйте в общем чате, где всем видно).\n"
            "Когда готовы голосовать — хост запускает /vote."
        )
    else:
        note = (
            "🗳 Формат: онлайн с голосованием.\n"
            "Обсуждайте где вам удобно (например, в общем голосовом чате), "
            "а когда решите вычислить шпиона — хост запускает команду /vote, "
            "и каждый анонимно голосует прямо здесь, в этом чате с ботом."
        )

    for uid in room.players:
        await _safe_send(bot, uid, note)


@router.callback_query(F.data == "spy_guess")
async def spy_guess_start(callback: CallbackQuery, state: FSMContext) -> None:
    room = storage.get_room_by_user(callback.from_user.id)
    if not room or room.status != RoomStatus.IN_PROGRESS:
        await callback.answer("Сейчас нельзя это сделать.", show_alert=True)
        return
    await state.set_state(SpyGuess.waiting_guess)
    await callback.message.answer("Напиши слово, которое, как ты думаешь, было загадано:")
    await callback.answer()


@router.message(SpyGuess.waiting_guess)
async def spy_guess_answer(message: Message, state: FSMContext) -> None:
    await state.clear()
    room = storage.get_room_by_user(message.from_user.id)
    if not room or room.status != RoomStatus.IN_PROGRESS:
        return

    guess = (message.text or "").strip()
    actual = room.secret_word or room.location or ""
    correct = guess.strip().lower() == actual.strip().lower()

    room.status = RoomStatus.FINISHED
    result_text = (
        f"🕵️ {message.from_user.full_name} объявил: «Я знаю слово!»\n"
        f"Его вариант: <b>{guess}</b>\n"
        f"Правильный ответ: <b>{actual}</b>\n\n"
    )
    result_text += (
        "🏆 Шпион угадал и ПОБЕДИЛ!" if correct else "❌ Шпион ошибся — победили мирные жители!"
    )

    for uid in room.players:
        await _safe_send(message.bot, uid, result_text)

    storage.delete_room(room.code)


@router.message(F.text == "/next")
async def next_turn(message: Message) -> None:
    room = storage.get_room_by_user(message.from_user.id)
    if not room or room.status != RoomStatus.IN_PROGRESS:
        await message.answer("Нет активной игры.")
        return
    if room.settings.game_format != GameFormat.ONLINE_TURNS:
        await message.answer("Команда /next доступна только в формате «онлайн по очереди».")
        return

    if not room.turn_order:
        room.turn_order = [uid for uid, p in room.players.items() if not p.is_host]

    if not room.turn_order:
        await message.answer("В комнате нет игроков для очереди.")
        return

    current_uid = room.turn_order[room.current_turn_idx % len(room.turn_order)]
    room.current_turn_idx += 1
    name = room.players[current_uid].name
    await message.answer(f"🎙 Слово участнику: <b>{name}</b>\n(следующий ход — команда /next)")


@router.message(F.text == "/reveal")
async def reveal(message: Message) -> None:
    room = storage.get_room_by_user(message.from_user.id)
    if not room or room.host_id != message.from_user.id:
        await message.answer("Только хост может завершить игру этой командой.")
        return
    if room.status != RoomStatus.IN_PROGRESS:
        await message.answer("Игра сейчас не идёт.")
        return

    room.status = RoomStatus.FINISHED
    spy_names = ", ".join(p.name for p in room.spies()) or "—"
    answer = room.secret_word or room.location or "—"
    text = (
        "🎭 Игра завершена хостом.\n"
        f"🕵️ Шпион(ы): {spy_names}\n"
        f"📝 Слово/локация: {answer}"
    )
    for uid in room.players:
        await _safe_send(message.bot, uid, text)
    storage.delete_room(room.code)


async def _safe_send(bot: Bot, uid: int, text: str) -> None:
    try:
        await bot.send_message(uid, text)
    except Exception:  # noqa: BLE001 - игрок мог заблокировать бота
        pass


async def _safe_send_photo(bot: Bot, uid: int, photo_bytes: bytes, filename: str, caption: str, kb=None) -> None:
    try:
        await bot.send_photo(
            uid,
            BufferedInputFile(photo_bytes, filename=filename),
            caption=caption,
            reply_markup=kb,
        )
    except Exception:  # noqa: BLE001
        pass
