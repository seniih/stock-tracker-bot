"""Adaptörlerin paylaştığı HTTP istemcisi: gerçekçi header'lar + basit rate-limit.

Sitelere kibar olmak (ve bloklanmamak) için domain başına istekler arasına küçük bir
bekleme koyar ve tarayıcıya benzeyen bir User-Agent gönderir.
"""
from __future__ import annotations

import asyncio
import time
from urllib.parse import urlsplit

import httpx

# Gerçek bir Chrome isteğine benzeyen header seti — bazı siteler (DeFacto vb.)
# eksik header'lı istekleri 403 ile reddediyor.
_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

# Aynı domaine ardışık istekler arasında en az bu kadar saniye bekle.
_MIN_INTERVAL_SEC = 2.0

_last_request_at: dict[str, float] = {}
_locks: dict[str, asyncio.Lock] = {}


def _domain(url: str) -> str:
    return urlsplit(url).netloc


async def _throttle(domain: str) -> None:
    lock = _locks.setdefault(domain, asyncio.Lock())
    async with lock:
        elapsed = time.monotonic() - _last_request_at.get(domain, 0.0)
        wait = _MIN_INTERVAL_SEC - elapsed
        if wait > 0:
            await asyncio.sleep(wait)
        _last_request_at[domain] = time.monotonic()


async def get(url: str, *, headers: dict | None = None, **kwargs) -> httpx.Response:
    """Rate-limit'li GET. Ek header'lar varsayılanların üzerine yazılır."""
    await _throttle(_domain(url))
    merged = {**_DEFAULT_HEADERS, **(headers or {})}
    async with httpx.AsyncClient(
        follow_redirects=True, timeout=20.0, headers=merged, http2=True
    ) as client:
        return await client.get(url, **kwargs)
