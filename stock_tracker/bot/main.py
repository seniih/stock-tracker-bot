"""Bot giriş noktası.

Çalıştırma:  python -m stock_tracker.bot.main
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from stock_tracker.adapters import load_all
from stock_tracker.bot import handlers
from stock_tracker.core.config import load_settings
from stock_tracker.core.db import init_db
from stock_tracker.core.poller import check_all

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", level=logging.INFO
)
# httpx INFO seviyesinde her istegi tam URL'iyle logluyor; Telegram API URL'i
# bot token'ini icerdigi icin token her 10 saniyede bir loglara (ve `docker logs`
# ciktisina) yaziliyordu. WARNING'e cekilince gercek hatalar hala gorunur.
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("stock_tracker")


def build_app(token: str) -> Application:
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", handlers.start))
    app.add_handler(CommandHandler(["yardim", "help"], handlers.help_cmd))
    app.add_handler(CommandHandler(["liste", "list"], handlers.liste))
    app.add_handler(CallbackQueryHandler(handlers.on_subscribe, pattern=r"^sub:"))
    app.add_handler(CallbackQueryHandler(handlers.on_delete, pattern=r"^del:"))
    # Komut olmayan düz metinler (on_url içinde link olup olmadığı kontrol edilir)
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.on_url)
    )
    return app


def main() -> None:
    settings = load_settings()
    init_db(settings.db_url)
    load_all()  # mağaza adaptörlerini registry'ye yükle
    logger.info("Veritabanı hazır: %s", settings.db_url)

    async def _post_init(app: Application) -> None:
        # Bot'un event loop'u çalışırken zamanlayıcıyı başlat.
        scheduler = AsyncIOScheduler()
        scheduler.add_job(
            check_all,
            trigger="interval",
            minutes=settings.poll_interval_minutes,
            args=[app.bot],
            jitter=60,  # sitelere yükü dağıtmak için ±60 sn
            next_run_time=None,  # ilk turu bir sonraki aralıkta çalıştır
        )
        scheduler.start()
        app.bot_data["scheduler"] = scheduler
        logger.info(
            "Poller aktif: her %d dakikada bir stok kontrolü",
            settings.poll_interval_minutes,
        )

    app = build_app(settings.bot_token)
    app.post_init = _post_init
    logger.info("Bot başlatılıyor (long polling)...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
