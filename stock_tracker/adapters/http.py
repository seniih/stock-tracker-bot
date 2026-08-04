"""Adaptörlerin paylaştığı HTTP istemcisi: tarayıcı gibi görünen istekler + basit rate-limit.

Sitelere kibar olmak (ve bloklanmamak) için domain başına istekler arasına küçük bir
bekleme koyar.

`httpx` yerine `curl_cffi` kullanılıyor: `httpx`'in TLS/HTTP2 el sıkışması gerçek
Chrome'unkinden farklı bir parmak izi (JA3/JA4) bırakıyor ve Akamai gibi
bot-korumaları bunu header'lardan bağımsız olarak tespit edip 403 dönebiliyor.
`curl_cffi` gerçek bir Chrome'un TLS/HTTP2 parmak izini taklit ediyor
(`impersonate="chrome"`).
"""
from __future__ import annotations

import asyncio
import time
from urllib.parse import urlsplit

from curl_cffi.requests import AsyncSession, Response

# `impersonate="chrome"` zaten User-Agent, sec-ch-ua, Accept vb. tüm header'ları
# taklit edilen Chrome sürümüyle tutarlı şekilde otomatik ayarlıyor (TLS parmak
# izinden farklı bir tarayıcı sürümü iddia etmek, tam tersine şüphe uyandırır).
# Burada sadece siteye Türkçe içerik istediğimizi belirtmek için Accept-Language
# override ediliyor.
_DEFAULT_HEADERS = {
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
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


async def get(url: str, *, headers: dict | None = None, **kwargs) -> Response:
    """Rate-limit'li GET. Ek header'lar varsayılanların üzerine yazılır."""
    await _throttle(_domain(url))
    merged = {**_DEFAULT_HEADERS, **(headers or {})}
    async with AsyncSession(impersonate="chrome", timeout=20.0) as session:
        return await session.get(url, headers=merged, allow_redirects=True, **kwargs)
