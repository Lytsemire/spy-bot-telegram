import random

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.config import suggested_spy_range
from app.game_data import CLASSIC_CATEGORIES, ROLE_LOCATIONS
from app.handlers.lobby import render_lobby
from app.keyboards import (
    FORMAT_TITLES,
    MODE_TITLES,
    category_kb,
    confirm_kb,
    format_kb,
    mode_kb,
    players_count_kb,
    spies_count_kb,
)
from app.models import GameFormat, GameMode, Player, Room, RoomSettings, RoomStatus, generate_room_code
from app.states import CreateRoom, HostWord
from app.storage import storage

router = Router()


@router.callback_query(F.data == "create_room")
async def create_room_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(CreateRoom.players)
    await callback.message.edit_text(
        "Сколько игроков будет участвовать? (от 3 до 15)\n"
        "Хост тоже считается игроком, кроме режима «Ведущий».",
        reply_markup=players_count_kb(),
    )
    await callback.answer()


@router.callback_query(CreateRoom.players, F.data.startswith("players:"))
async def choose_players(callback: CallbackQuery, state: FSMContext) -> None:
    n = int(callback.data.split(":")[1])
    await state.update_data(num_players=n)
    await state.set_state(CreateRoom.spies)
    lo, hi = suggested_spy_range(n)
    await callback.message.edit_text(
        f"👥 Игроков: {n}\n\nСколько шпионов? (по правилам рекомендуется {lo}-{hi})",
        reply_markup=spies_count_kb(n),
    )
    await callback.answer()


@router.callback_query(CreateRoom.spies, F.data.startswith("spies:"))
async def choose_spies(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[1]
    data = await state.get_data()
    n = data["num_players"]

    if value == "random":
        lo, hi = suggested_spy_range(n)
        num_spies = random.randint(lo, hi)
    else:
        num_spies = int(value)

    await state.update_data(num_spies=num_spies)
    await state.set_state(CreateRoom.mode)
    await callback.message.edit_text(
        f"🕵️ Шпионов: {num_spies}\n\nВыбери режим игры:",
        reply_markup=mode_kb(),
    )
    await callback.answer()


@router.callback_query(CreateRoom.mode, F.data.startswith("mode:"))
async def choose_mode(callback: CallbackQuery, state: FSMContext) -> None:
    mode = GameMode(callback.data.split(":")[1])
    await state.update_data(mode=mode.value)

    if mode == GameMode.HOST_LED:
        await state.set_state(HostWord.waiting_word)
        await callback.message.edit_text(
            "👑 Режим ведущего.\n"
            "Ты не будешь участвовать в раунде — просто следишь за игрой.\n\n"
            "Напиши секретное слово (только ты его увидишь):"
        )
        await callback.answer()
        return

    await state.set_state(CreateRoom.category)
    await callback.message.edit_text(
        f"Режим: {MODE_TITLES[mode]}\n\nВыбери категорию:",
        reply_markup=category_kb(mode),
    )
    await callback.answer()


@router.message(HostWord.waiting_word)
async def receive_host_word(message: Message, state: FSMContext) -> None:
    word = (message.text or "").strip()
    if not word:
        await message.answer("Слово не может быть пустым, попробуй ещё раз:")
        return
    await state.update_data(secret_word=word, category="host_led")
    await state.set_state(CreateRoom.game_format)
    await message.answer(
        "Слово принято ✅ (никому не покажу)\n\nВыбери формат игры:",
        reply_markup=format_kb(),
    )


@router.callback_query(CreateRoom.category, F.data.startswith("category:"))
async def choose_category(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    mode = GameMode(data["mode"])
    key = callback.data.split(":")[1]
    source = ROLE_LOCATIONS if mode == GameMode.ROLES else CLASSIC_CATEGORIES

    if key == "random":
        key = random.choice(list(source.keys()))

    await state.update_data(category=key)
    await state.set_state(CreateRoom.game_format)
    await callback.message.edit_text(
        f"Категория: {source[key]['title']}\n\nВыбери формат игры:",
        reply_markup=format_kb(),
    )
    await callback.answer()


@router.callback_query(CreateRoom.game_format, F.data.startswith("format:"))
async def choose_format(callback: CallbackQuery, state: FSMContext) -> None:
    game_format = GameFormat(callback.data.split(":")[1])
    await state.update_data(game_format=game_format.value)
    data = await state.get_data()

    mode = GameMode(data["mode"])
    if mode == GameMode.HOST_LED:
        category_title = "задаёт ведущий"
    else:
        source = ROLE_LOCATIONS if mode == GameMode.ROLES else CLASSIC_CATEGORIES
        category_title = source[data["category"]]["title"]

    text = (
        "📋 <b>Параметры комнаты</b>\n\n"
        f"👥 Игроков: {data['num_players']}\n"
        f"🕵️ Шпионов: {data['num_spies']}\n"
        f"🎮 Режим: {MODE_TITLES[mode]}\n"
        f"📁 Категория: {category_title}\n"
        f"🌐 Формат: {FORMAT_TITLES[game_format]}\n\n"
        "Всё верно?"
    )
    await callback.message.edit_text(text, reply_markup=confirm_kb())
    await callback.answer()


@router.callback_query(F.data == "host_confirm")
async def host_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    user = callback.from_user

    settings = RoomSettings(
        num_players=data["num_players"],
        num_spies=data["num_spies"],
        mode=GameMode(data["mode"]),
        game_format=GameFormat(data["game_format"]),
        category=data.get("category", ""),
    )

    room = Room(code=generate_room_code(), host_id=user.id, settings=settings, status=RoomStatus.LOBBY)
    if settings.mode == GameMode.HOST_LED:
        room.secret_word = data.get("secret_word")

    room.add_player(Player(user_id=user.id, name=user.full_name, is_host=True))
    storage.create_room(room)

    await state.clear()
    await render_lobby(callback.message, room, edit=True)
    await callback.answer()
