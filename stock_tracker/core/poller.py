"""Periyodik stok kontrolü ve bildirim.

Her turda: aboneli ürünleri çek, her abonelik için bedenin durumunu karşılaştır.
Bir beden 'stokta değil (veya bilinmiyor) -> stokta' geçişi yaparsa kullanıcıya haber ver.
`last_status` güncellenerek aynı stok için tekrar tekrar bildirim (spam) engellenir.
"""
from __future__ import annotations

import logging

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError

from stock_tracker.adapters.base import Status, get_adapter
from stock_tracker.core import repo

logger = logging.getLogger("stock_tracker.poller")


async def notify(bot: Bot, chat_id: int, product_name: str, size: str, url: str) -> None:
    text = (
        "🎉 *Stok geldi!*\n\n"
        f"*{product_name}* — *{size}* bedeni artık stokta!"
    )
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🛒 Ürüne git", url=url)]]
    )
    try:
        await bot.send_message(
            chat_id, text, parse_mode="Markdown", reply_markup=keyboard
        )
    except TelegramError as e:
        logger.warning("Bildirim gönderilemedi (chat %s): %r", chat_id, e)


async def check_all(bot: Bot) -> None:
    products = repo.products_with_subscribers()
    logger.info("Poll turu: %d ürün kontrol edilecek", len(products))

    for pid, _store, url, pname in products:
        adapter = get_adapter(url)
        if adapter is None:
            continue
        try:
            info = await adapter.fetch(url)
        except Exception as e:  # noqa: BLE001 - bir ürün patlarsa döngü sürsün
            logger.warning("Ürün çekilemedi (%s): %r", url, e)
            continue

        repo.touch_product(pid)
        display_name = pname or info.name or "Ürün"

        for sub_id, size, last_status, chat_id in repo.subscriptions_for_product(pid):
            current = info.sizes.get(size, Status.UNKNOWN)
            if current is Status.UNKNOWN:
                continue  # durum bilinmiyorsa dokunma
            # 'stokta değil -> stokta' geçişi mi?
            if current is Status.IN_STOCK and last_status != Status.IN_STOCK.value:
                await notify(bot, chat_id, display_name, size, url)
            if current.value != last_status:
                repo.update_subscription_status(sub_id, current.value)
