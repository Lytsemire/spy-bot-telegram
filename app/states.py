from aiogram.fsm.state import State, StatesGroup


class CreateRoom(StatesGroup):
    players = State()
    spies = State()
    mode = State()
    category = State()
    game_format = State()
    confirm = State()


class HostWord(StatesGroup):
    waiting_word = State()


class JoinRoom(StatesGroup):
    waiting_code = State()


class SpyGuess(StatesGroup):
    waiting_guess = State()
