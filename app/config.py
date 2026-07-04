import os

from dotenv import load_dotenv

# Подхватываем .env независимо от того, как запущен процесс —
# из консоли, из Task Scheduler или из службы (systemd).
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

MIN_PLAYERS = 3
MAX_PLAYERS = 15

# Правила рекомендованного количества шпионов относительно числа игроков
_SPY_RULES = [
    (range(3, 6), (1, 1)),
    (range(6, 11), (1, 2)),
    (range(11, 16), (2, 3)),
]


def suggested_spy_range(players: int) -> tuple[int, int]:
    """Возвращает (мин, макс) рекомендованное количество шпионов для данного
    числа игроков, согласно таблице из правил."""
    for r, bounds in _SPY_RULES:
        if players in r:
            return bounds
    return 1, max(1, players // 5)
