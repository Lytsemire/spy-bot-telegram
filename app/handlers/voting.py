from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, Message

from app.keyboards import voting_kb
from app.models import Room, RoomStatus
from app.storage import storage

router = Router()


@router.message(F.text == "/vote")
async def start_voting(message: Message) -> None:
    room = storage.get_room_by_user(message.from_user.id)
    if not room or room.host_id != message.from_user.id:
        await message.answer("Только хост может запустить голосование.")
        return
    if room.status != RoomStatus.IN_PROGRESS:
        await message.answer("Голосование недоступно сейчас.")
        return

    room.status = RoomStatus.VOTING
    for p in room.players.values():
        p.vote_for = None

    for uid, player in room.players.items():
        if player.is_host:
            continue
        try:
            await message.bot.send_message(
                uid,
                "🗳 Голосование началось! Кто, по-твоему, шпион?",
                reply_markup=voting_kb(room, exclude_uid=uid),
            )
        except Exception:  # noqa: BLE001
            pass

    await message.answer("Голосование запущено, ждём голосов от всех игроков.")


@router.callback_query(F.data.startswith("vote:"))
async def cast_vote(callback: CallbackQuery) -> None:
    room = storage.get_room_by_user(callback.from_user.id)
    if not room or room.status != RoomStatus.VOTING:
        await callback.answer("Голосование уже закончилось.", show_alert=True)
        return

    target_uid = int(callback.data.split(":")[1])
    voter = room.players.get(callback.from_user.id)
    if voter is None:
        await callback.answer()
        return

    voter.vote_for = target_uid
    await callback.message.edit_text("✅ Голос принят! Ждём остальных...")
    await callback.answer()

    await _maybe_finish_voting(callback.bot, room)


async def _maybe_finish_voting(bot: Bot, room: Room) -> None:
    voters = [p for p in room.players.values() if not p.is_host]
    if not voters or any(p.vote_for is None for p in voters):
        return

    tally: dict[int, int] = {}
    for p in voters:
        tally[p.vote_for] = tally.get(p.vote_for, 0) + 1

    max_votes = max(tally.values())
    top = [uid for uid, cnt in tally.items() if cnt == max_votes]

    room.status = RoomStatus.FINISHED
    spy_ids = {p.user_id for p in room.spies()}

    civilians_won = len(top) == 1 and top[0] in spy_ids

    accused_names = ", ".join(room.players[uid].name for uid in top if uid in room.players)
    spy_names = ", ".join(room.players[uid].name for uid in spy_ids if uid in room.players) or "—"

    lines = [
        f"• {room.players[uid].name}: {cnt} голос(ов)"
        for uid, cnt in sorted(tally.items(), key=lambda kv: -kv[1])
        if uid in room.players
    ]

    text = (
        "📊 Итоги голосования:\n" + "\n".join(lines) + "\n\n"
        f"🎯 Заподозрен(ы): {accused_names}\n"
        f"🕵️ Настоящий шпион(ы): {spy_names}\n\n"
    )
    text += "🏆 Мирные жители победили!" if civilians_won else "🏆 Шпион(ы) победили!"

    for uid in room.players:
        try:
            await bot.send_message(uid, text)
        except Exception:  # noqa: BLE001
            pass

    storage.delete_room(room.code)
