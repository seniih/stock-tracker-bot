"""Mağaza adaptörleri için ortak arayüz ve registry.

Her mağaza (Zara, LC Waikiki, ...) bir StockAdapter uygular. Hepsi aynı sözleşmeyi
konuşur: bir ürün URL'sini alır, ürün bilgisini + beden bazında stok durumunu döndürür.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, runtime_checkable


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


def all_adapters() -> list[StockAdapter]:
    return list(_ADAPTERS)
