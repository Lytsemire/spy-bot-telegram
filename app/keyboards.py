from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.config import MAX_PLAYERS, MIN_PLAYERS, suggested_spy_range
from app.game_data import CLASSIC_CATEGORIES, ROLE_LOCATIONS
from app.models import GameFormat, GameMode, Room

MODE_TITLES = {
    GameMode.CLASSIC: "📝 Классика (одно слово)",
    GameMode.ROLES: "🎭 Роли (локация + роли, аналог Spyfall)",
    GameMode.TWO_WORD: "🕵️ Двойной агент (два похожих слова)",
    GameMode.HOST_LED: "👑 Режим ведущего (слово задаёт человек)",
}

FORMAT_TITLES = {
    GameFormat.OFFLINE: "🧑‍🤝‍🧑 Офлайн — все в одной комнате",
    GameFormat.ONLINE_TURNS: "💬 Онлайн — бот следит за очередью",
    GameFormat.ONLINE_VOTING: "🗳 Онлайн — обсуждение вовне + голосование в боте",
}


def main_menu_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🎲 Создать комнату", callback_data="create_room")
    b.button(text="🔑 Присоединиться по коду", callback_data="join_room")
    b.adjust(1)
    return b.as_markup()


def players_count_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for n in range(MIN_PLAYERS, MAX_PLAYERS + 1):
        b.button(text=str(n), callback_data=f"players:{n}")
    b.adjust(4)
    return b.as_markup()


def spies_count_kb(num_players: int) -> InlineKeyboardMarkup:
    lo, hi = suggested_spy_range(num_players)
    b = InlineKeyboardBuilder()
    for n in range(lo, hi + 1):
        b.button(text=f"{n} 🕵️", callback_data=f"spies:{n}")
    b.button(text="🎲 Случайно", callback_data="spies:random")
    b.adjust(3)
    return b.as_markup()


def mode_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for mode, title in MODE_TITLES.items():
        b.button(text=title, callback_data=f"mode:{mode.value}")
    b.adjust(1)
    return b.as_markup()


def category_kb(mode: GameMode) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    source = ROLE_LOCATIONS if mode == GameMode.ROLES else CLASSIC_CATEGORIES
    for key, data in source.items():
        b.button(text=data["title"], callback_data=f"category:{key}")
    b.button(text="🎲 Случайная категория", callback_data="category:random")
    b.adjust(1)
    return b.as_markup()


def format_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for fmt, title in FORMAT_TITLES.items():
        b.button(text=title, callback_data=f"format:{fmt.value}")
    b.adjust(1)
    return b.as_markup()


def confirm_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✅ Захостить игру", callback_data="host_confirm")
    b.button(text="✏️ Начать заново", callback_data="create_room")
    b.adjust(1)
    return b.as_markup()


def lobby_kb(is_host: bool, ready: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if is_host and ready:
        b.button(text="🚀 Начать игру", callback_data="start_game")
    b.button(text="🚪 Выйти из комнаты", callback_data="leave_room")
    b.adjust(1)
    return b.as_markup()


def spy_action_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🤫 Я знаю слово!", callback_data="spy_guess")
    b.adjust(1)
    return b.as_markup()


def voting_kb(room: Room, exclude_uid: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for uid, player in room.players.items():
        if uid == exclude_uid or player.is_host:
            continue
        b.button(text=player.name, callback_data=f"vote:{uid}")
    b.adjust(1)
    return b.as_markup()
