"""Простое in-memory хранилище комнат.

Для MVP этого достаточно. Если бот будет перезапускаться часто или
работать на нескольких инстансах — замените на Redis/БД, интерфейс
класса Storage можно оставить тем же.
"""

from app.models import Room


class Storage:
    def __init__(self) -> None:
        self.rooms: dict[str, Room] = {}
        self.user_room: dict[int, str] = {}

    def create_room(self, room: Room) -> None:
        self.rooms[room.code] = room
        self.user_room[room.host_id] = room.code

    def get_room(self, code: str) -> Room | None:
        if not code:
            return None
        return self.rooms.get(code.upper())

    def get_room_by_user(self, user_id: int) -> Room | None:
        code = self.user_room.get(user_id)
        return self.rooms.get(code) if code else None

    def join_room(self, code: str, user_id: int) -> Room | None:
        room = self.get_room(code)
        if room:
            self.user_room[user_id] = room.code
        return room

    def delete_room(self, code: str) -> None:
        room = self.rooms.pop(code, None)
        if room:
            for uid in list(room.players.keys()):
                self.user_room.pop(uid, None)


storage = Storage()
