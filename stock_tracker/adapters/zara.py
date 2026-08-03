"""Zara adaptörü.

Zara'nın ürün HTML sayfası Akamai bot-koruması ardında; ama `products-details`
JSON ucu tek istekte her şeyi veriyor: ürün adı, renk, görsel ve beden bazında stok.

Ürün URL'sindeki `?v1=<productId>` parametresi, sorgulanacak renk/ürün id'sidir.
Örn: .../trf-...-p04730012.html?v1=497131620  ->  productId = 497131620
"""
from __future__ import annotations

import asyncio
import sys
from urllib.parse import parse_qs, urlsplit

from stock_tracker.adapters import http
from stock_tracker.adapters.base import ProductInfo, Status, register

_DETAILS_URL = "https://www.zara.com/tr/tr/products-details?productIds={pid}&ajax=true"
_JSON_HEADERS = {"Accept": "application/json, text/plain, */*"}

# Zara availability değerleri -> bizim Status
_IN_STOCK = {"in_stock", "low_on_stock"}
_OUT_OF_STOCK = {"out_of_stock", "coming_soon", "back_soon"}


def _map_status(availability: str | None) -> Status:
    av = (availability or "").lower()
    if av in _IN_STOCK:
        return Status.IN_STOCK
    if av in _OUT_OF_STOCK:
        return Status.OUT_OF_STOCK
    return Status.UNKNOWN


class ZaraAdapter:
    store = "zara"

    def matches(self, url: str) -> bool:
        return "zara.com" in urlsplit(url).netloc.lower()

    def _product_id(self, url: str) -> str:
        qs = parse_qs(urlsplit(url).query)
        v1 = qs.get("v1", [None])[0]
        if not v1 or not v1.isdigit():
            raise ValueError(
                "Zara linkinde ürün id'si (v1) bulunamadı. Lütfen ürün sayfasındaki "
                "'Paylaş' linkini kullan; sonunda '?v1=...' olmalı."
            )
        return v1

    async def fetch(self, url: str) -> ProductInfo:
        pid = self._product_id(url)
        resp = await http.get(_DETAILS_URL.format(pid=pid), headers=_JSON_HEADERS)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            raise ValueError("Zara ürün verisi boş döndü.")

        product = data[0]
        colors = product.get("detail", {}).get("colors", []) or []
        # v1 ile eşleşen rengi seç; bulunamazsa ilk renk.
        color = next(
            (c for c in colors if str(c.get("productId")) == pid),
            colors[0] if colors else {},
        )

        sizes: dict[str, Status] = {}
        for size in color.get("sizes", []) or []:
            label = size.get("name")
            if label:
                sizes[str(label)] = _map_status(size.get("availability"))

        return ProductInfo(
            store=self.store,
            external_id=pid,
            url=url,
            name=product.get("name"),
            image_url=_first_image(color),
            sizes=sizes,
        )


def _first_image(color: dict) -> str | None:
    for media in color.get("xmedia", []) or []:
        u = media.get("url")
        if u:
            # Zara url'lerinde genişlik yer tutucusu olabilir.
            return u.replace("{width}", "563")
    return None


register(ZaraAdapter())


# ---- CLI testi:  python -m stock_tracker.adapters.zara <url> -------------------
async def _cli(url: str) -> None:
    info = await ZaraAdapter().fetch(url)
    print(f"Ürün : {info.name}")
    print(f"Id   : {info.external_id}")
    print(f"Görsel: {info.image_url}")
    print("Bedenler:")
    for label, status in info.sizes.items():
        mark = "✅" if status is Status.IN_STOCK else "❌"
        print(f"  {mark} {label:>4}  {status.value}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Kullanım: python -m stock_tracker.adapters.zara <urun_url>")
        raise SystemExit(1)
    asyncio.run(_cli(sys.argv[1]))
