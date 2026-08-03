"""Inline klavyeler: beden seçimi ve abonelik listesi."""
from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from stock_tracker.adapters.base import Status
from stock_tracker.core.models import Product, Subscription

# callback_data biçimleri (64 bayt sınırı içinde):
#   sub:<product_id>:<size_label>   -> bedene abone ol
#   del:<subscription_id>           -> aboneliği sil


def size_keyboard(product_id: int, sizes: dict[str, Status]) -> InlineKeyboardMarkup:
    """Her beden bir buton: '✅ 38' (mevcut) / '❌ 38' (tükenmiş). Dokununca abone olur."""
    buttons: list[InlineKeyboardButton] = []
    for label, status in sizes.items():
        mark = "✅" if status is Status.IN_STOCK else "❌"
        buttons.append(
            InlineKeyboardButton(
                f"{mark} {label}", callback_data=f"sub:{product_id}:{label}"
            )
        )
    # 3'erli satırlar
    rows = [buttons[i : i + 3] for i in range(0, len(buttons), 3)]
    return InlineKeyboardMarkup(rows)


def list_keyboard(items: list[tuple[Subscription, Product]]) -> InlineKeyboardMarkup:
    """Her abonelik için bir 'sil' butonu."""
    rows = []
    for sub, prod in items:
        name = (prod.name or "Ürün")[:28]
        rows.append(
            [
                InlineKeyboardButton(
                    f"🗑 {name} · {sub.size_label}", callback_data=f"del:{sub.id}"
                )
            ]
        )
    return InlineKeyboardMarkup(rows)
