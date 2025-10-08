from datetime import datetime, timedelta
from typing import Iterable, List, Optional, Tuple

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
    依規則挑選每日單張雨量圖：
    - 06:20 取當天 05:00（f15）
    - 12:20 取當天 11:00（f09）
    若當下圖檔尚未發布，會回退嘗試另一時段或前一日 11:00。
    只要找到第一個 HTTP 可用的網址即回傳，否則回傳 None。
    """
    if not now:
        now = datetime.now()  # Local time (UTC+8)

    # 準備候選清單：優先依當前時段，並回退
    candidates_local = []  # List[(local_dt, f_str)]
    if 8 < now.hour < 18:
        # 中午時段：先試當天 11:00，再試當天 05:00，最後前一日 11:00
        candidates_local.append((now.replace(hour=11, minute=0, second=0, microsecond=0), "f09"))
        candidates_local.append((now.replace(hour=5, minute=0, second=0, microsecond=0), "f15"))
        candidates_local.append(((now - timedelta(days=1)).replace(hour=11, minute=0, second=0, microsecond=0), "f09"))
    else:
        # 早上或其他時段：先試當天 05:00，再試前一日 11:00，再試前一日 05:00
        candidates_local.append((now.replace(hour=5, minute=0, second=0, microsecond=0), "f15"))
        candidates_local.append(((now - timedelta(days=1)).replace(hour=11, minute=0, second=0, microsecond=0), "f09"))
        candidates_local.append(((now - timedelta(days=1)).replace(hour=5, minute=0, second=0, microsecond=0), "f15"))

    base_url = "https://watch.ncdr.nat.gov.tw/00_Wxmap/5F11_CWB_QPF_OFFICIAL"

    for local_dt, f_str in candidates_local:
        # 轉為 UTC 時戳做路徑（台灣 UTC+8）
        ts_utc = local_dt - timedelta(hours=8)
        ym = ts_utc.strftime("%Y%m")
        ts = ts_utc.strftime("%Y%m%d%H")
        url = f"{base_url}/{ym}/O01_{ts}_{f_str}_d12s.gif"
        if _is_image_url(url):
            print(f"Constructed NCDR daily rain URL: {url}")
            return url

    return None


def resolve_ncdr_12h_series_urls(now: Optional[datetime] = None) -> List[str]:
    """
    Build the list of 12 NCDR nowcast images (f01h..f12h) based on the latest available
    hour directory that exists. It searches backwards up to 24 hours.

    Examples (provided by user):
    - `https://watch.ncdr.nat.gov.tw/00_Wxmap/7F17_NCDRQPF_12H/202510/20251007/2025100720/2025100720_f01h.gif`
    - `https://watch.ncdr.nat.gov.tw/00_Wxmap/7F17_NCDRQPF_12H/202510/20251007/2025100720/2025100720_f02h.gif`
    """
    base_time = now or datetime.utcnow()
    base_url = "https://watch.ncdr.nat.gov.tw/00_Wxmap/7F17_NCDRQPF_12H"

    # Generate candidate hour directories, newest first
    candidate_hours = [base_time - timedelta(hours=h) for h in range(0, 25)]

    for ts in candidate_hours:
        ym = ts.strftime("%Y%m")
        ymd = ts.strftime("%Y%m%d")
        ymdh = ts.strftime("%Y%m%d%H")
        # Test f01h existence to confirm this hour directory has products
        test_url = f"{base_url}/{ym}/{ymd}/{ymdh}/{ymdh}_f01h.gif"
        if _is_image_url(test_url):
            # Build the full 12-image list
            return [f"{base_url}/{ym}/{ymd}/{ymdh}/{ymdh}_f{idx:02d}h.gif" for idx in range(1, 13)]

    return []

