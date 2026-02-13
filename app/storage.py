from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional
from redis import Redis
from app.database import Database, User

@dataclass
class DailyState:
    date: str                # YYYY-MM-DD (user timezone bo'yicha)
    reminded_times: set[str] # HH:MM
    congrats_sent: bool
    last_lc_check_ts: int    # unix seconds (throttle uchun)
    last_error_ts: int = 0   # unix seconds (error spam prevention)
    last_rate_limit_ts: int = 0  # unix seconds (rate limit error spam prevention)

class Storage:
    """
    Redis schema:
    - users set: lc:users -> chat_id lar
    - user config hash: lc:user:{chat_id} -> username, tz, times(json)
    - daily state key: lc:state:{chat_id}:{date} -> json
    
    PostgreSQL:
    - users table: telegram_id, telegram_username, leetcode_username, etc.
    """

    def __init__(self, r: Redis, db: Optional[Database] = None):
        self.r = r
        self.db = db  # PostgreSQL database (optional)

    # -------- users registry --------
    def add_user(
        self,
        chat_id: int,
        telegram_username: Optional[str] = None,
        telegram_first_name: Optional[str] = None,
        telegram_last_name: Optional[str] = None,
    ) -> None:
        """Add user to Redis and PostgreSQL"""
        self.r.sadd("lc:users", str(chat_id))
        
        # Also save to PostgreSQL if available
        if self.db:
            try:
                self.db.create_or_update_user(
                    telegram_id=chat_id,
                    telegram_username=telegram_username,
                    telegram_first_name=telegram_first_name,
                    telegram_last_name=telegram_last_name,
                    is_active=True,
                )
            except Exception:
                # PostgreSQL error shouldn't break Redis operations
                pass

    def remove_user(self, chat_id: int) -> None:
        """Remove user from Redis and mark as inactive in PostgreSQL"""
        self.r.srem("lc:users", str(chat_id))
        
        # Mark as inactive in PostgreSQL if available
        if self.db:
            try:
                self.db.create_or_update_user(
                    telegram_id=chat_id,
                    is_active=False,
                )
            except Exception:
                pass

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
        """Set LeetCode username in Redis and PostgreSQL"""
        self.r.hset(self._user_key(chat_id), "username", username)
        
        # Also save to PostgreSQL if available
        if self.db:
            try:
                self.db.create_or_update_user(
                    telegram_id=chat_id,
                    leetcode_username=username,
                )
            except Exception:
                pass

    def get_username(self, chat_id: int) -> Optional[str]:
        v = self.r.hget(self._user_key(chat_id), "username")
        if v:
            return (v.decode() if isinstance(v, bytes) else v)
        # PostgreSQL fallback (Redis yo'qolsa yoki eviction bo'lsa)
        if self.db:
            try:
                user = self.db.get_user_by_telegram_id(chat_id)
                if user and user.leetcode_username:
                    self.r.hset(self._user_key(chat_id), "username", user.leetcode_username)
                    return user.leetcode_username
            except Exception:
                pass
        return None

    def set_timezone(self, chat_id: int, tz: str) -> None:
        """Set timezone in Redis and PostgreSQL"""
        self.r.hset(self._user_key(chat_id), "tz", tz)
        
        # Also save to PostgreSQL if available
        if self.db:
            try:
                self.db.create_or_update_user(
                    telegram_id=chat_id,
                    timezone=tz,
                )
            except Exception:
                pass

    def get_timezone(self, chat_id: int, default_tz: str) -> str:
        v = self.r.hget(self._user_key(chat_id), "tz")
        if v:
            return (v.decode() if isinstance(v, bytes) else v)
        if self.db:
            try:
                user = self.db.get_user_by_telegram_id(chat_id)
                if user and user.timezone:
                    self.r.hset(self._user_key(chat_id), "tz", user.timezone)
                    return user.timezone
            except Exception:
                pass
        return default_tz

    def set_remind_times(self, chat_id: int, times: list[str]) -> None:
        """Set remind times in Redis and PostgreSQL"""
        self.r.hset(self._user_key(chat_id), "times", json.dumps(times, ensure_ascii=False))
        
        # Also save to PostgreSQL if available
        if self.db:
            try:
                self.db.create_or_update_user(
                    telegram_id=chat_id,
                    remind_times=times,
                )
            except Exception:
                pass

    def get_remind_times(self, chat_id: int, default_times: list[str]) -> list[str]:
        v = self.r.hget(self._user_key(chat_id), "times")
        if v:
            try:
                raw = v.decode() if isinstance(v, bytes) else v
                arr = json.loads(raw)
                if isinstance(arr, list):
                    return [str(x) for x in arr]
            except Exception:
                pass
        if self.db:
            try:
                user = self.db.get_user_by_telegram_id(chat_id)
                if user and user.remind_times:
                    times = [str(t) for t in user.remind_times]
                    self.r.hset(self._user_key(chat_id), "times", json.dumps(times, ensure_ascii=False))
                    return times
            except Exception:
                pass
        return default_times

    # -------- external api cooldown --------
    def _api_cooldown_key(self, chat_id: int, scope: str) -> str:
        return f"lc:api_cooldown:{scope}:{chat_id}"

    def acquire_external_api_slot(
        self, chat_id: int, cooldown_seconds: int, scope: str = "shared"
    ) -> tuple[bool, int]:
        """
        Acquire cooldown slot for external API calls.
        Returns (allowed, remaining_seconds_if_blocked).
        """
        if cooldown_seconds <= 0:
            return True, 0

        key = self._api_cooldown_key(chat_id, scope)
        # NX + EX => set only if key does not exist
        acquired = self.r.set(key, "1", ex=cooldown_seconds, nx=True)
        if acquired:
            return True, 0

        ttl = self.r.ttl(key)
        return False, max(int(ttl), 0)

    # -------- daily state --------
    def _state_key(self, chat_id: int, date_str: str) -> str:
        return f"lc:state:{chat_id}:{date_str}"

    def load_state(self, chat_id: int, date_str: str) -> DailyState:
        key = self._state_key(chat_id, date_str)
        v = self.r.get(key)
        if not v:
            return DailyState(date=date_str, reminded_times=set(), congrats_sent=False, last_lc_check_ts=0, last_error_ts=0, last_rate_limit_ts=0)
        try:
            raw = v.decode() if isinstance(v, bytes) else v
            obj = json.loads(raw)
            return DailyState(
                date=obj.get("date", date_str),
                reminded_times=set(obj.get("reminded_times") or []),
                congrats_sent=bool(obj.get("congrats_sent")),
                last_lc_check_ts=int(obj.get("last_lc_check_ts") or 0),
                last_error_ts=int(obj.get("last_error_ts") or 0),
                last_rate_limit_ts=int(obj.get("last_rate_limit_ts") or 0),
            )
        except Exception:
            return DailyState(date=date_str, reminded_times=set(), congrats_sent=False, last_lc_check_ts=0, last_error_ts=0, last_rate_limit_ts=0)

    def save_state(self, chat_id: int, state: DailyState) -> None:
        key = self._state_key(chat_id, state.date)
        obj = {
            "date": state.date,
            "reminded_times": sorted(state.reminded_times),
            "congrats_sent": state.congrats_sent,
            "last_lc_check_ts": state.last_lc_check_ts,
            "last_error_ts": state.last_error_ts,
            "last_rate_limit_ts": state.last_rate_limit_ts,
        }
        # 8 kun TTL (state yig'ilib qolmasin)
        self.r.set(key, json.dumps(obj, ensure_ascii=False), ex=60 * 60 * 24 * 8)
