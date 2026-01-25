from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import requests
import pytz

LC_GRAPHQL = "https://leetcode.com/graphql/"

QUERY = """
query recent($username: String!, $limit: Int!) {
  recentSubmissionList(username: $username, limit: $limit) {
    title
    titleSlug
    timestamp
    statusDisplay
    lang
  }
}
"""

@dataclass(frozen=True)
class AcceptedInfo:
    title: str
    slug: str
    lang: str
    time_hhmm: str

def problem_link(slug: str) -> str:
    if not slug:
        return "https://leetcode.com/problemset/"
    return f"https://leetcode.com/problems/{slug}/"

def solved_today(username: str, tz_name: str) -> tuple[bool, AcceptedInfo | None]:
    tz = pytz.timezone(tz_name)
    today = datetime.now(tz).date()

    payload = {"query": QUERY, "variables": {"username": username, "limit": 50}}
    r = requests.post(LC_GRAPHQL, json=payload, timeout=20)
    r.raise_for_status()
    data = r.json()

    if "errors" in data:
        raise RuntimeError(f"LeetCode GraphQL error: {data['errors']}")

    subs = (data.get("data") or {}).get("recentSubmissionList") or []

    for s in subs:
        try:
            ts = int(s["timestamp"])
        except Exception:
            continue
        dt = datetime.fromtimestamp(ts, tz)
        if dt.date() == today and s.get("statusDisplay") == "Accepted":
            return True, AcceptedInfo(
                title=s.get("title") or "Accepted",
                slug=s.get("titleSlug") or "",
                lang=s.get("lang") or "",
                time_hhmm=dt.strftime("%H:%M"),
            )

    return False, None
