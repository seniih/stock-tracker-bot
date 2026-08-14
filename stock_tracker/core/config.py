"""Uygulama ayarları — .env dosyasından okunur."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    bot_token: str
    db_url: str
    poll_interval_minutes: int
    max_subscriptions_per_user: int


def load_settings() -> Settings:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN tanımlı değil. .env dosyasını .env.example'a göre doldur."
        )
    return Settings(
        bot_token=token,
        db_url=os.getenv("DB_URL", "sqlite:///stock_tracker.db").strip(),
        poll_interval_minutes=int(os.getenv("POLL_INTERVAL_MINUTES", "10")),
        # Bot herkese açık: kullanıcı başına abonelik sınırı olmazsa poller her
        # turda sınırsız sayıda ürün çeker ve mağazalar bizim IP'mizi engeller.
        max_subscriptions_per_user=int(os.getenv("MAX_SUBSCRIPTIONS_PER_USER", "20")),
    )
