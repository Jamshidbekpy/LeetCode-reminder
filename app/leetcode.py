from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass
from datetime import datetime

import requests
import pytz
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

LC_GRAPHQL_ENDPOINTS = [
    "https://leetcode.com/graphql",
    "https://leetcode.com/graphql/",
]
LC_HOME = "https://leetcode.com/"

# Real browser user agents (rotate to avoid detection)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Safari/605.1.15",
]

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

# requests 2.28+ has JSONDecodeError; fallback to stdlib for older versions
_RequestsJSONDecodeError = getattr(requests.exceptions, "JSONDecodeError", json.JSONDecodeError)

# Global session with retry strategy
_session = None

def _get_session() -> requests.Session:
    """Create or return a session with proper retry strategy and headers."""
    global _session
    if _session is None:
        _session = requests.Session()
        
        # Retry strategy: exponential backoff
        retry_strategy = Retry(
            total=1,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST", "GET"],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        _session.mount("https://", adapter)
        _session.mount("http://", adapter)
    
    return _session

def _get_headers(csrf_token: str | None = None) -> dict[str, str]:
    """Generate safe headers for server-to-server GraphQL requests."""
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/json",
        "Origin": "https://leetcode.com",
        "Referer": "https://leetcode.com/",
    }
    if csrf_token:
        headers["x-csrftoken"] = csrf_token
        headers["x-requested-with"] = "XMLHttpRequest"
    return headers


def _prime_session(session: requests.Session) -> str | None:
    """Warm up cookies and return csrf token if available."""
    try:
        response = session.get(
            LC_HOME,
            headers={
                "User-Agent": random.choice(USER_AGENTS),
                "Accept": "text/html,application/xhtml+xml",
                "Referer": "https://leetcode.com/",
            },
            timeout=20,
            allow_redirects=True,
        )
        response.raise_for_status()
    except requests.RequestException:
        return None
    return session.cookies.get("csrftoken")

def problem_link(slug: str) -> str:
    if not slug:
        return "https://leetcode.com/problemset/"
    return f"https://leetcode.com/problems/{slug}/"

