import random
import string
import time
from dataclasses import dataclass, field
from enum import Enum


class GameMode(str, Enum):
    CLASSIC = "classic"        # одно слово на всех, шпион без слова
    ROLES = "roles"            # локация + уникальные роли (аналог Spyfall)
    TWO_WORD = "two_word"      # "двойной агент" — у части игроков другое слово
    HOST_LED = "host_led"      # ведущий сам загадывает слово и не играет


class GameFormat(str, Enum):
    OFFLINE = "offline"                # все в одной комнате, голосуют вживую
    ONLINE_TURNS = "online_turns"      # бот следит за очередью высказываний
    ONLINE_VOTING = "online_voting"    # общаются вовне (например, в Discord), голосуют через бота


class RoomStatus(str, Enum):
    SETUP = "setup"
    LOBBY = "lobby"
    IN_PROGRESS = "in_progress"
    VOTING = "voting"
    FINISHED = "finished"


@dataclass
class Player:
    user_id: int
    name: str
    is_host: bool = False
    is_spy: bool = False
    is_agent: bool = False       # для режима "двойной агент" (агент = второй "шпион")
    word: str | None = None      # слово / роль, которые видит игрок
    vote_for: int | None = None  # user_id того, за кого проголосовал


@dataclass
class RoomSettings:
    num_players: int = 5
    num_spies: int = 1
    mode: GameMode = GameMode.CLASSIC
    game_format: GameFormat = GameFormat.OFFLINE
    category: str = ""


def generate_room_code(length: int = 6) -> str:
    alphabet = string.ascii_uppercase + string.digits
    # убираем визуально неоднозначные символы
    for ch in "O0I1":
        alphabet = alphabet.replace(ch, "")
    return "".join(random.choice(alphabet) for _ in range(length))


@dataclass
class Room:
    code: str
    host_id: int
    settings: RoomSettings = field(default_factory=RoomSettings)
    players: dict[int, Player] = field(default_factory=dict)
    status: RoomStatus = RoomStatus.SETUP
    secret_word: str | None = None
    agent_word: str | None = None
    location: str | None = None
    created_at: float = field(default_factory=time.time)
    turn_order: list[int] = field(default_factory=list)
    current_turn_idx: int = 0

    def add_player(self, player: Player) -> None:
        self.players[player.user_id] = player

    def playing_players(self) -> list[Player]:
        """Игроки, которые реально получают слово/роль в этом раунде.
        В режиме ведущего сам ведущий не играет и не учитывается."""
        if self.settings.mode == GameMode.HOST_LED:
            return [p for p in self.players.values() if not p.is_host]
        return list(self.players.values())

    def spies(self) -> list[Player]:
        return [p for p in self.players.values() if p.is_spy]

    def is_full(self) -> bool:
        return len(self.playing_players()) >= self.settings.num_players
