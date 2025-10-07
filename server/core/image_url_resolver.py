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

def resolve_ncdr_daily_rain_url(now: Optional[datetime] = None) -> Optional[str]:
    """
    Constructs the specific NCDR daily rain forecast image URL based on the time of day.
    - For the 06:20 run, it targets the 05:00 local time image.
    - For the 12:20 run, it targets the 11:00 local time image.
    """
    if not now:
        now = datetime.now() # Local time

    target_hour_local = 0
    f_hour_str = ""
    
    # Determine which run we are closer to
    if 8 < now.hour < 18: # Noon run (12:20)
        target_hour_local = 11
        f_hour_str = "f09"
    else: # Morning run (06:20) or other times
        target_hour_local = 5
        f_hour_str = "f15"

    target_time_local = now.replace(hour=target_hour_local, minute=0, second=0, microsecond=0)
    
    # Convert local target time to UTC
    # Taiwan is UTC+8
    target_time_utc = target_time_local - timedelta(hours=8)

    base_url = "https://watch.ncdr.nat.gov.tw/00_Wxmap/5F11_CWB_QPF_OFFICIAL"
    year_month = target_time_utc.strftime("%Y%m")
    timestamp = target_time_utc.strftime("%Y%m%d%H")

    # Format: O01_{YYYYMMDDHH}_{fXX}_d12s.gif
    url = f"{base_url}/{year_month}/O01_{timestamp}_{f_hour_str}_d12s.gif"
    
    print(f"Constructed NCDR daily rain URL: {url}")
    return url

