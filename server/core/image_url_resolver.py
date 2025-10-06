from datetime import datetime, timedelta
from typing import Iterable, List, Optional

import requests


def _is_image_url(url: str, timeout_seconds: int = 10) -> bool:
    from server import config
    try:
        resp = requests.head(
            url,
            timeout=timeout_seconds,
            allow_redirects=True,
            verify=getattr(config, "REQUESTS_VERIFY_SSL", True),
        )
        if resp.status_code == 200 and 'image' in (resp.headers.get('Content-Type') or '').lower():
            return True
        # Some servers do not support HEAD properly; try GET with small timeout
        resp = requests.get(
            url,
            timeout=timeout_seconds,
            stream=True,
            verify=getattr(config, "REQUESTS_VERIFY_SSL", True),
        )
        content_type = (resp.headers.get('Content-Type') or '').lower()
        return resp.status_code == 200 and 'image' in content_type
    except Exception:
        return False


def _try_patterns(patterns: Iterable[str], times: Iterable[datetime]) -> Optional[str]:
    for ts in times:
        for pattern in patterns:
            candidate = ts.strftime(pattern)
            if _is_image_url(candidate):
                return candidate
    return None


def resolve_latest_url(patterns: List[str], now: Optional[datetime] = None, hours_back: int = 36) -> Optional[str]:
    """
    Try multiple timestamped URL patterns and return the first that exists.
    """
    if not patterns:
        return None
    base_time = now or datetime.utcnow()
    times = [base_time - timedelta(hours=h) for h in range(hours_back + 1)]
    return _try_patterns(patterns, times)


