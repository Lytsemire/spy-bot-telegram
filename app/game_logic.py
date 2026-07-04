import random

from app.game_data import CLASSIC_CATEGORIES, ROLE_LOCATIONS
from app.models import GameMode, Room


def pick_spies(candidate_ids: list[int], num_spies: int) -> set[int]:
    n = min(num_spies, len(candidate_ids))
    return set(random.sample(candidate_ids, n)) if n > 0 else set()


def assign_classic(room: Room) -> None:
    category = CLASSIC_CATEGORIES[room.settings.category]
    word = random.choice(category["words"])
    room.secret_word = word

    playing = room.playing_players()
    spy_ids = pick_spies([p.user_id for p in playing], room.settings.num_spies)

    for uid, player in room.players.items():
        if uid in spy_ids:
            player.is_spy = True
            player.word = None
        elif player in playing:
            player.word = word


def assign_roles_mode(room: Room) -> None:
    location = ROLE_LOCATIONS[room.settings.category]
    room.location = location["title"]

    playing = room.playing_players()
    spy_ids = pick_spies([p.user_id for p in playing], room.settings.num_spies)

    available_roles = location["roles"][:]
    random.shuffle(available_roles)

    for uid, player in room.players.items():
        if uid in spy_ids:
            player.is_spy = True
            player.word = None
        elif player in playing:
            player.word = available_roles.pop() if available_roles else "Гость"


def assign_two_word(room: Room) -> None:
    category = CLASSIC_CATEGORIES[room.settings.category]
    main_word, agent_word = random.sample(category["words"], 2)
    room.secret_word = main_word
    room.agent_word = agent_word

    playing = room.playing_players()
    # здесь "число шпионов" из настроек используется как "число агентов"
    agent_ids = pick_spies([p.user_id for p in playing], room.settings.num_spies)

    for uid, player in room.players.items():
        if uid in agent_ids:
            player.is_spy = True
            player.is_agent = True
            player.word = agent_word
        elif player in playing:
            player.word = main_word


def assign_host_led(room: Room) -> None:
    playing = room.playing_players()  # ведущий уже исключён этим методом
    spy_ids = pick_spies([p.user_id for p in playing], room.settings.num_spies)

    for uid, player in room.players.items():
        if player.is_host:
            continue
        if uid in spy_ids:
            player.is_spy = True
            player.word = None
        else:
            player.word = room.secret_word


def start_game(room: Room) -> None:
    if room.settings.mode == GameMode.CLASSIC:
        assign_classic(room)
    elif room.settings.mode == GameMode.ROLES:
        assign_roles_mode(room)
    elif room.settings.mode == GameMode.TWO_WORD:
        assign_two_word(room)
    elif room.settings.mode == GameMode.HOST_LED:
        assign_host_led(room)
    else:
        raise ValueError(f"Неизвестный режим игры: {room.settings.mode}")