def solved_today(username: str, tz_name: str, max_retries: int = 2) -> tuple[bool, AcceptedInfo | None]:
    """
    Check if user solved a problem today.
    
    Args:
        username: LeetCode username
        tz_name: Timezone name (e.g., 'Asia/Tashkent')
        max_retries: Maximum number of retry attempts
    
    Returns:
        Tuple of (solved_today: bool, AcceptedInfo | None)
    
    Raises:
        RuntimeError: If API returns errors or request fails after retries
        requests.RequestException: If network request fails
    """
    tz = pytz.timezone(tz_name)
    today = datetime.now(tz).date()
    
    payload = {
        "query": QUERY,
        "variables": {"username": username, "limit": 50},
        "operationName": "recent"
    }
    
    session = _get_session()
    csrf_token = _prime_session(session)
    headers = _get_headers(csrf_token)
    
    last_error = None
    
    for attempt in range(max_retries):
        try:
            # Random delay between requests to mimic human behavior
            if attempt > 0:
                delay = random.uniform(1.0, 3.0) * (attempt + 1)
                time.sleep(delay)
            
            # Make request with proper headers
            endpoint = LC_GRAPHQL_ENDPOINTS[attempt % len(LC_GRAPHQL_ENDPOINTS)]
            response = session.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=30,
                allow_redirects=False,
            )

            # Redirect bo'lsa ko'pincha HTML sahifaga ketadi (JSON emas)
            if 300 <= response.status_code < 400:
                location = response.headers.get("Location", "")
                last_error = RuntimeError(
                    f"LeetCode redirect qaytardi (status={response.status_code}, location={location})."
                )
                if attempt < max_retries - 1:
                    csrf_token = _prime_session(session)
                    headers = _get_headers(csrf_token)
                    continue
                raise last_error
            
            # Check for rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                if attempt < max_retries - 1:
                    time.sleep(retry_after + random.uniform(1, 5))
                    csrf_token = _prime_session(session)
                    headers = _get_headers(csrf_token)
                    continue
                raise RuntimeError(f"Rate limited. Retry after {retry_after} seconds")

            response.raise_for_status()

            text = response.text.strip()
            if not text or not (text.startswith("{") or text.startswith("[")):
                last_error = RuntimeError(
                    "LeetCode bo'sh yoki noto'g'ri javob qaytardi "
                    f"(status={response.status_code}). Keyinroq urinib ko'ring."
                )
                if attempt < max_retries - 1:
                    csrf_token = _prime_session(session)
                    headers = _get_headers(csrf_token)
                    continue
                raise last_error

            try:
                data = json.loads(text)
            except json.JSONDecodeError as e:
                last_error = RuntimeError(
                    f"LeetCode javobi JSON emas: {e}. "
                    "Sayt vaqtincha bloklagan yoki o'zgartirgan bo'lishi mumkin. Keyinroq urinib ko'ring."
                )
                if attempt < max_retries - 1:
                    csrf_token = _prime_session(session)
                    headers = _get_headers(csrf_token)
                    continue
                raise last_error
            
            # Check for GraphQL errors
            if "errors" in data:
                errors = data["errors"]
                # Some errors might be recoverable
                error_msg = str(errors[0].get("message", errors)) if errors else str(errors)
                
                # If it's a user not found error, that's different from API blocking
                if "user" in error_msg.lower() and "not found" in error_msg.lower():
                    raise RuntimeError(f"User '{username}' not found on LeetCode")
                
                # For other errors, retry if we have attempts left
                if attempt < max_retries - 1:
                    last_error = RuntimeError(f"LeetCode GraphQL error: {error_msg}")
                    csrf_token = _prime_session(session)
                    headers = _get_headers(csrf_token)
                    continue
                
                raise RuntimeError(f"LeetCode GraphQL error: {error_msg}")
            
            # Parse submissions
            subs = (data.get("data") or {}).get("recentSubmissionList") or []
            
            # Find today's accepted submission
            for s in subs:
                try:
                    ts = int(s["timestamp"])
                except (ValueError, KeyError, TypeError):
                    continue
                
                dt = datetime.fromtimestamp(ts, tz)
                if dt.date() == today and s.get("statusDisplay") == "Accepted":
                    return True, AcceptedInfo(
                        title=s.get("title") or "Accepted",
                        slug=s.get("titleSlug") or "",
                        lang=s.get("lang") or "",
                        time_hhmm=dt.strftime("%H:%M"),
                    )
            
            # No accepted submission found for today
            return False, None
            
        except requests.exceptions.Timeout as e:
            last_error = e
            if attempt < max_retries - 1:
                csrf_token = _prime_session(session)
                headers = _get_headers(csrf_token)
                continue
            raise RuntimeError(f"Request timeout after {max_retries} attempts: {e}")

        except (json.JSONDecodeError, _RequestsJSONDecodeError) as e:
            last_error = RuntimeError(
                "LeetCode bo'sh yoki noto'g'ri javob qaytardi (blok/cheklov bo'lishi mumkin). "
                "Bir necha daqiqa keyin /check yoki /status ni qayta urinib ko'ring."
            )
            if attempt < max_retries - 1:
                csrf_token = _prime_session(session)
                headers = _get_headers(csrf_token)
                continue
            raise last_error

        except requests.exceptions.RequestException as e:
            last_error = e
            err_msg = str(e).strip()
            if "expecting value" in err_msg.lower():
                last_error = RuntimeError(
                    "LeetCode bo'sh yoki noto'g'ri javob qaytardi (blok/cheklov bo'lishi mumkin). "
                    "Bir necha daqiqa keyin /check yoki /status ni qayta urinib ko'ring."
                )
            if attempt < max_retries - 1:
                csrf_token = _prime_session(session)
                headers = _get_headers(csrf_token)
                continue
            raise last_error if isinstance(last_error, RuntimeError) else RuntimeError(
                f"So'rov {max_retries} marta muvaffaqiyatsiz: {e}"
            )

        except (KeyError, ValueError, TypeError) as e:
            # Data parsing errors - don't retry
            raise RuntimeError(f"Failed to parse LeetCode response: {e}")
    
    # If we exhausted retries, raise the last error
    if last_error:
        raise last_error
    
    return False, None
