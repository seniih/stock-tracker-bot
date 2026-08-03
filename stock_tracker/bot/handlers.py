"""Telegram komut ve callback handler'ları."""
from __future__ import annotations

import logging
import re

from telegram import Update
from telegram.ext import ContextTypes

from stock_tracker.adapters.base import Status, get_adapter
from stock_tracker.bot import keyboards
from stock_tracker.core import repo

logger = logging.getLogger("stock_tracker.handlers")

_URL_RE = re.compile(r"https?://\S+")

WELCOME = (
    "Merhaba {name}! 👋\n\n"
    "Ben StockTracker. Giyim mağazalarında tükenen ürünlerin bedeni tekrar stoğa "
    "girince sana haber veririm.\n\n"
    "🛍 Bir ürünün linkini bana gönder (şu an *Zara* ve *DeFacto* destekleniyor). "
    "Sana bedenleri göstereyim, hangisini takip etmek istersen dokun.\n\n"
    "Komutlar:\n"
    "/liste — takip ettiklerim\n"
    "/yardim — yardım"
)

HELP = (
    "📖 *Nasıl kullanılır?*\n\n"
    "1️⃣ Bir ürün linki gönder (ör. Zara ürün sayfasının paylaş linki).\n"
    "2️⃣ Bedenleri butonlarla gösteririm: ✅ mevcut, ❌ tükenmiş.\n"
    "3️⃣ Takip etmek istediğin bedene dokun.\n"
    "4️⃣ O beden stoğa girince sana mesaj atarım.\n\n"
    "/liste ile takip ettiklerini görüp silebilirsin."
)


def _ensure_user(update: Update) -> None:
    u, c = update.effective_user, update.effective_chat
    if u and c:
        repo.upsert_user(u.id, c.id, u.username)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _ensure_user(update)
    await update.message.reply_markdown(
        WELCOME.format(name=update.effective_user.first_name)
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_markdown(HELP)


async def on_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Kullanıcı bir link gönderdi: mağazayı tanı, ürünü çek, bedenleri göster."""
    _ensure_user(update)
    match = _URL_RE.search(update.message.text or "")
    if not match:
        return
    url = match.group(0)

    adapter = get_adapter(url)
    if adapter is None:
        await update.message.reply_text(
            "Bu siteyi henüz desteklemiyorum. Şu an Zara ve DeFacto linklerini "
            "gönderebilirsin."
        )
        return

    status_msg = await update.message.reply_text("🔎 Ürün kontrol ediliyor...")
    try:
        info = await adapter.fetch(url)
    except Exception as e:  # noqa: BLE001 - kullanıcıya sade mesaj
        logger.warning("fetch hatası (%s): %r", url, e)
        await status_msg.edit_text(f"⚠️ Ürünü alamadım: {e}")
        return

    if not info.sizes:
        await status_msg.edit_text("Bu üründe beden bilgisi bulamadım.")
        return

    product_id = repo.upsert_product(info)
    # Bedenlerin güncel durumunu callback'te kullanmak için önbelleğe al.
    cache = context.user_data.setdefault("sizes", {})
    cache[product_id] = {k: v.value for k, v in info.sizes.items()}

    await status_msg.delete()
    caption = (
        f"🛍 *{info.name or 'Ürün'}*\n\n"
        "Takip etmek istediğin bedene dokun (✅ mevcut, ❌ tükenmiş):"
    )
    keyboard = keyboards.size_keyboard(product_id, info.sizes)
    if info.image_url:
        await update.message.reply_photo(
            info.image_url, caption=caption, parse_mode="Markdown", reply_markup=keyboard
        )
    else:
        await update.message.reply_markdown(caption, reply_markup=keyboard)


async def on_subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """'sub:<product_id>:<size>' butonuna basıldı."""
    query = update.callback_query
    await query.answer()
    _, product_id_str, size = query.data.split(":", 2)
    product_id = int(product_id_str)
    user_id = update.effective_user.id

    # Bedenin güncel durumu (önbellekten; yoksa UNKNOWN -> poller ilk turda düzeltir).
    cached = context.user_data.get("sizes", {}).get(product_id, {})
    last_status = cached.get(size, Status.UNKNOWN.value)

    added = repo.add_subscription(user_id, product_id, size, last_status)
    if added:
        note = ""
        if last_status == Status.IN_STOCK.value:
            note = "\n(Bu beden şu an *stokta*; tükenip tekrar gelirse haber veririm.)"
        await query.message.reply_markdown(f"✅ *{size}* bedeni takibe alındı.{note}")
    else:
        await query.message.reply_text(f"ℹ️ *{size}* bedenini zaten takip ediyorsun.")


async def liste(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _ensure_user(update)
    items = repo.list_subscriptions(update.effective_user.id)
    if not items:
        await update.message.reply_text(
            "Henüz bir şey takip etmiyorsun. Bir ürün linki gönder! 🛍"
        )
        return
    await update.message.reply_text(
        f"📋 Takip ettiklerin ({len(items)}). Silmek için dokun:",
        reply_markup=keyboards.list_keyboard(items),
    )


async def on_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """'del:<subscription_id>' butonuna basıldı."""
    query = update.callback_query
    sub_id = int(query.data.split(":", 1)[1])
    label = repo.delete_subscription(update.effective_user.id, sub_id)
    if label is None:
        await query.answer("Bulunamadı.")
        return
    await query.answer(f"{label} bedeni silindi.")
    # Listeyi güncelle
    items = repo.list_subscriptions(update.effective_user.id)
    if items:
        await query.edit_message_reply_markup(keyboards.list_keyboard(items))
    else:
        await query.edit_message_text("Takip listen boş. 🛍")
