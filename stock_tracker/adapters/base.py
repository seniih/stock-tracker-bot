"""Mağaza adaptörleri için ortak arayüz ve registry.

Her mağaza (Zara, LC Waikiki, ...) bir StockAdapter uygular. Hepsi aynı sözleşmeyi
konuşur: bir ürün URL'sini alır, ürün bilgisini + beden bazında stok durumunu döndürür.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, runtime_checkable
from urllib.parse import urlsplit


class Status(str, Enum):
    IN_STOCK = "IN_STOCK"
    OUT_OF_STOCK = "OUT_OF_STOCK"
    UNKNOWN = "UNKNOWN"


@dataclass
class ProductInfo:
    store: str
    external_id: str
    url: str
    name: str | None = None
    image_url: str | None = None
    # beden etiketi -> stok durumu, ör. {"S": IN_STOCK, "M": OUT_OF_STOCK}
    sizes: dict[str, Status] = field(default_factory=dict)


@runtime_checkable
class StockAdapter(Protocol):
    store: str

    def matches(self, url: str) -> bool:
        """Bu adaptör verilen URL'yi işleyebilir mi?"""
        ...

    async def fetch(self, url: str) -> ProductInfo:
        """Ürünü çek ve beden bazında stok durumunu döndür."""
        ...


def domain_matches(url: str, domain: str) -> bool:
    """URL gerçekten `domain`e mi ait?

    Adaptörlerin `matches()` metodu bunu kullanmalı. Basit bir alt-dize kontrolü
    (`"zara.com" in netloc`) yetmez, çünkü bot herkese açık ve URL'yi kullanıcı
    gönderiyor; şu adresler alt-dize kontrolünü geçip sunucumuzu saldırganın
    seçtiği bir host'a istek atmaya zorlardı (SSRF):

        https://zara.com.saldirgan.net/...   -> netloc alt-dize olarak eşleşir
        https://www.zara.com@saldirgan.net/  -> netloc "www.zara.com@saldirgan.net",
                                                ama istek saldirgan.net'e gider

    Bu yüzden host, kullanıcı bilgisi (`user@`) ve porttan arındırılıp tam
    eşitlik ya da gerçek alt alan adı (`.domain` ile bitme) aranıyor.
    """
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        return False
    # netloc "kullanici@host:port" olabilir; sadece host kısmını al.
    host = parts.netloc.lower().rpartition("@")[2].partition(":")[0]
    return host == domain or host.endswith("." + domain)


# ---- Registry ----------------------------------------------------------------

_ADAPTERS: list[StockAdapter] = []


def register(adapter: StockAdapter) -> StockAdapter:
    _ADAPTERS.append(adapter)
    return adapter


def get_adapter(url: str) -> StockAdapter | None:
    for adapter in _ADAPTERS:
        if adapter.matches(url):
            return adapter
    return None
