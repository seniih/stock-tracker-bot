"""DeFacto adaptörü.

DeFacto ürün sayfası (gerçekçi tarayıcı header'larıyla) HTML içinde beden/stok
verisini sunucu tarafında gömüyor: her beden için `"SizeName":"M","StockQuantity":N`.
StockQuantity > 0 -> stokta. Ayrı API'ye gerek yok.

Ürün id'si URL'nin sonundaki sayıdır: .../...-elbise-3484705 -> 3484705
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
from html import unescape
from urllib.parse import urlsplit

from stock_tracker.adapters import http
from stock_tracker.adapters.base import ProductInfo, Status, register

_SIZE_RE = re.compile(r'"SizeName":"([^"]+)","StockQuantity":(\d+)')
_ID_RE = re.compile(r"-(\d+)(?:[/?#]|$)")
_LDJSON_RE = re.compile(
    r'<script type="application/ld\+json">(.*?)</script>', re.S
)
_OG_IMAGE_RE = re.compile(
    r'<meta[^>]+property=["\']?og:image["\']?[^>]+content=["\']?([^"\'\s>]+)'
)
_TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S)


class DefactoAdapter:
    store = "defacto"

    def matches(self, url: str) -> bool:
        return "defacto.com.tr" in urlsplit(url).netloc.lower()

    def _product_id(self, url: str) -> str:
        path = urlsplit(url).path
        matches = _ID_RE.findall(path)
        if not matches:
            raise ValueError("DeFacto linkinde ürün id'si bulunamadı.")
        return matches[-1]

    async def fetch(self, url: str) -> ProductInfo:
        pid = self._product_id(url)
        resp = await http.get(url)
        resp.raise_for_status()
        html = resp.text

        sizes: dict[str, Status] = {}
        for label, qty in _SIZE_RE.findall(html):
            # Aynı beden birden fazla geçerse stokta olanı önceliklendir.
            status = Status.IN_STOCK if int(qty) > 0 else Status.OUT_OF_STOCK
            if label not in sizes or status is Status.IN_STOCK:
                sizes[label] = status

        return ProductInfo(
            store=self.store,
            external_id=pid,
            url=url,
            name=_extract_name(html),
            image_url=_extract_image(html),
            sizes=sizes,
        )


def _extract_name(html: str) -> str | None:
    for m in _LDJSON_RE.finditer(html):
        try:
            data = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        types = data.get("@type") if isinstance(data, dict) else None
        if types == "Product" or (isinstance(types, list) and "Product" in types):
            if data.get("name"):
                return unescape(data["name"]).strip()
    m = _TITLE_RE.search(html)
    if m:
        name = re.sub(r"\s*\|\s*DeFacto.*$", "", unescape(m.group(1)))
        return re.sub(r"\s*\d+\s*$", "", name).strip()  # sondaki ürün id'sini at
    return None


def _extract_image(html: str) -> str | None:
    m = _OG_IMAGE_RE.search(html)
    return m.group(1) if m else None


register(DefactoAdapter())


# ---- CLI testi:  python -m stock_tracker.adapters.defacto <url> ----------------
async def _cli(url: str) -> None:
    info = await DefactoAdapter().fetch(url)
    print(f"Ürün : {info.name}")
    print(f"Id   : {info.external_id}")
    print(f"Görsel: {info.image_url}")
    print("Bedenler:")
    for label, status in info.sizes.items():
        mark = "✅" if status is Status.IN_STOCK else "❌"
        print(f"  {mark} {label:>4}  {status.value}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Kullanım: python -m stock_tracker.adapters.defacto <urun_url>")
        raise SystemExit(1)
    asyncio.run(_cli(sys.argv[1]))
