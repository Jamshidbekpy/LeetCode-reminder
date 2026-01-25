from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional
from redis import Redis

@dataclass
class DailyState:
    date: str                # YYYY-MM-DD (user timezone bo'yicha)
    reminded_times: set[str] # HH:MM
    congrats_sent: bool
    last_lc_check_ts: int    # unix seconds (throttle uchun)

class Storage:
    """
    Redis schema:
    - users set: lc:users -> chat_id lar
    - user config hash: lc:user:{chat_id} -> username, tz, times(json)
    - daily state key: lc:state:{chat_id}:{date} -> json
    """

    def __init__(self, r: Redis):
        self.r = r

    # -------- users registry --------
    def add_user(self, chat_id: int) -> None:
        self.r.sadd("lc:users", str(chat_id))

    def remove_user(self, chat_id: int) -> None:
        self.r.srem("lc:users", str(chat_id))

    def list_users(self) -> list[int]:
        vals = self.r.smembers("lc:users")
        out: list[int] = []
        for v in vals:
            try:
                out.append(int(v.decode() if isinstance(v, bytes) else v))
            except Exception:
                pass
        return sorted(out)

    # -------- user config --------
    def _user_key(self, chat_id: int) -> str:
        return f"lc:user:{chat_id}"

    def set_username(self, chat_id: int, username: str) -> None:
        self.r.hset(self._user_key(chat_id), "username", username)

    def get_username(self, chat_id: int) -> Optional[str]:
        v = self.r.hget(self._user_key(chat_id), "username")
        return (v.decode() if isinstance(v, bytes) else v) if v else None

    def set_timezone(self, chat_id: int, tz: str) -> None:
        self.r.hset(self._user_key(chat_id), "tz", tz)

    def get_timezone(self, chat_id: int, default_tz: str) -> str:
        v = self.r.hget(self._user_key(chat_id), "tz")
        return (v.decode() if isinstance(v, bytes) else v) if v else default_tz

    def set_remind_times(self, chat_id: int, times: list[str]) -> None:
        self.r.hset(self._user_key(chat_id), "times", json.dumps(times, ensure_ascii=False))

    def get_remind_times(self, chat_id: int, default_times: list[str]) -> list[str]:
        v = self.r.hget(self._user_key(chat_id), "times")
        if not v:
            return default_times
        try:
            raw = v.decode() if isinstance(v, bytes) else v
            arr = json.loads(raw)
            if isinstance(arr, list):
                return [str(x) for x in arr]
        except Exception:
            return default_times
        return default_times

    # -------- daily state --------
    def _state_key(self, chat_id: int, date_str: str) -> str:
        return f"lc:state:{chat_id}:{date_str}"

    def load_state(self, chat_id: int, date_str: str) -> DailyState:
        key = self._state_key(chat_id, date_str)
        v = self.r.get(key)
        if not v:
            return DailyState(date=date_str, reminded_times=set(), congrats_sent=False, last_lc_check_ts=0)
        try:
            raw = v.decode() if isinstance(v, bytes) else v
            obj = json.loads(raw)
            return DailyState(
                date=obj.get("date", date_str),
                reminded_times=set(obj.get("reminded_times") or []),
                congrats_sent=bool(obj.get("congrats_sent")),
                last_lc_check_ts=int(obj.get("last_lc_check_ts") or 0),
            )
        except Exception:
            return DailyState(date=date_str, reminded_times=set(), congrats_sent=False, last_lc_check_ts=0)

    def save_state(self, chat_id: int, state: DailyState) -> None:
        key = self._state_key(chat_id, state.date)
        obj = {
            "date": state.date,
            "reminded_times": sorted(state.reminded_times),
            "congrats_sent": state.congrats_sent,
            "last_lc_check_ts": state.last_lc_check_ts,
        }
        # 8 kun TTL (state yig'ilib qolmasin)
        self.r.set(key, json.dumps(obj, ensure_ascii=False), ex=60 * 60 * 24 * 8)
